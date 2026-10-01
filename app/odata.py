from datetime import datetime
from urllib.parse import urlsplit, urlunsplit
from xml.etree import ElementTree
import requests
try:
 from requests_negotiate_sspi import HttpNegotiateAuth
except ImportError:
 HttpNegotiateAuth = None

def windows_auth():
 if HttpNegotiateAuth is None: raise RuntimeError("requests-negotiate-sspi ist nicht installiert.")
 return HttpNegotiateAuth()

def metadata_url(service):
 parts=urlsplit(service.odata_v4_url); marker="/ODataV4/"
 path=parts.path.split(marker,1)[0]+marker if marker in parts.path else parts.path.rsplit("/",1)[0]+"/"
 return urlunsplit((parts.scheme,parts.netloc,path+"$metadata","",""))

def service_schema(service):
 if not service.odata_v4_url: return False,"Keine OData-V4-URL hinterlegt.",{"fields":[],"expands":[]}
 try:
  response=requests.get(metadata_url(service),auth=windows_auth(),timeout=25); response.raise_for_status()
  root=ElementTree.fromstring(response.content); ns={"edm":"http://docs.oasis-open.org/odata/ns/edm"}
  endpoint_name=urlsplit(service.odata_v4_url).path.rstrip("/").rsplit("/",1)[-1]
  entity_set=next((root.find(".//edm:EntitySet[@Name='%s']" % name,ns) for name in (service.service_name,endpoint_name) if root.find(".//edm:EntitySet[@Name='%s']" % name,ns) is not None),None)
  entity_type=entity_set.get("EntityType").split(".")[-1] if entity_set is not None else service.service_name
  entity=root.find(".//edm:EntityType[@Name='%s']" % entity_type,ns)
  if entity is None:
   # Some published BC services use a service alias which differs from the EDM entity name.
   # Use a harmless sample row and select the metadata entity with the most matching properties.
   sample=requests.get(service.odata_v4_url,params={"$top":1},auth=windows_auth(),timeout=25).json().get("value",[])
   keys=set(sample[0].keys()) if sample and isinstance(sample[0],dict) else set()
   candidates=root.findall(".//edm:EntityType",ns)
   entity=max(candidates,key=lambda item:len(keys & {p.get("Name") for p in item.findall("edm:Property",ns)}),default=None)
   if entity is None or not keys or not entity.findall("edm:Property",ns): return False,"Der Entitätstyp wurde in den Metadaten nicht gefunden.",{"fields":[],"expands":[]}
  return True,"Metadaten geladen.",{"fields":[{"name":x.get("Name"),"type":x.get("Type", "Edm.String")} for x in entity.findall("edm:Property",ns)],"expands":[x.get("Name") for x in entity.findall("edm:NavigationProperty",ns)]}
 except (requests.RequestException,ElementTree.ParseError,RuntimeError,ValueError) as e:
  return False,f"Metadaten konnten nicht geladen werden: {e}",{"fields":[],"expands":[]}

def request_odata(service,params):
 if not service.odata_v4_url: return False,"Keine OData-V4-URL hinterlegt.",[]
 try:
  r=requests.get(service.odata_v4_url,params=params,headers={"Accept":"application/json"},auth=windows_auth(),timeout=25)
  r.raise_for_status(); body=r.json(); rows=body.get("value",body if isinstance(body,list) else [])
  service.last_success_at=datetime.utcnow(); service.last_error=None
  return True,f"Abfrage erfolgreich ({r.status_code}).",rows
 except (requests.RequestException,ValueError,RuntimeError) as e:
  service.last_error=str(e)[:2000]; return False,f"Abfrage fehlgeschlagen: {e}",[]

def insert_odata(service,payload):
 if not service.odata_v4_url: return False,"Keine OData-V4-URL hinterlegt.",None
 try:
  response=requests.post(service.odata_v4_url,json=payload,headers={"Accept":"application/json","Content-Type":"application/json"},auth=windows_auth(),timeout=25)
  response.raise_for_status(); service.last_success_at=datetime.utcnow(); service.last_error=None
  try: body=response.json()
  except ValueError: body=None
  return True,f"Datensatz in BC angelegt ({response.status_code}).",body
 except (requests.RequestException,ValueError,RuntimeError) as error:
  service.last_error=str(error)[:2000]; return False,f"Einfügen in BC fehlgeschlagen: {error}",None

