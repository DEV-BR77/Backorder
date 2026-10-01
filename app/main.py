from datetime import datetime, date, timedelta
from io import BytesIO
import json
import re
from pathlib import Path
import secrets
from types import SimpleNamespace
from fastapi import Depends,FastAPI,Form,HTTPException,Request,status
from fastapi.responses import HTMLResponse,RedirectResponse,StreamingResponse
from fastapi.security import HTTPBasic,HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openpyxl import Workbook,load_workbook
from sqlalchemy import inspect,select
from sqlalchemy.orm import Session
from .config import get_settings
from .database import Base,engine,get_db
from .models import ODataService
from .odata import insert_odata,request_odata,service_schema
from .backlogs import metrics as backlog_metrics, router as backlogs_router
from .mapping_admin import router as mappings_router

SOURCE_XLSX=Path(r"C:\Users\radke2\Documents\ODATA.xlsx")
app=FastAPI(title="Rueckstandslisten")
app.router.include_router(backlogs_router)
app.router.include_router(mappings_router)
app.mount("/static",StaticFiles(directory=Path(__file__).parent/"static"),name="static")
templates=Jinja2Templates(directory=Path(__file__).parent/"templates"); security=HTTPBasic()
def as_bool(value): return str(value).strip().lower() in {"ja","yes","true","1"}
def import_services(db):
 if db.scalar(select(ODataService.id).limit(1)) or not SOURCE_XLSX.exists(): return
 ws=load_workbook(SOURCE_XLSX,read_only=True,data_only=True)["Adressen"]; rows=ws.values; headers=[str(v).strip() if v else "" for v in next(rows)]
 for row in rows:
  item=dict(zip(headers,row)); name=item.get("Servicename")
  if name: db.add(ODataService(object_type=item.get("Objektart"),object_id=int(item["Objekt-ID"]) if item.get("Objekt-ID") is not None else None,object_name=item.get("Objektname"),service_name=str(name),all_tenants=as_bool(item.get("Alle Tenants")),published=as_bool(item.get("Veröffentlicht")),odata_v4_url=item.get("OData V4-URL"),odata_url=item.get("OData-URL"),soap_url=item.get("SOAP-URL")))
 db.commit()
@app.on_event("startup")
def startup():
 Base.metadata.create_all(engine)
 if "group_name" not in [c["name"] for c in inspect(engine).get_columns("odata_services")]:
  with engine.begin() as cn: cn.exec_driver_sql("ALTER TABLE odata_services ADD COLUMN group_name VARCHAR(120)")
 with Session(engine) as db: import_services(db)
def require_admin(c:HTTPBasicCredentials=Depends(security)):
 s=get_settings()
 if not s.admin_username or not s.admin_password: raise HTTPException(503,"ADMIN_USERNAME und ADMIN_PASSWORD müssen gesetzt sein.")
 if not(secrets.compare_digest(c.username,s.admin_username) and secrets.compare_digest(c.password,s.admin_password)): raise HTTPException(status.HTTP_401_UNAUTHORIZED,"Nicht berechtigt",headers={"WWW-Authenticate":"Basic"})
def services(db): return list(db.scalars(select(ODataService).order_by(ODataService.group_name,ODataService.service_name)))
def unique_service_name(db,requested,exclude_id=None):
 base=requested.strip(); candidate=base; suffix=2
 while True:
  existing=db.scalar(select(ODataService.id).where(ODataService.service_name==candidate))
  if existing is None or existing==exclude_id: return candidate
  candidate=f"{base}-{suffix}"; suffix+=1
def form_values(group_name,object_type,object_id,object_name,service_name,all_tenants,published,v4,v3,soap): return {"group_name":group_name.strip() or None,"object_type":object_type or None,"object_id":int(object_id) if object_id else None,"object_name":object_name or None,"service_name":service_name.strip(),"all_tenants":all_tenants=="on","published":published=="on","odata_v4_url":v4.strip() or None,"odata_url":v3.strip() or None,"soap_url":soap.strip() or None}
def temp_service(url): return SimpleNamespace(odata_v4_url=url,service_name=url.rstrip("/").split("/")[-1],last_success_at=None,last_error=None)
def literal(value,t): return value.lower() if t=="Edm.Boolean" else value if t in {"Edm.Int16","Edm.Int32","Edm.Int64","Edm.Decimal","Edm.Double"} else "'"+value.replace("'","''")+"'"
def make_rows(rows, expands, mode):
 if mode!="combined" or not expands: return rows
 result=[]
 for row in rows:
  item={k:v for k,v in row.items() if k not in expands}
  for relation in expands:
   value=row.get(relation,[])
   if isinstance(value,list):
    values={}
    for child in value:
     for key,val in child.items(): values.setdefault(key,[]).append(str(val))
    for key,val in values.items(): item[f"{relation}.{key}"]=" | ".join(val)
   elif isinstance(value,dict):
    for key,val in value.items(): item[f"{relation}.{key}"]=val
  result.append(item)
 return result
