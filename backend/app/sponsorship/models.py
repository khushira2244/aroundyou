from sqlalchemy import String,Integer,ForeignKey,UniqueConstraint,Numeric
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.shared.database import Base
from app.shared.types import uid
class Organization(Base):
    __tablename__='organizations'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    version:Mapped[int]=mapped_column(Integer,default=1)
    status:Mapped[str]=mapped_column(String(30),default='draft')
    profile:Mapped[dict]=mapped_column(JSONB,default=dict)
class OrganizationMembership(Base):
    __tablename__='organization_memberships'
    __table_args__=(UniqueConstraint('organization_id','account_id',name='uq_org_member'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    organization_id:Mapped[str]=mapped_column(ForeignKey('organizations.id'))
    account_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    permission:Mapped[str]=mapped_column(String(30),default='representative')
class SupportOffer(Base):
    __tablename__='support_offers'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'),index=True)
    account_id:Mapped[str]=mapped_column(ForeignKey('users.id'))
    organization_id:Mapped[str|None]=mapped_column(ForeignKey('organizations.id'))
    plan_id:Mapped[str]=mapped_column(ForeignKey('plan_versions.id'))
    version:Mapped[int]=mapped_column(Integer,default=1)
    status:Mapped[str]=mapped_column(String(30),default='draft')
    content:Mapped[dict]=mapped_column(JSONB)
class SupportFulfillment(Base):
    __tablename__='support_fulfillments'
    __table_args__=(UniqueConstraint('event_id','reference',name='uq_fulfillment_reference'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'))
    offer_id:Mapped[str]=mapped_column(ForeignKey('support_offers.id'))
    quantity:Mapped[float]=mapped_column(Numeric(16,4))
    reference:Mapped[str]=mapped_column(String(200))
    evidence_reference:Mapped[str]=mapped_column(String(1000))
    created_by:Mapped[str]=mapped_column(ForeignKey('users.id'))

class SupportOfferRevision(Base):
    __tablename__='support_offer_revisions'
    __table_args__=(UniqueConstraint('offer_id','version',name='uq_support_offer_version'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('events.id'))
    offer_id:Mapped[str]=mapped_column(ForeignKey('support_offers.id'))
    version:Mapped[int]=mapped_column(Integer)
    content:Mapped[dict]=mapped_column(JSONB)
    created_by:Mapped[str]=mapped_column(ForeignKey('users.id'))
