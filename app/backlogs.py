from datetime import date, datetime, timedelta
import json
import re
from pathlib import Path
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session
from .database import get_db
from .models import Backlog, BacklogChange, BacklogImport, BacklogImportRow, OtlgMapping
from fastapi.templating import Jinja2Templates

templates=Jinja2Templates(directory=Path(__file__).parent / "templates")
router=APIRouter()
FOLDER=Path(r"G:\Disposition\Rückstandslisten")

def key(value): return re.sub(r"[^a-z0-9]+", "", str(value).lower())
def field(data, *names):
 expected={key(name) for name in names}
 return next((value for name,value in data.items() if key(name) in expected),None)
def parse_date(value):
 if isinstance(value,datetime): return value
 if isinstance(value,date): return datetime.combine(value,datetime.min.time())
 if isinstance(value,str):
  try: return datetime.fromisoformat(value)
  except ValueError: pass
  for fmt in ("%Y-%m-%d","%d.%m.%Y","%d.%m.%y"):
   try: return datetime.strptime(value,fmt)
   except ValueError: pass
 return None
def serialise(value): return value.isoformat() if hasattr(value,"isoformat") else value

def mapping_key(value): return re.sub(r"\s+"," ",str(value or "").casefold()).strip()
def mapping_lookup(db): return {item.text_key:item for item in db.scalars(select(OtlgMapping)).all()}
def sync_mapping_texts(db,records):
 known=mapping_lookup(db)
 for row in records:
  text=str(field(row,"Bemerkung OTLG") or "").strip(); normalized=mapping_key(text)
  if normalized and normalized not in known:
   item=OtlgMapping(text_key=normalized,original_text=text); db.add(item); known[normalized]=item
 return known
def apply_mapping(row,mapping=None):
 if mapping:
  row["Maßnahme"]=mapping.measure or ""; row["Kategorie"]=mapping.category or ""; row["Mapping-Regel"]=mapping.mapping_rule or ""
 row["Avisierter Liefertermin"]=announced_delivery(row,mapping)
def announced_delivery(row,mapping=None):
 if mapping and mapping.announced_delivery and "anlagedatum" not in str(mapping.mapping_rule or "").casefold(): return mapping.announced_delivery
 note=str(field(row,"Bemerkung OTLG") or "")
 week_blocks=re.findall(r"\bKW\s*(\d{1,2}(?:\s*[/.-]\s*\d{1,2})*)",note,re.I)
 weeks=[int(number) for block in week_blocks for number in re.findall(r"\d{1,2}",block)]
 if weeks: return f"KW {max(weeks)+1}"
 days=re.search(r"Planlieferzeit[^\d]*(\d+)\s*Tage",note,re.I); creation=parse_date(field(row,"Anlagedatum"))
 if days and creation: return (creation+timedelta(days=int(days.group(1))+2)).strftime("%d.%m.%Y")
 return ""

def read_rows(path):
 workbook=load_workbook(path,read_only=True,data_only=True); worksheet=workbook.active; values=worksheet.values
 headers=[str(value).strip() if value is not None else "" for value in next(values)]
 result={}
 for source in values:
  row={headers[index]:serialise(value) for index,value in enumerate(source[:len(headers)]) if headers[index]}
  backlog_id=field(row,"Rückstand ID","Rueckstand ID")
  if backlog_id not in (None,""): result[str(backlog_id).strip()]=row
 return result

def comparison_text(data,names):
 parts=[]
 for name in names:
  value=field(data,name)
  parts.append(f"{name}: {str(value) if value not in (None, "") else '-'}")
 return " | ".join(parts)
