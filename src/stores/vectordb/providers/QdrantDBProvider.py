import uuid

from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import VectorDBEnums, DistanceMethodEnums
import logging                             
from qdrant_client import models, QdrantClient
from typing import List
from models.db_schemas import RetrievedDocument

class QdrantDBProvider(VectorDBInterface):

    def __init__(self, db_client: str, default_vetor_size: int = 786,
                 distance_method: str = None, index_threshold: int = 10000):

        self.client = None
        self.db_client = db_client
        self.distance_method = distance_method
        self.default_vetor_size = default_vetor_size

        if distance_method == DistanceMethodEnums.COSINE.value:
            self.distance_method = models.Distance.COSINE
        elif distance_method == DistanceMethodEnums.DOT.value:
            self.distance_method = models.Distance.DOT

        self.logger = logging.getLogger("uvicorn")

    async def connect(self):           
        self.client = QdrantClient(path=self.db_client)
   
    async def disconnect(self):
        self.client = None
            
    async def is_collection_existed(self, collection_name: str) -> bool:
       return  self.client.collection_exists(collection_name=collection_name)
    
    async def list_all_collections(self):
        return self.client.get_collections()
  
    async def get_collection_info(self, collection_name: str) -> List:
        return self.client.get_collection(collection_name=collection_name)
        
    async def delete_collection(self, collection_name: str):
        if self.is_collection_existed(collection_name):
            return self.client.delete_collection(collection_name=collection_name)
        
    async def create_collection(self, collection_name: str, 
                                embedding_size: int,
                                do_reset: bool = False):
        if do_reset:
            _ = self.delete_collection(collection_name)

        if not self.is_collection_existed(collection_name=collection_name):

            self.logger.info(f"Creating new Qdrant collection: {collection_name}")

            _ = self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=embedding_size, distance=self.distance_method),
                )
            
            return True

        return False 
    
    async def insert_one(self, collection_name: str, text: str, vector: list,
                            metadata: dict = None, 
                            point_id: str = None):
        
        if not self.is_collection_existed(collection_name):
            self.logger.error(f"Can not insert new record to non-existed collection: {collection_name}")
            return False

        point_id = point_id if point_id else str(uuid.uuid4())

        try:
            _ = self.client.upsert(
                collection_name=collection_name,
                points=[
                    models.PointStruct(
                        id = point_id,
                        vector=vector,
                        payload={
                            "text": text, "metadata": metadata
                        }
                    )
                ]
            )
        except Exception as e:
            self.logger.error(f"Error while inserting point: {e}")
            return None


        return point_id
            
    async def insert_many(self, collection_name: str, texts: list, 
                            vectors: list, metadata: list = None,  
                            points_ids: list = None, batch_size: int = 50):
        
        if metadata is None:
            metadata = [None] * len(texts)

        if points_ids is None:
            points_ids = [
                str(uuid.uuid4()) 
                for _ in range(len(texts))
            ]
            

        points = [
            models.PointStruct(
                id=points_ids[i],
                vector=vectors[i],
                payload={
                    "text": texts[i],
                    "metadata": metadata[i]
                }
            )
            for i in range(len(texts))
        ]

        try:
            _ = self.client.upload_points(
                collection_name=collection_name,
                points= points,
                batch_size=batch_size
            )

        except Exception as e:
                    self.logger.error(f"Error while inserting point: {e}")
                    return None

        return points_ids

    async def search_by_vector(self, collection_name: str, vector: list, limit: int):

        results = self.client.query_points(
            collection_name=collection_name,
            query=vector,
            limit=limit
        )
        
        if not results or not results.points:
            return None
        
        return [
            RetrievedDocument(**{
                "score": point.score,
                "text": point.payload["text"],
            })
            for point in results.points
        ]


