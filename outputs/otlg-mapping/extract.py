import json, re, unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import engine
from app.models import BacklogChange, BacklogImport, BacklogImportRow

def normal(value):
 return ''.join(c for c in unicodedata.normalize('NFKD',str(value)) if not unicodedata.combining(c)).lower()
def otlg(data):
 for name,value in data.items():
  if normal(name) == 'bemerkung otlg': return str(value).strip() if value is not None else ''
 return ''
def creation(data):
 for name,value in data.items():
  if normal(name) == 'anlagedatum': return value
 return None
def delivery(data):
 for name,value in data.items():
  if normal(name) == 'liefertermin': return value
 return None
def proposal(text):
 date=re.search(r'(?<!\d)(\d{1,2}[.]\d{1,2}[.]20\d{2})(?!\d)',text)
 kw=re.search(r'\bKW\s*(\d{1,2})(?:\s*[/.-]\s*(20\d{2}))?',text,re.I)
 if date:return ('Datum im Text',date.group(1),'Datum direkt aus Text übernehmen')
 if kw:return ('KW-Avis',('KW '+kw.group(1)+(('/'+kw.group(2)) if kw.group(2) else '')),'Kalenderwoche prüfen und als Datum festlegen')
 if 'tschechien' in text.lower():return ('Lieferant Tschechien','','kein Termin im Text')
 return ('Noch zuzuordnen','','')

db=Session(engine)
imports={row.id:row.source_name for row in db.scalars(select(BacklogImport)).all()}
counts=Counter(); examples={}; example_dates={}
for snapshot in db.scalars(select(BacklogImportRow)).all():
 data=json.loads(snapshot.data); text=otlg(data)
 if text:
  counts[text]+=1; examples.setdefault(text,snapshot.backlog_id); example_dates.setdefault(text,creation(data))
mapping=[]
for text,count in sorted(counts.items(),key=lambda item:(-item[1],item[0].lower())):
 category, suggestion, rule=proposal(text)
 mapping.append({'Originaltext':text,'Häufigkeit':count,'Beispiel Rückstand ID':examples[text],'Beispiel Anlagedatum':example_dates[text],'Vorschlag Kategorie':category,'Vorschlag Avisiertes Lieferdatum':suggestion,'Avisiertes Lieferdatum (manuell)':'','Regel / Mapping (manuell)':rule})
changes=[]
for change in db.scalars(select(BacklogChange).order_by(BacklogChange.import_id,BacklogChange.backlog_id)).all():
 before=json.loads(change.before_data) if change.before_data else {}; after=json.loads(change.after_data) if change.after_data else {}
 changes.append({'Datei':imports.get(change.import_id,''),'Rückstand ID':change.backlog_id,'Änderungsart':change.change_type,'Geänderte Felder':change.changed_fields or '', 'Liefertermin vorher':delivery(before) or '', 'Liefertermin nachher':delivery(after) or '', 'Bemerkung OTLG vorher':otlg(before), 'Bemerkung OTLG nachher':otlg(after)})
out={'mapping':mapping,'changes':changes,'summary':{'distinct_texts':len(mapping),'text_occurrences':sum(counts.values()),'changes':len(changes),'imports':len(imports)}}
Path('outputs/otlg-mapping/source.json').write_text(json.dumps(out,ensure_ascii=False,default=str),encoding='utf-8')
print(out['summary'])
db.close()

