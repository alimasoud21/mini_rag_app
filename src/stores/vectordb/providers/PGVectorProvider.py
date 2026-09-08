from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import (DistanceMethodEnums, PgVectorDistanceMethodEnums,
                            PgVectorIndexTypeEnums, PgVectorTableSchemeEnums)
import logging 
from typing import List
from models.db_schemas import RetrievedDocument
from sqlalchemy.sql import text as sql_text
import json

class PGVectorProvider(VectorDBInterface):

    def __init__(self, db_client, default_vector_size: int = 786,
                 distance_method: str = None, index_threshold: int = 10000):
        
        self.db_client = db_client
        self.default_vector_size = default_vector_size
        self.distance_method = distance_method
        self.index_threshold = index_threshold

        if distance_method == DistanceMethodEnums.COSINE.value:
            distance_method = PgVectorDistanceMethodEnums.COSINE.value
        elif distance_method == DistanceMethodEnums.DOT.value:
            distance_method = PgVectorDistanceMethodEnums.DOT.value

        self.distance_method = distance_method
        self.pgvector_table_prefix = PgVectorTableSchemeEnums._PREFIX.value
        self.logger = logging.getLogger("uvicorn")

        self.default_index_name = lambda collection_name : f"{collection_name}_vector_idx"
    
    async def connect(self):
        async with self.db_client() as session:
            async with session.begin():
                await session.execute(sql_text(
                    "CREATE EXTENSION IF NOT EXISTS vector"
                ))
        
    async def disconnect(self):
        pass

    async def is_collection_existed(self, collection_name: str) -> bool:

        record = None
        async with self.db_client() as session:
            async with session.begin():
                list_tbl = sql_text(f'SELECT * FROM pg_tables WHERE tablename = :collection_name')
                results = await session.execute(list_tbl, {"collection_name": collection_name})
                record = results.scalar_one_or_none()

        return record

    async def list_all_collections(self) -> List:
        records = []
        async with self.db_client() as session:
            async with session.begin():
                list_tbl = sql_text('SELECT tablename FROM pg_tables WHERE tablename LIKE :prefix')
                results = await session.execute(list_tbl, {"prefix": self.pgvector_table_prefix})
                records = results.scalars().all()
        
        return records

    async def get_collection_info(self, collection_name: str) -> dict:
        async with self.db_client() as session:
            async with session.begin():
                
                table_info_sql = sql_text(f'''
                    SELECT schemaname, tablename, tableowner, tablespace, hasindexes 
                    FROM pg_tables 
                    WHERE tablename = :collection_name
                ''')

                count_sql = sql_text(f'SELECT COUNT(*) FROM {collection_name}')

                table_info = await session.execute(table_info_sql, {"collection_name": collection_name})
                record_count = await session.execute(count_sql)

                table_data = table_info.fetchone()
                if not table_data:
                    return None
                
                return {
                    "table_info": {
                        "schemaname": table_data[0],
                        "tablename": table_data[1],
                        "tableowner": table_data[2],
                        "tablespace": table_data[3],
                        "hasindexes": table_data[4],
                    },
                    "record_count": record_count.scalar_one(),
                }

    async def delete_collection(self, collection_name: str):
        async with self.db_client() as session:
            async with session.begin():
                self.logger.info(f"Deleting collection: {collection_name}")

                delete_sql = sql_text(f'DROP TABLE IF EXISTS {collection_name}')
                await session.execute(delete_sql)
                await session.commit()
        
        return True
       
    async def create_collection(self, collection_name: str,
                                      embedding_size: int,
                                      do_reset: bool = False):
        
        if do_reset:
            _ = await self.delete_collection(collection_name=collection_name)

        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            self.logger.info(f"Creating collection: {collection_name}")
            async with self.db_client() as session:
                async with session.begin():
                    create_sql = sql_text(
                        f'CREATE TABLE {collection_name} ('
                            f'{PgVectorTableSchemeEnums.ID.value} bigserial PRIMARY KEY,'
                            f'{PgVectorTableSchemeEnums.TEXT.value} text, '
                            f'{PgVectorTableSchemeEnums.VECTOR.value} vector({embedding_size}), '
                            f'{PgVectorTableSchemeEnums.METADATA.value} jsonb DEFAULT \'{{}}\', '
                            f'{PgVectorTableSchemeEnums.CHUNK_ID.value} integer, '
                            f'FOREIGN KEY ({PgVectorTableSchemeEnums.CHUNK_ID.value}) REFERENCES chunks(chunk_id)'
                        ')'
                    )
                    await session.execute(create_sql)
                               
            return True

        return False

    async def is_index_existed(self, collection_name: str) -> bool:
        index_name = self.default_index_name(collection_name)
        async with self.db_client() as session:
            async with session.begin():
                query = sql_text("""
                    SELECT 1 
                    FROM pg_indexes
                    WHERE tablename = :collection_name
                    AND indexname = :index_name    
                    """)
                results = await session.execute(query, {
                    "collection_name" : collection_name,
                    "index_name" : index_name
                })

                return bool(results.scalar_one_or_none())

    async def create_index_vector(self, collection_name: str, index_type: str = PgVectorIndexTypeEnums.HNSW.value):

        is_index_existed = await self.is_index_existed(collection_name=collection_name)
        if is_index_existed:
            return False

        async with self.db_client() as session:
            async with session.begin():
                query = sql_text(f"SELECT COUNT(*) FROM {collection_name} ")
                result = await session.execute(query)
                records_count = result.scalar_one()

                if records_count < self.index_threshold:
                    return False

                self.logger.info(f"START: creating vector index for collection: {collection_name}")

                index_name = self.default_index_name(collection_name)

                create_index_query = sql_text(
                    f'CREATE INDEX {index_name} ON {collection_name} '
                    f'USING {index_type} ({PgVectorTableSchemeEnums.VECTOR.value} {self.distance_method})'
                )
                await session.execute(create_index_query)

                self.logger.info(f"END: created vector index for collection: {collection_name}")
        
    async def reset_vector_index(self, collection_name: str, index_type: str = PgVectorIndexTypeEnums.HNSW.value):

        index_name = self.default_index_name(collection_name)
        async with self.db_client() as session:
            async with session.begin():
                drop_query = sql_text(f"DROP INDEX IF EXISTS {index_name}")
                await session.execute(drop_query)

        return await self.create_index_vector(collection_name=collection_name, index_type=index_type) 

    async def insert_one(self, collection_name: str, text: str, vector: list, metadata: dict = None, point_id: str = None):

        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            self.logger.error(f"Can not insert new record to non-existed collection: {collection_name}")
            return False
        
        if not point_id:
            self.logger.error(f"Can not insert new record without chunk_id: {collection_name}")
            return False
        
        async with self.db_client() as session:
            async with session.begin():
                insert_sql = sql_text(f'INSERT INTO {collection_name} '
                                      f'({PgVectorTableSchemeEnums.TEXT.value}, {PgVectorTableSchemeEnums.VECTOR.value}, {PgVectorTableSchemeEnums.METADATA.value}, {PgVectorTableSchemeEnums.CHUNK_ID.value}) '
                                      'VALUES (:text, :vector, :metadata, :chunk_id)'
                                      )
                
                metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata is not None else "{}"
                await session.execute(insert_sql, {
                    'text': text,
                    #pgvector takes the vector as string not list [0,1,2,3]
                    'vector': "[" + ",".join([ str(v) for v in vector ]) + "]",
                    'metadata': metadata_json,
                    'chunk_id': point_id
                })


                await self.create_vector_index(collection_name=collection_name)
        
        return True

    async def insert_many(self, collection_name: str, texts: list, vectors: list, metadata: list = None, points_ids: list = None, batch_size: int = 50):

        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)

        if not is_collection_existed:
            self.logger.error(f"Can not insert new records to non-existed collection: {collection_name}")
            return False

        if not metadata or len(metadata) == 0 :
            metadata = [None] * len(texts) 

        async with self.db_client() as session:
            async with session.begin():
                for i in range(0, len(texts), batch_size):
                    batch_text = texts[i:i+batch_size]
                    batch_vectors = vectors[i:i+batch_size]
                    batch_metadata = metadata[i:i+batch_size]
                    batch_points_ids = points_ids[i:i+batch_size]

                    values = []
                    for _text, _vector, _metadata, _point_id in zip(batch_text, batch_vectors, batch_metadata, batch_points_ids):
                        values.append({
                            'text': _text,
                            'vector': "[" + ",".join([ str(v) for v in _vector ]) + "]",
                            'metadata': json.dumps(_metadata, ensure_ascii=False) if _metadata else "{}",
                            'chunk_id': _point_id
                        })


                    batch_insert_sql = sql_text(f'INSERT INTO {collection_name} '
                                                f'({PgVectorTableSchemeEnums.TEXT.value}, '
                                                f'{PgVectorTableSchemeEnums.VECTOR.value}, '
                                                f'{PgVectorTableSchemeEnums.METADATA.value}, '
                                                f'{PgVectorTableSchemeEnums.CHUNK_ID.value}) '
                                                f'VALUES (:text, :vector, :metadata, :chunk_id)')
        
                    await session.execute(batch_insert_sql, values)
                    
        await self.create_index_vector(collection_name= collection_name)
        
        return True

    async def search_by_vector(self, collection_name: str, vector: list, limit: int) -> List[RetrievedDocument]:

        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            self.logger.error(f"Can not search for records in a non-existed collection: {collection_name}")
            return False

        vector = "[" + ",".join([ str(v) for v in vector ]) + "]"

        async with self.db_client() as session:
            async with session.begin():
                # Using Cosine Distance (<=>) as the default sorting metric
                search_query = sql_text(f"""
                    SELECT {PgVectorTableSchemeEnums.TEXT.value} as text,  {PgVectorTableSchemeEnums.VECTOR.value} <=> :vector AS score 
                    FROM {collection_name} 
                    ORDER BY score 
                    LIMIT :limit
                """)
                
                result = await session.execute(search_query, {
                    "vector": vector,
                    "limit": limit
                })
                
                records = result.fetchall()
                
                # Format the returned rows back into standard Python dictionaries
                return [
                    RetrievedDocument(
                        text = re.text,
                        score = 1 - re.score 
                    )
                    for re in records
                ]
            