def import_file(db,path):
 info=path.stat(); source_key=f"{path.resolve()}|{info.st_size}|{info.st_mtime_ns}"
 if db.scalar(select(BacklogImport.id).where(BacklogImport.source_key==source_key)): return None
 incoming=read_rows(path); mappings=sync_mapping_texts(db,incoming.values())
 for row in incoming.values(): apply_mapping(row,mappings.get(mapping_key(field(row,"Bemerkung OTLG"))))
 batch=BacklogImport(source_name=path.name,source_key=source_key,row_count=len(incoming)); db.add(batch); db.flush()
 active={item.backlog_id:item for item in db.scalars(select(Backlog)).all()}
 previous_active={backlog_id for backlog_id,item in active.items() if item.is_active}
 for backlog_id,row in incoming.items():
  current=active.get(backlog_id); previous_active.discard(backlog_id)
  delivery=field(row,"Liefertermin"); note=field(row,"Bemerkung OTLG"); creation=parse_date(field(row,"Anlagedatum"))
  delivery=str(delivery) if delivery is not None else None; note=str(note) if note is not None else None
  if not current:
   row["Ge\u00e4ndert"]="Nein"; row["Alte Information"]=""; row["Neue Information"]=""
   payload=json.dumps(row,ensure_ascii=False,default=str); db.add(BacklogImportRow(import_id=batch.id,backlog_id=backlog_id,data=payload))
   db.add(Backlog(backlog_id=backlog_id,creation_date=creation,delivery_date=delivery,otlg_note=note,data=payload,first_import_id=batch.id,last_import_id=batch.id)); db.add(BacklogChange(import_id=batch.id,backlog_id=backlog_id,change_type="Neu",after_data=payload)); batch.new_count+=1; continue
  before=current.data; before_row=json.loads(before); changed=[]
  if current.delivery_date!=delivery: changed.append("Liefertermin")
  if current.otlg_note!=note: changed.append("Bemerkung OTLG")
  if changed:
   row["Ge\u00e4ndert"]="Ja"; row["Alte Information"]=comparison_text(before_row,changed); row["Neue Information"]=comparison_text(row,changed)
  else:
   row["Ge\u00e4ndert"]="Nein"; row["Alte Information"]=""; row["Neue Information"]=""
  payload=json.dumps(row,ensure_ascii=False,default=str); db.add(BacklogImportRow(import_id=batch.id,backlog_id=backlog_id,data=payload))
  if changed:
   db.add(BacklogChange(import_id=batch.id,backlog_id=backlog_id,change_type="Ge\u00e4ndert",changed_fields=", ".join(changed),before_data=before,after_data=payload)); batch.changed_count+=1
  current.creation_date=creation or current.creation_date; current.delivery_date=delivery; current.otlg_note=note; current.data=payload; current.last_import_id=batch.id; current.is_active=True
 for missing_id in previous_active:
  missing=active[missing_id]
  missing.is_active=False; missing.last_import_id=batch.id; db.add(BacklogChange(import_id=batch.id,backlog_id=missing.backlog_id,change_type="Entfernt",before_data=missing.data)); batch.missing_count+=1
 db.commit(); return batch
def date_order(path):
 match=re.search(r"(\d{2})\.(\d{2})\.(\d{2,4})|(?<!\d)(\d{6})(?!\d)",path.name)
 if not match:return (9999,12,31,path.name)
 if match.group(4): return (2000+int(match.group(4)[4:]),int(match.group(4)[2:4]),int(match.group(4)[:2]),path.name)
 return (int(match.group(3))+(2000 if len(match.group(3))==2 else 0),int(match.group(2)),int(match.group(1)),path.name)

def import_folder(db):
 if not FOLDER.exists(): return [],"Der Rückstandsordner auf G: ist nicht erreichbar."
 reports=[]
 for path in sorted(FOLDER.glob("*.xlsx"),key=date_order):
  if path.name.startswith("~$"): continue
  try:
   batch=import_file(db,path)
   if batch: reports.append(f"{path.name}: {batch.new_count} neu, {batch.changed_count} geändert, {batch.missing_count} entfernt")
  except Exception as error:
   db.rollback(); reports.append(f"{path.name}: übersprungen ({error})")
 return reports,None

