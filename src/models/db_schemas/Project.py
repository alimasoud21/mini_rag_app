from pydantic import BaseModel, Field, validator # type: ignore
from typing import Optional
from bson.objectid import ObjectId # type: ignore

class Project(BaseModel):
    id: Optional[ObjectId] = Field(None, alias= "_id")

    Project_ID: str = Field(pattern=r'^[a-zA-Z0-9]+$')

    
    
    #this prevints error coming from that ObjectID is arbitrary for pydantic 
    class Config:
        arbitrary_types_allowed = True

        
    """
    Project_ID: str =  Field(..., min_length=1)

    #this is a custom validator and it could be impleminted by other way
    @validator('Project_ID')
    def validate_project_id(cls, value):
        if not value.isalnum():
            raise ValueError("project_id must be alphanumeric")

        return value
    """