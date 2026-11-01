from sqlalchemy import String,Integer,ForeignKey,UniqueConstraint,Numeric,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.shared.database import Base
from app.shared.types import uid
class ResourceTransaction(Base):
    __tablename__='resource_transactions'
    __table_args__=(UniqueConstraint('event_id','reference',name='uq_resource_receipt_reference'),CheckConstraint('quantity > 0',name='ck_resource_positive'))
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
    resource_id:Mapped[str]=mapped_column(String(60))
    offer_id:Mapped[str|None]=mapped_column(ForeignKey('support_offers.id'))
    fulfillment_id:Mapped[str|None]=mapped_column(ForeignKey('support_fulfillments.id'),unique=True)
    quantity:Mapped[float]=mapped_column(Numeric(16,4))
    unit:Mapped[str]=mapped_column(String(80))
    reference:Mapped[str]=mapped_column(String(200))
    evidence_reference:Mapped[str]=mapped_column(String(1000))
    kind:Mapped[str]=mapped_column(String(30),default='receipt')
    reverses_id:Mapped[str|None]=mapped_column(ForeignKey('resource_transactions.id'),unique=True)
    created_by:Mapped[str]=mapped_column(ForeignKey('users.id'))
class ResourceReservation(Base):
    __tablename__='resource_reservations'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
    resource_id:Mapped[str]=mapped_column(String(60))
    work_id:Mapped[str]=mapped_column(String(60))
    plan_id:Mapped[str]=mapped_column(ForeignKey('plan_versions.id'))
    quantity:Mapped[float]=mapped_column(Numeric(16,4))
    unit:Mapped[str]=mapped_column(String(80))
    status:Mapped[str]=mapped_column(String(20),default='reserved')
    version:Mapped[int]=mapped_column(Integer,default=1)