@app.get("/",response_class=HTMLResponse)
def dashboard(request:Request,db:Session=Depends(get_db)):
 rows=services(db); values={"services":rows,"configured":sum(bool(x.odata_v4_url) for x in rows),"healthy":sum(x.last_success_at is not None and not x.last_error for x in rows)}; values.update(backlog_metrics(db)); return templates.TemplateResponse(request,"dashboard.html",values)
@app.get("/odata/query",response_class=HTMLResponse)
def query_page(request:Request,db:Session=Depends(get_db)): return templates.TemplateResponse(request,"query.html",{"services":services(db),"selected":None,"result":None,"message":None,"inputs":{}})
@app.get("/odata/schema")
def schema(service_id:int|None=None,url:str|None=None,db:Session=Depends(get_db)):
 service=db.get(ODataService,service_id) if service_id else temp_service(url) if url else None
 if not service: raise HTTPException(400,"Dienst oder URL erforderlich.")
 ok,message,data=service_schema(service); return {"ok":ok,"message":message,**data}
@app.post("/odata/query",response_class=HTMLResponse)
def query_page_post(request:Request,service_id:int|None=Form(None),manual_url:str=Form(""),filter_field:str=Form(""),filter_operator:str=Form("eq"),filter_input:str=Form(""),select_fields:list[str]=Form([]),expand_tables:list[str]=Form([]),expand_mode:str=Form("individual"),use_top:str=Form(""),top_value:str=Form("100"),use_orderby:str=Form(""),orderby_field:str=Form(""),orderby_direction:str=Form("asc"),db:Session=Depends(get_db)):
 service=temp_service(manual_url.strip()) if manual_url.strip() else db.get(ODataService,service_id) if service_id else None
 if not service: return templates.TemplateResponse(request,"query.html",{"services":services(db),"selected":service_id,"result":None,"message":"Bitte einen Dienst oder eine OData-V4-URL angeben.","inputs":{}})
 _,_,schema_data=service_schema(service); types={x["name"]:x["type"] for x in schema_data.get("fields",[]) if isinstance(x,dict)}; p={}
 if use_top=="on" and top_value.strip(): p["$top"]=top_value.strip()
 if filter_field and filter_input.strip(): p["$filter"]=f"{filter_operator}({filter_field},{literal(filter_input.strip(),types.get(filter_field,'Edm.String'))})" if filter_operator in {"contains","startswith"} else f"{filter_field} {filter_operator} {literal(filter_input.strip(),types.get(filter_field,'Edm.String'))}"
 if select_fields: p["$select"]=",".join(select_fields)
 if expand_tables: p["$expand"]=",".join(expand_tables)
 if use_orderby=="on" and orderby_field: p["$orderby"]=orderby_field+(" desc" if orderby_direction=="desc" else "")
 ok,message,raw_rows=request_odata(service,p)
 if isinstance(service,ODataService): db.commit()
 rows=make_rows(raw_rows,expand_tables,expand_mode); columns=sorted({k for row in rows if isinstance(row,dict) for k in row} - set(expand_tables if expand_mode=="individual" else []))
 return templates.TemplateResponse(request,"query.html",{"services":services(db),"selected":service_id,"result":{"rows":rows,"columns":columns,"raw_rows":raw_rows,"expands":expand_tables,"mode":expand_mode} if ok else None,"message":message,"inputs":{"manual_url":manual_url,"filter_field":filter_field,"filter_operator":filter_operator,"filter_input":filter_input,"select_fields":select_fields,"expand_tables":expand_tables,"expand_mode":expand_mode,"use_top":use_top,"top_value":top_value,"use_orderby":use_orderby,"orderby_field":orderby_field,"orderby_direction":orderby_direction}})
@app.post("/odata/export")
def export_odata(payload:str=Form(...)):
 data=json.loads(payload); book=Workbook(); book.remove(book.active)
 for sheet_name,rows in data.get("sheets",{}).items():
  sheet=book.create_sheet((sheet_name or "Ergebnis")[:31]); columns=sorted({key for row in rows if isinstance(row,dict) for key in row}) or ["Keine Daten"]
  sheet.append(columns)
  for cell in sheet[1]: cell.font=__import__("openpyxl").styles.Font(bold=True)
  for row in rows: sheet.append([str(row.get(key,"")) if isinstance(row.get(key),(dict,list)) else row.get(key,"") for key in columns])
  sheet.freeze_panes="A2"; sheet.auto_filter.ref=sheet.dimensions
  for column in sheet.columns: sheet.column_dimensions[column[0].column_letter].width=min(45,max(12,max(len(str(cell.value or "")) for cell in column)+2))
 output=BytesIO(); book.save(output); output.seek(0)
 return StreamingResponse(output,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers={"Content-Disposition":"attachment; filename=odata-ergebnis.xlsx"})
