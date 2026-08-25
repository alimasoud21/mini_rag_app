from pydantic import BaseModel, Field, validator # type: ignore
from typing import Optional
from bson.objectid import ObjectId # type: ignore 
from datetime import datetime

class Asset(BaseModel):
     id: Optional[ObjectId] = Field(None, alias= "_id")

     asset_project_id : ObjectId
     asset_type : str = Field(...,min_length=1)
     asset_name: str = Field(..., min_lenght=1)
     asset_size: int = Field(ge=0, default=None ) #not optional 
     asset_config: dict = Field(default=None)
     asset_creation: datetime  = Field(default=datetime.now)

     class Config:
          arbitrary_types_allowed = True
     

     @classmethod
     def get_indexes(cls):

          return [ 
               {
                   "key": [
                        ("asset_project_id", 1)
                   ],
                   "name": "asset_project_id_index_1",
                   "unique": False #many files could go under on project 

               },
               {
                    "key":[
                         ("asset_project_id", 1),
                         ("asset_name", 1)
                    ],
                    "name": "asset_project_id_index_name_1",
                    "unique": True

               }

          ]

     




