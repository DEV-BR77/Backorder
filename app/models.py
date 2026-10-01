from datetime import datetime
from sqlalchemy import Boolean,DateTime,Integer,String,Text,ForeignKey
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base

class ODataService(Base):
 __tablename__="odata_services"
 id:Mapped[int]=mapped_column(Integer,primary_key=True)
 group_name:Mapped[str|None]=mapped_column(String(120),nullable=True,index=True)
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

class BacklogImport(Base):
 __tablename__="backlog_imports"
 id:Mapped[int]=mapped_column(Integer,primary_key=True)
 source_name:Mapped[str]=mapped_column(String(500))
 source_key:Mapped[str]=mapped_column(String(700),unique=True,index=True)
 imported_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,index=True)
 row_count:Mapped[int]=mapped_column(Integer,default=0)
 new_count:Mapped[int]=mapped_column(Integer,default=0)
 changed_count:Mapped[int]=mapped_column(Integer,default=0)
 missing_count:Mapped[int]=mapped_column(Integer,default=0)

class BacklogImportRow(Base):
 __tablename__="backlog_import_rows"
 id:Mapped[int]=mapped_column(Integer,primary_key=True)
 import_id:Mapped[int]=mapped_column(ForeignKey("backlog_imports.id"),index=True)
 backlog_id:Mapped[str]=mapped_column(String(100),index=True)
 data:Mapped[str]=mapped_column(Text)

class Backlog(Base):
 __tablename__="backlogs"
 id:Mapped[int]=mapped_column(Integer,primary_key=True)
 backlog_id:Mapped[str]=mapped_column(String(100),unique=True,index=True)
 creation_date:Mapped[datetime|None]=mapped_column(DateTime,index=True)
 delivery_date:Mapped[str|None]=mapped_column(String(120),nullable=True)
 otlg_note:Mapped[str|None]=mapped_column(Text,nullable=True)
 data:Mapped[str]=mapped_column(Text)
 is_active:Mapped[bool]=mapped_column(Boolean,default=True,index=True)
 first_import_id:Mapped[int|None]=mapped_column(Integer,nullable=True)
 last_import_id:Mapped[int|None]=mapped_column(Integer,nullable=True)
 updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)

class BacklogChange(Base):
 __tablename__="backlog_changes"
 id:Mapped[int]=mapped_column(Integer,primary_key=True)
 import_id:Mapped[int]=mapped_column(ForeignKey("backlog_imports.id"),index=True)
 backlog_id:Mapped[str]=mapped_column(String(100),index=True)
 change_type:Mapped[str]=mapped_column(String(20),index=True)
 changed_fields:Mapped[str|None]=mapped_column(Text,nullable=True)
 before_data:Mapped[str|None]=mapped_column(Text,nullable=True)
 after_data:Mapped[str|None]=mapped_column(Text,nullable=True)

class OtlgMapping(Base):
 __tablename__="otlg_mappings"
 id:Mapped[int]=mapped_column(Integer,primary_key=True)
 text_key:Mapped[str]=mapped_column(String(1200),unique=True,index=True)
 original_text:Mapped[str]=mapped_column(Text)
 announced_delivery:Mapped[str|None]=mapped_column(String(120),nullable=True)
 mapping_rule:Mapped[str|None]=mapped_column(Text,nullable=True)
 measure:Mapped[str|None]=mapped_column(String(160),nullable=True)
 category:Mapped[str|None]=mapped_column(String(160),nullable=True)
 updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