def group_statistics(records,key_name):
 today=date.today(); groups={}
 for item in records:
  data=json.loads(item.data); name=str(data.get(key_name) or "Nicht zugeordnet").strip() or "Nicht zugeordnet"; age=(today-item.creation_date.date()).days if item.creation_date else None
  groups.setdefault(name,[]).append(age)
 result=[]
 for name,ages in groups.items():
  known=[age for age in ages if age is not None]
  result.append({"name":name,"count":len(ages),"min_age":min(known) if known else None,"max_age":max(known) if known else None,"avg_age":round(sum(known)/len(known),1) if known else None})
 return sorted(result,key=lambda item:(-item["count"],item["name"]))
def dashboard_statistics(db):
 today=date.today(); active=list(db.scalars(select(Backlog).where(Backlog.is_active.is_(True))).all()); incomplete=sum(not item.measure or not item.category for item in db.scalars(select(OtlgMapping)).all()); measures=group_statistics(active,"Maßnahme"); categories={}
 for item in measures:
  related=[record for record in active if (str(json.loads(record.data).get("Maßnahme") or "").strip() or "Nicht zugeordnet")==item["name"]]
  categories[item["name"]]=group_statistics(related,"Kategorie")
 return {"backlog_total":len(active),"backlog_fresh":sum(bool(item.creation_date and item.creation_date.date()>=today-timedelta(days=7)) for item in active),"backlog_medium":sum(bool(item.creation_date and today-timedelta(days=30)<=item.creation_date.date()<today-timedelta(days=7)) for item in active),"backlog_old":sum(bool(item.creation_date and item.creation_date.date()<today-timedelta(days=30)) for item in active),"mapping_incomplete":incomplete,"measures":measures,"categories":categories}
def metrics(db): return dashboard_statistics(db)
@router.get("/backlogs",response_class=HTMLResponse)
def page(request:Request,notice:str|None=None,import_id:int|None=None,measure:str="",category:str="",db:Session=Depends(get_db)):
 records=list(db.scalars(select(Backlog).where(Backlog.is_active.is_(True)).order_by(Backlog.creation_date.desc(),Backlog.backlog_id)).all()); rows=[json.loads(record.data) for record in records]
 for row in rows: row.setdefault("Ge\u00e4ndert","Nein"); row.setdefault("Alte Information",""); row.setdefault("Neue Information","")
 columns=list(rows[0].keys()) if rows else []
 for column in ["Ge\u00e4ndert","Alte Information","Neue Information"]:
  if column not in columns: columns.append(column)
 imports=list(db.scalars(select(BacklogImport).order_by(BacklogImport.imported_at.desc()).limit(20)).all()); selected_import=next((item for item in imports if item.id==import_id),imports[0] if imports else None)
 changes=[]
 if selected_import:
  for item in db.scalars(select(BacklogChange).where(BacklogChange.import_id==selected_import.id).order_by(BacklogChange.change_type,BacklogChange.backlog_id)).all():
   before=json.loads(item.before_data) if item.before_data else {}; after=json.loads(item.after_data) if item.after_data else {}
   changes.append({"backlog_id":item.backlog_id,"change_type":item.change_type,"changed_fields":item.changed_fields or "–","delivery_before":field(before,"Liefertermin") or "–","delivery_after":field(after,"Liefertermin") or "–","otlg_before":field(before,"Bemerkung OTLG") or "–","otlg_after":field(after,"Bemerkung OTLG") or "–"})
 return templates.TemplateResponse(request,"backlogs.html",{"rows":rows,"columns":columns,"imports":imports,"latest":selected_import,"changes":changes,"notice":notice,"initial_filters":{"Maßnahme":measure,"Kategorie":category}})
@router.post("/backlogs/import")
def import_all(db:Session=Depends(get_db)):
 reports,error=import_folder(db); message=error or ("; ".join(reports) if reports else "Keine neue Tagesdatei gefunden.")
 return RedirectResponse("/backlogs?notice="+message,303)
















