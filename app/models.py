from datetime import datetime
from sqlalchemy import Boolean,DateTime,Integer,String,Text
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base

class ODataService(Base):
 __tablename__="odata_services"
 id:Mapped[int]=mapped_column(Integer,primary_key=True)
 object_type:Mapped[str|None]=mapped_column(String(100),nullable=True)
 object_id:Mapped[int|None]=mapped_column(Integer,nullable=True)
 object_name:Mapped[str|None]=mapped_column(String(300),nullable=True)
 service_name:Mapped[str]=mapped_column(String(300),unique=True,index=True)
 all_tenants:Mapped[bool|None]=mapped_column(Boolean,nullable=True)
 published:Mapped[bool|None]=mapped_column(Boolean,nullable=True)
 odata_v4_url:Mapped[str|None]=mapped_column(Text,nullable=True)
 odata_url:Mapped[str|None]=mapped_column(Text,nullable=True)
 soap_url:Mapped[str|None]=mapped_column(Text,nullable=True)
 last_success_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
 last_error:Mapped[str|None]=mapped_column(Text,nullable=True)
 updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
