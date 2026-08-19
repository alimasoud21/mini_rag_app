from .BaseDataModel import BaseDataModel
from .db_schemas.DataChunk import DataChunk
from .enums.DataBaseEnum import DataBaseEnum
from bson.objectid import ObjectId #type: ignore
from pymongo import InsertOne #type: ignore

class ChunkModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.collection = self.db_client[DataBaseEnum.COLLECTION_CHUNK_NAME.value]

    async def create_chunk(self, chunk: DataChunk):
        result = self.collection.insert_one(chunk.dict(by_alias= True, exclude_unset=True))
        chunk._id = result.inserted_id
        return chunk
    
    async def get_chunk(self, chunk_id: str):
        result = await self.collection.fine_one({
            "_id": ObjectId(chunk_id)
        })

        if result is None:
            return None

        return DataChunk(**result)

    async def insert_many_chunks(self, chunks: list, batch_size: int=100):

        for i in range(0, len(chunks), batch_size):

            batch = chunks[i: i+batch_size]

            operations = [
                InsertOne(chunk.dict(by_alias= True, exclude_unset=True))
                for chunk in batch 
            ]

            await self.collection.bulk_write(operations)

        return len(chunks)
    

    async def delete_chunks_by_project_id(self, Project_ID: ObjectId):
        result = await self.collection.delete_many({
            "chunk_Project_ID": Project_ID
                            
        })

        return result.deleted_count
    