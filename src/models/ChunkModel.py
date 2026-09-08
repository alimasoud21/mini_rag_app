from .BaseDataModel import BaseDataModel
from .db_schemas import DataChunk
from .enums.DataBaseEnum import DataBaseEnum
from bson.objectid import ObjectId
from pymongo import InsertOne
from sqlalchemy.future import select
from sqlalchemy import func, delete


class ChunkModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_client = db_client

    @classmethod
    async def create_instacne(cls, db_client: object):
        #call init
        instance=cls(db_client) 
        return instance
    
               
    async def create_chunk(self, chunk: DataChunk):
        async with self.db_client() as session:
            async with session.begin():
                session.add(chunk)
            await session.commit()
            await session.refresh(chunk)

        return chunk

    async def get_chunk(self, chunk_id: str):
        async with self.db_client() as session:
            result  = await session.execute(select(DataChunk).where(DataChunk.chunk_id == chunk_id))
            chunk = result.scaler_one_or_none()
        return chunk 

    async def insert_many_chunks(self, chunks: list[DataChunk]):

        async with self.db_client() as session:
            async with session.begin(): #session.begin() automaticly commits if there is no errors

                # we could use await session.execute(insert(DataChunk), chunks) but pass list[dict] to it 
                # which is faster but it bypass the validation layer implemented at DataChunk class
                session.add_all(chunks)

        return len(chunks)
    
    async def delete_chunks_by_project_id(self, project_id: ObjectId):
        async with self.db_client() as session:
            async with session.begin():
                result  = await session.execute(delete(DataChunk).where(DataChunk.chunk_project_id == project_id))

        return result.rowcount
    
    async def get_project_chunks(self, project_id: ObjectId, page_number: int=1, page_size : int=50 ):
        async with self.db_client() as session:
            query = select(DataChunk).where(DataChunk.chunk_project_id == project_id).offset((page_number - 1) * page_size).limit(page_size)
            result = await session.execute(query)
            records = result.scalars().all()
        return records

    async def get_total_chunks_count(self, project_id: ObjectId):
        total_count = 0
        async with self.db_client() as session:
            count_sql = select(func.count(DataChunk.chunk_id)).where(DataChunk.chunk_project_id == project_id)
            records_count = await session.execute(count_sql)
            total_count = records_count.scalar()
        
        return total_count
    