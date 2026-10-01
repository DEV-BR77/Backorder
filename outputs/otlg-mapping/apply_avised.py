import json
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import engine
from app.models import Backlog
from app.backlogs import announced_delivery

db=Session(engine)
for item in db.scalars(select(Backlog)).all():
 data=json.loads(item.data); data["Avisiertes Lieferdatum"]=announced_delivery(data); item.data=json.dumps(data,ensure_ascii=False)
db.commit(); db.close()
