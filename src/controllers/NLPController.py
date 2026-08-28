from .BaseController import BaseController
from models.db_schemas import Project, DataChunk
from typing import List
from stores.llm.LLMEnums import DocumentTypeEnums
import json

class NLPController(BaseController):

    def __init__(self, vectordb_client, generation_client, embedding_client):
        super().__init__()

        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client


    def create_collection_name(self, Project_ID: str):

        return f"collection_{Project_ID}". strip()
    
    def reset_vector_db_collection(self, project: Project, collection_name: str):

        collection_name = self.create_collection_name(Project_ID=project.Project_ID)
        return self.vectordb_client.delete_collection(collection_name=collection_name)

    def get_vector_collection_info(self, project: Project):

        collection_name = self.create_collection_name(Project_ID=project.Project_ID)
        collection_info =  self.vectordb_client.get_collection_info(collection_name=collection_name)

        # string -> dic
        return json.loads(
            # object -> json string
            json.dumps(collection_info, default=lambda x: x.__dict__)
        )
    
    def index_into_vector_db(self, project: Project, chunks: List[DataChunk], do_reset: bool = False): 

        # get collection name
        collection_name = self.create_collection_name(Project_ID=project.Project_ID)

        # manage items for insert many
        texts = [c.chunk_text for c in chunks]        
        metadata = [c.chunk_metadata for c in chunks]
        vectors =[
            self.embedding_client.embed_text(text = text, 
                                             document_type=DocumentTypeEnums.DOCUMENT.value) 
            for text in texts
            ]
        
        # create collection if not existed -> bool
        collection = self.vectordb_client.create_collection(
                     collection_name=collection_name,
                     embedding_size = self.embedding_client.embedding_size,
                     do_reset = do_reset
                     )

        #insert into database -> list
        points_ids = self.vectordb_client.insert_many( 
            collection_name = collection_name,
            texts = texts, 
            vectors = vectors,
            metadata =metadata
        )

        return {
            "created_collection": collection,
            "points_ids": points_ids
        }

    def search_vector_db_collection(self, project: Project, text: str, limit: int = 10):

        # get collection name
        collection_name = self.create_collection_name(Project_ID=project.Project_ID)

        # get text embedding vector
        vector = self.embedding_client.embed_text(
            text = text, 
            document_type = DocumentTypeEnums.QUERY.value
        )

        # validate vector
        if not vector or len(vector) == 0:
            return False
        
        # do semantic search
        results = self.vectordb_client.search_by_vector(
            collection_name=collection_name,
            vector = vector,
            limit = limit
        )

        if not results:
            return False
        
        return json.loads(
            # object -> json string
            json.dumps(results, default=lambda x: x.__dict__)
        )



