from datetime import datetime
import requests
try:
 from requests_negotiate_sspi import HttpNegotiateAuth
except ImportError:
 HttpNegotiateAuth = None

def windows_auth():
 if HttpNegotiateAuth is None:
  raise RuntimeError("requests-negotiate-sspi ist nicht installiert.")
 return HttpNegotiateAuth()

def request_odata(service, params):
 if not service.odata_v4_url: return False,"Keine OData-V4-URL hinterlegt.",[]
 try:
  r=requests.get(service.odata_v4_url,params=params,headers={"Accept":"application/json"},auth=windows_auth(),timeout=25)
  r.raise_for_status(); body=r.json(); rows=body.get("value",body if isinstance(body,list) else [])
  service.last_success_at=datetime.utcnow(); service.last_error=None
  return True,f"Abfrage erfolgreich ({r.status_code}).",rows
 except (requests.RequestException,ValueError,RuntimeError) as e:
  service.last_error=str(e)[:2000]; return False,f"Abfrage fehlgeschlagen: {e}",[]
