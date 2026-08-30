from .BaseController import BaseController
from models.db_schemas import Project, DataChunk
from typing import List
from stores.llm.LLMEnums import DocumentTypeEnums
import json

class NLPController(BaseController):

    def __init__(self, vectordb_client, generation_client, embedding_client, template_purser):
        super().__init__()

        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.template_purser = template_purser


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
        
        return results
    
    def answer_rag_question(self, project: Project, query: str, limit: int = 10):
        answer, full_messages = None, None
        
        # step 1: retrieve related documents
        retrieved_documents = self.search_vector_db_collection(
            project=project,
            text=query,
            limit=limit,
        )

        if not retrieved_documents or len(retrieved_documents) == 0:
            return answer, full_messages

        # step 2: construct llm prompt parts
        system_prompt = self.template_purser.get("rag", "system_prompt")

        document_prompts = "\n".join([
            self.template_purser.get("rag", "document_prompt",{
                "doc_num": idx + 1,
                "chunk_text": document.text,
            })
            for idx, document in enumerate(retrieved_documents)
        ])
        
        footer_prompt = self.template_purser.get("rag", "footer_prompt")
        full_prompt = "\n\n".join([document_prompts, footer_prompt])

        # step 3: Construct Generation Client Prompts (The V2 way)
        # Here we use construct_prompt to build the strict [{"role": "system", "content": ...}] format
        full_messages = [
            self.generation_client.construct_prompt(
                prompt=system_prompt,
                role=self.generation_client.enums.SYSTEM.value  # Will be lowercased inside construct_prompt
            ),
            self.generation_client.construct_prompt(
                prompt=full_prompt,
                role=self.generation_client.enums.USER.value    # Will be lowercased inside construct_prompt
            )
        ]

        # step 4: Retrieve the Answer
        # We pass the full_messages list to the prompt argument
        answer = self.generation_client.generate_text(
            prompt=full_messages, 
        )

        #return answer, full_prompt, full_messages

        return (
            json.loads(json.dumps(answer, default=lambda x: x.__dict__)),
            json.loads(json.dumps(full_messages, default=lambda x: x.__dict__))
        )