@app.get("/admin/odata",response_class=HTMLResponse,dependencies=[Depends(require_admin)])
def manage(request:Request,notice:str|None=None,db:Session=Depends(get_db)): return templates.TemplateResponse(request,"odata.html",{"services":services(db),"notice":notice})
@app.post("/admin/odata",dependencies=[Depends(require_admin)])
def create_service(group_name:str=Form(""),object_type:str=Form(""),object_id:str=Form(""),object_name:str=Form(""),service_name:str=Form(...),all_tenants:str=Form(""),published:str=Form(""),odata_v4_url:str=Form(""),odata_url:str=Form(""),soap_url:str=Form(""),db:Session=Depends(get_db)):
 values=form_values(group_name,object_type,object_id,object_name,service_name,all_tenants,published,odata_v4_url,odata_url,soap_url)
 known_url=db.scalar(select(ODataService.id).where(ODataService.odata_v4_url==values["odata_v4_url"])) if values["odata_v4_url"] else None
 if known_url: return RedirectResponse("/admin/odata?notice=Adresse+ist+bereits+gespeichert",303)
 values["service_name"]=unique_service_name(db,values["service_name"]); db.add(ODataService(**values)); db.commit(); return RedirectResponse("/admin/odata?notice=Adresse+gespeichert",303)
@app.post("/admin/odata/{sid}",dependencies=[Depends(require_admin)])
def update_service(sid:int,group_name:str=Form(""),object_type:str=Form(""),object_id:str=Form(""),object_name:str=Form(""),service_name:str=Form(...),all_tenants:str=Form(""),published:str=Form(""),odata_v4_url:str=Form(""),odata_url:str=Form(""),soap_url:str=Form(""),db:Session=Depends(get_db)):
 item=db.get(ODataService,sid)
 if not item: raise HTTPException(404)
 values=form_values(group_name,object_type,object_id,object_name,service_name,all_tenants,published,odata_v4_url,odata_url,soap_url); values["service_name"]=unique_service_name(db,values["service_name"],sid)
 for k,v in values.items(): setattr(item,k,v)
 db.commit(); return RedirectResponse("/admin/odata?notice=Adresse+gespeichert",303)
@app.post("/admin/odata/selection/delete",dependencies=[Depends(require_admin)])
def delete_selected(service_ids:list[int]=Form(...),db:Session=Depends(get_db)):
 for item in db.scalars(select(ODataService).where(ODataService.id.in_(service_ids))).all(): db.delete(item)
 db.commit(); return RedirectResponse("/admin/odata",303)
@app.post("/admin/odata/selection/test",dependencies=[Depends(require_admin)])
def test_selected(service_ids:list[int]=Form(...),db:Session=Depends(get_db)):
 if len(service_ids)!=1: return {"ok":False,"message":"Bitte genau eine Adresse auswählen."}
 item=db.get(ODataService,service_ids[0]); ok,message,_=request_odata(item,{"$top":"1"}); db.commit(); return {"ok":ok,"message":message}
@app.get("/health")
def health(): return {"status":"ok","timestamp":datetime.utcnow().isoformat()}





def backlog_test_service(db):
 return next((item for item in services(db) if item.service_name.casefold()=="backlog_test"),None)
def render_backlog_test(request,db,service,message=None,submitted=None):
 if not service: return templates.TemplateResponse(request,"backlog_test.html",{"service":None,"fields":[],"message":"Der OData-Dienst BACKLOG_Test ist nicht gespeichert.","submitted":submitted})
 ok,schema_message,schema=service_schema(service)
 return templates.TemplateResponse(request,"backlog_test.html",{"service":service,"fields":schema.get("fields",[]) if ok else [],"message":message or schema_message,"submitted":submitted})
@app.get("/backlogs/bc-test",response_class=HTMLResponse,dependencies=[Depends(require_admin)])
def backlog_test_page(request:Request,db:Session=Depends(get_db)):
 return render_backlog_test(request,db,backlog_test_service(db))
@app.post("/backlogs/bc-test",response_class=HTMLResponse,dependencies=[Depends(require_admin)])
async def backlog_test_insert(request:Request,service_id:int=Form(...),db:Session=Depends(get_db)):
 service=db.get(ODataService,service_id)
 if not service: return render_backlog_test(request,db,None,"Der ausgewählte Dienst wurde nicht gefunden.")
 ok,schema_message,schema=service_schema(service)
 if not ok: return render_backlog_test(request,db,service,schema_message)
 form=await request.form(); payload={}
 for definition in schema.get("fields",[]):
  name=definition["name"]; raw=str(form.get(name,"")).strip()
  if not raw: continue
  payload[name]=(raw.lower()=="true") if definition.get("type")=="Edm.Boolean" else raw
 if not payload: return render_backlog_test(request,db,service,"Bitte mindestens ein Feld für den Testdatensatz ausfüllen.")
 inserted,message,_=insert_odata(service,payload); db.commit()
 return render_backlog_test(request,db,service,message,payload)
