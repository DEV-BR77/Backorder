from datetime import datetime
from pathlib import Path
import secrets
from urllib.parse import parse_qsl
from fastapi import Depends,FastAPI,Form,HTTPException,Request,status
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.security import HTTPBasic,HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import get_settings
from .database import Base,engine,get_db
from .models import ODataService
from .odata import request_odata

SOURCE_XLSX=Path(r"C:\Users\radke2\Documents\ODATA.xlsx")
app=FastAPI(title="Rueckstandslisten")
app.mount("/static",StaticFiles(directory=Path(__file__).parent/"static"),name="static")
templates=Jinja2Templates(directory=Path(__file__).parent/"templates"); security=HTTPBasic()

def as_bool(value): return str(value).strip().lower() in {"ja","yes","true","1"}
def import_services(db):
 if db.scalar(select(ODataService.id).limit(1)) or not SOURCE_XLSX.exists(): return 0
 ws=load_workbook(SOURCE_XLSX,read_only=True,data_only=True)["Adressen"]
 rows=ws.values; headers=[str(v).strip() if v else "" for v in next(rows)]; added=0
 for row in rows:
  item=dict(zip(headers,row)); name=item.get("Servicename")
  if not name: continue
  db.add(ODataService(object_type=item.get("Objektart"),object_id=int(item["Objekt-ID"]) if item.get("Objekt-ID") is not None else None,object_name=item.get("Objektname"),service_name=str(name),all_tenants=as_bool(item.get("Alle Tenants")),published=as_bool(item.get("Veröffentlicht")),odata_v4_url=item.get("OData V4-URL"),odata_url=item.get("OData-URL"),soap_url=item.get("SOAP-URL"))); added+=1
 db.commit(); return added
@app.on_event("startup")
def startup():
 Base.metadata.create_all(engine)
 with Session(engine) as db: import_services(db)
def require_admin(c:HTTPBasicCredentials=Depends(security)):
 s=get_settings()
 if not s.admin_username or not s.admin_password: raise HTTPException(503,"ADMIN_USERNAME und ADMIN_PASSWORD muessen gesetzt sein.")
 if not(secrets.compare_digest(c.username,s.admin_username) and secrets.compare_digest(c.password,s.admin_password)): raise HTTPException(status.HTTP_401_UNAUTHORIZED,"Nicht berechtigt",headers={"WWW-Authenticate":"Basic"})
def services(db): return list(db.scalars(select(ODataService).order_by(ODataService.service_name)))
def form_values(object_type,object_id,object_name,service_name,all_tenants,published,v4,v3,soap):
 return {"object_type":object_type or None,"object_id":int(object_id) if object_id else None,"object_name":object_name or None,"service_name":service_name,"all_tenants":all_tenants=="on","published":published=="on","odata_v4_url":v4 or None,"odata_url":v3 or None,"soap_url":soap or None}
@app.get("/",response_class=HTMLResponse)
def dashboard(request:Request,db:Session=Depends(get_db)):
 rows=services(db); return templates.TemplateResponse(request,"dashboard.html",{"services":rows,"configured":sum(bool(x.odata_v4_url) for x in rows),"healthy":sum(x.last_success_at is not None and not x.last_error for x in rows)})
@app.get("/odata/query",response_class=HTMLResponse)
def query_page(request:Request,service_id:int|None=None,db:Session=Depends(get_db)):
 return templates.TemplateResponse(request,"query.html",{"services":services(db),"selected":service_id,"result":None,"message":None,"inputs":{}})
@app.post("/odata/query",response_class=HTMLResponse)
def query_page_post(request:Request,service_id:int=Form(...),filter_value:str=Form(""),select_value:str=Form(""),expand_value:str=Form(""),extra_params:str=Form(""),db:Session=Depends(get_db)):
 p=dict(parse_qsl(extra_params.lstrip("?"),keep_blank_values=True)); p.setdefault("$top","100")
 if filter_value.strip(): p["$filter"]=filter_value.strip()
 if select_value.strip(): p["$select"]=select_value.strip()
 if expand_value.strip(): p["$expand"]=expand_value.strip()
 service=db.get(ODataService,service_id); ok,message,rows=request_odata(service,p) if service else (False,"Dienst nicht gefunden.",[]); db.commit()
 columns=sorted({key for row in rows if isinstance(row,dict) for key in row})
 return templates.TemplateResponse(request,"query.html",{"services":services(db),"selected":service_id,"result":{"rows":rows,"columns":columns} if ok else None,"message":message,"inputs":{"filter":filter_value,"select":select_value,"expand":expand_value,"extra":extra_params}})
@app.get("/admin/odata",response_class=HTMLResponse,dependencies=[Depends(require_admin)])
def manage(request:Request,db:Session=Depends(get_db)):
 return templates.TemplateResponse(request,"odata.html",{"services":services(db),"edit":None,"message":None})
@app.get("/admin/odata/{sid}",response_class=HTMLResponse,dependencies=[Depends(require_admin)])
def edit_service(sid:int,request:Request,db:Session=Depends(get_db)):
 return templates.TemplateResponse(request,"odata.html",{"services":services(db),"edit":db.get(ODataService,sid),"message":None})
@app.post("/admin/odata",dependencies=[Depends(require_admin)])
def create_service(object_type:str=Form(""),object_id:str=Form(""),object_name:str=Form(""),service_name:str=Form(...),all_tenants:str=Form(""),published:str=Form(""),odata_v4_url:str=Form(""),odata_url:str=Form(""),soap_url:str=Form(""),db:Session=Depends(get_db)):
 db.add(ODataService(**form_values(object_type,object_id,object_name,service_name,all_tenants,published,odata_v4_url,odata_url,soap_url))); db.commit(); return RedirectResponse("/admin/odata",303)
@app.post("/admin/odata/{sid}",dependencies=[Depends(require_admin)])
def update_service(sid:int,object_type:str=Form(""),object_id:str=Form(""),object_name:str=Form(""),service_name:str=Form(...),all_tenants:str=Form(""),published:str=Form(""),odata_v4_url:str=Form(""),odata_url:str=Form(""),soap_url:str=Form(""),db:Session=Depends(get_db)):
 x=db.get(ODataService,sid)
 if not x: raise HTTPException(404)
 for k,v in form_values(object_type,object_id,object_name,service_name,all_tenants,published,odata_v4_url,odata_url,soap_url).items(): setattr(x,k,v)
 db.commit(); return RedirectResponse("/admin/odata",303)
@app.post("/admin/odata/{sid}/delete",dependencies=[Depends(require_admin)])
def delete_service(sid:int,db:Session=Depends(get_db)):
 x=db.get(ODataService,sid)
 if not x: raise HTTPException(404)
 db.delete(x); db.commit(); return RedirectResponse("/admin/odata",303)
@app.post("/admin/odata/{sid}/test",dependencies=[Depends(require_admin)])
def test_service(sid:int,db:Session=Depends(get_db)):
 x=db.get(ODataService,sid)
 if not x: raise HTTPException(404)
 ok,message,_=request_odata(x,{"$top":"1"}); db.commit(); return {"ok":ok,"message":message}
@app.get("/health")
def health(): return {"status":"ok","timestamp":datetime.utcnow().isoformat()}



