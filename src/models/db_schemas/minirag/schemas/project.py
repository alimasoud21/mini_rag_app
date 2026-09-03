from .minirag_base import SQLAlchemyBase #type: ignore
from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship

class Project(SQLAlchemyBase):

    __tablename__ = "projects"

    #indexed by default 
    project_id = Column(Integer, primary_key=True, autoincrement=True)
    project_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)

    project_created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    project_updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    assets = relationship("Asset", back_populates="project")
    chunks = relationship("DataChunk", back_populates="project")

