from pydantic import BaseModel
from .minirag_base import SQLAlchemyBase #type: ignore
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy import Index
import uuid

class Asset(SQLAlchemyBase):

    __tablename__ = "assets"

    #indexed by default 
    asset_id = Column(Integer, primary_key=True, autoincrement=True)
    asset_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)

    asset_type = Column(String, nullable=False)
    asset_name = Column(String, nullable=False)
    asset_size = Column(Integer, nullable=False)
    asset_config = Column(JSONB, nullable=True)

    asset_created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    asset_updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True) 

    #connect the asset to its parent project_id    
    asset_project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False)

    # get the data from Project Module and back populate it into assets
    project = relationship("Project", back_populates="assets")
    chunks = relationship("DataChunk", back_populates="asset")

    #create an index for asset project id

    __table_args__ = (
        Index('ix_asset_project_id', asset_project_id),
    )


class RetrievedDocument(BaseModel):
    text: str
    score : float