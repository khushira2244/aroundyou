from sqlalchemy import ForeignKey,String,Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped,mapped_column
from app.shared.database import Base
from app.shared.types import uid
class GovernanceTicket(Base):
    __tablename__='governance_tickets'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id: Mapped[str]=mapped_column(ForeignKey('events.id'),unique=True)
    version: Mapped[int]=mapped_column(Integer,default=1)
    configuration: Mapped[dict]=mapped_column(JSONB)
