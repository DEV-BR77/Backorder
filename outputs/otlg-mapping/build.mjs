import fs from "node:fs/promises";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";
const outputDir="outputs/otlg-mapping";
const source=JSON.parse(await fs.readFile(`${outputDir}/source.json`,"utf8"));
const normalize=value=>String(value).toLowerCase().replace(/\s+/g," ").trim();
const manual=new Map([
["Derzeit ist eine Lieferterminaussage seitens Lieferant noch nicht möglich, wir informieren Sie per PARDS sobald sich die Situation ändert.",["","Monitoring","Rückstand"]],
["Engpasssteuerung, keine Lieferterminaussage möglich",["","Monitoring","Rückstand"]],
["Die Position ist beim Lieferanten in Kassel vorrätig und wird in 1-2 Tagen ausgeliefert.",["3-4 Werktage","Kassel","Bestand Lieferant"]],
["Die Position ist beim Lieferanten in Spanien vorrätig und wird in der regulären Durchlaufzeit von 4-5 Tagen ausgeliefert.",["5-6 Werktage","Spanien","Bestand Lieferant"]],
["Sonderbeschaffung aus anderem VZ",["","Monitoring","Sonderbeschaffung"]],
["keine Sonderbeschaffung möglich",["","Monitoring","Rückstand"]],
["Die Position ist beim Lieferanten in Tschechien vorrätig und wird in der regulären Durchlaufzeit von 3-4 Tagen ausgeliefert.",["4-5 Werktage","Tschechien","Bestand Lieferant"]],
["Auslieferung geplant für KW40/41",["avisierte max. KW+1 = KW42","Mail Kunde","KW-Avis"]],
["Auslieferung geplant für KW 38/39",["avisierte max. KW+1 = KW40","Mail Kunde","KW-Avis"]],
["Liefertermin beim Lieferanten in Klärung",["","Monitoring","Lieferantenanfrage"]],
["Planlieferzeit ca. 15 Tage nach Auftragseingang",["=Anlagedatum + Tage aus Bemerkung +2 Tage","Plan","Planlieferzeit"]],
["Derzeit ist eine Lieferterminaussage seitens Lieferanten noch nicht möglich",["","Monitoring","Rückstand"]],
["Auslieferung geplant für KW 39-40",["KW41","Mail Kunde","KW-Avis"]],
["Auslieferung geplant für KW 39/40",["KW41","Mail Kunde","KW-Avis"]],
["Derzeit ist eine Lieferterminaussage seitens Lieferant noch nicht möglich, wir informieren Sie per Pards sobald sich die Situation ändert.",["","Monitoring","Rückstand"]],
["Auslieferung geplant für KW39/40",["KW41","Mail Kunde","KW-Avis"]],
["Engpasssteuerung",["","Monitoring","Rückstand"]],
["Auslieferung geplant für KW 41/42",["KW43","Mail Kunde","KW-Avis"]]
].map(([text,values])=>[normalize(text),values]));
const workbook=Workbook.create(); const mapping=workbook.worksheets.add("OTLG Mapping"); const changes=workbook.worksheets.add("Änderungen je Datei"); const navy="#11253F",pale="#EAF1F7",line="#D8E0E8";
for(const sheet of [mapping,changes]){sheet.showGridLines=false;sheet.tabColor=navy;}
mapping.getRange("A2:H2").merge(); mapping.getRange("A2").values=[["OTLG-Texte, Terminlogik und Kategorie"]]; mapping.getRange("A2").format={font:{name:"Arial",size:14,bold:true,color:navy}};
mapping.getRange("A4:B8").values=[["Unterschiedliche Texte",source.summary.distinct_texts],["Textvorkommen",source.summary.text_occurrences],["Importdateien",source.summary.imports],["Pflegehinweis","Spalte E: Ergebnis; Spalte F: automatisierte Regel; Spalten G/H: Maßnahme und verbindliche Kategorie."],["Hinweis","Unbearbeitete Texte bitte in F–H ergänzen."]]; mapping.getRange("A4:A8").format={fill:pale,font:{name:"Arial",bold:true,color:navy}};mapping.getRange("A4:B8").format.borders={preset:"all",style:"thin",color:line};mapping.getRange("B7:B8").format.wrapText=true;
const headers=["Originaltext","Häufigkeit","Beispiel Rückstand ID","Vorschlag Kategorie","Avisierter Liefertermin","Regel (automatisiertes Mapping)","Maßnahme","Kategorie (manuell)"];
const formatDate=value=>`${String(value.getDate()).padStart(2,"0")}.${String(value.getMonth()+1).padStart(2,"0")}.${value.getFullYear()}`;
const rows=source.mapping.map(item=>{
 const [configuredRule,configuredMeasure,configuredCategory]=manual.get(normalize(item.Originaltext))||["","",""];
 const text=item.Originaltext; let measure=configuredMeasure, category=configuredCategory, announced="", rule=configuredRule;
 const weekBlocks=[...text.matchAll(/\bKW\s*(\d{1,2}(?:\s*[/.-]\s*\d{1,2})*)/gi)]; const weeks=weekBlocks.flatMap(match=>[...match[1].matchAll(/\d{1,2}/g)].map(value=>Number(value[0]))); const days=text.match(/Planlieferzeit[^\d]*(\d+)\s*Tage/i); const location=text.match(/Lieferanten in (Kassel|Spanien|Tschechien)/i);
 if(weeks.length){announced=`KW ${Math.max(...weeks)+1}`; rule="Höchste KW aus dem Text + 1"; measure="Mail Kunde"; category="KW-Avis";}
 if(days){const base=new Date(String(item['Beispiel Anlagedatum']||'')); announced=Number.isNaN(base.valueOf())?"":formatDate(new Date(base.setDate(base.getDate()+Number(days[1])+2))); rule=`Anlagedatum + ${days[1]} Tage aus Bemerkung + 2 Tage`; measure="Plan"; category="Planlieferzeit";}
 if(location){measure=location[1][0].toUpperCase()+location[1].slice(1).toLowerCase(); category="Bestand Lieferant"; const duration=text.match(/(\d+)\s*-\s*(\d+)\s*Tagen?/i); if(duration) rule=`Textdauer + 1 Werktag (${Number(duration[1])+1}-${Number(duration[2])+1} Werktage)`;}
 if(/derzeit ist eine lieferterminaussage|engpasssteuerung|keine sonderbeschaffung möglich/i.test(text)){measure="Monitoring";category="Rückstand";}
 if(/sonderbeschaffung aus anderem/i.test(text)){measure="Monitoring";category="Sonderbeschaffung";}
 if(/liefertermin beim lieferanten in klärung/i.test(text)){measure="Monitoring";category="Lieferantenanfrage";}
 return [item.Originaltext,item.Häufigkeit,item['Beispiel Rückstand ID'],item['Vorschlag Kategorie'],announced,rule,measure,category];
});mapping.getRangeByIndexes(9,0,1,headers.length).values=[headers];mapping.getRangeByIndexes(10,0,rows.length,headers.length).values=rows;const table=mapping.tables.add(`A10:H${10+rows.length}`,true,"OtlGMappingTable");table.style="TableStyleMedium2";mapping.freezePanes.freezeRows(10);mapping.getRange(`A11:A${10+rows.length}`).format.wrapText=true;mapping.getRange(`F11:H${10+rows.length}`).format.fill="#FFF2CC";mapping.getRange(`B11:C${10+rows.length}`).format.horizontalAlignment="right";
[["A:A",58],["B:B",12],["C:C",20],["D:D",21],["E:E",26],["F:F",42],["G:G",18],["H:H",24]].forEach(([r,w])=>mapping.getRange(r).format.columnWidth=w);
changes.getRange("A2:H2").merge();changes.getRange("A2").values=[["Änderungen pro Importdatei und Rückstand-ID"]];changes.getRange("A2").format={font:{name:"Arial",size:14,bold:true,color:navy}};changes.getRange("A4:B5").values=[["Änderungen",source.summary.changes],["Hinweis","Nach Datei, Rückstand ID oder Änderungsart filtern."]];changes.getRange("A4:A5").format={fill:pale,font:{name:"Arial",bold:true,color:navy}};changes.getRange("A4:B5").format.borders={preset:"all",style:"thin",color:line};
const changeHeaders=["Datei","Rückstand ID","Änderungsart","Geänderte Felder","Liefertermin vorher","Liefertermin nachher","Bemerkung OTLG vorher","Bemerkung OTLG nachher"];changes.getRangeByIndexes(7,0,1,changeHeaders.length).values=[changeHeaders];changes.getRangeByIndexes(8,0,source.changes.length,changeHeaders.length).values=source.changes.map(row=>changeHeaders.map(header=>row[header]??""));const changeTable=changes.tables.add(`A8:H${8+source.changes.length}`,true,"BacklogChangesTable");changeTable.style="TableStyleMedium2";changes.freezePanes.freezeRows(8);changes.getRange(`G9:H${8+source.changes.length}`).format.wrapText=true;[["A:A",28],["B:B",18],["C:C",15],["D:D",25],["E:F",20],["G:H",58]].forEach(([r,w])=>changes.getRange(r).format.columnWidth=w);
workbook.recalculate();const check=await workbook.inspect({kind:"table",range:"OTLG Mapping!A2:H30",include:"values,formulas",tableMaxRows:30,tableMaxCols:8});console.log(check.ndjson);const image=await workbook.render({sheetName:"OTLG Mapping",range:"A1:H30",scale:1.2,format:"png"});await fs.writeFile(`${outputDir}/preview.png`,new Uint8Array(await image.arrayBuffer()));const file=await SpreadsheetFile.exportXlsx(workbook);await file.save(`${outputDir}/otlg-textmapping-vollstaendig.xlsx`);










