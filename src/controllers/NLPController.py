from .BaseController import BaseController
from models.db_schemas import Project, DataChunk
from typing import List
from stores.llm.LLMEnums import DocumentTypeEnums
import json
import asyncio
import logging

class NLPController(BaseController):

    def __init__(self, vectordb_client, generation_client, embedding_client, template_purser):
        super().__init__()

        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.template_purser = template_purser


    def create_collection_name(self, project_id: str):

        return f"collection_{self.vectordb_client.default_vector_size}_{project_id}". strip()
    
    async def reset_vector_db_collection(self, project: Project, collection_name: str):

        collection_name = self.create_collection_name(project_id=project.project_id)
        return await self.vectordb_client.delete_collection(collection_name=collection_name)

    async def get_vector_collection_info(self, project: Project):

        collection_name = self.create_collection_name(project_id=project.project_id)
        collection_info =  await self.vectordb_client.get_collection_info(collection_name=collection_name)

        # string -> dic
        return json.loads(
            # object -> json string
            json.dumps(collection_info, default=lambda x: x.__dict__)
        )
    
    async def index_into_vector_db(self, project: Project, chunks: List[DataChunk], points_ids= List[int], do_reset: bool = False): 

        # get collection name
        collection_name = self.create_collection_name(project_id=project.project_id)

        # manage items for insert many
        texts = [c.chunk_text for c in chunks]        
        metadata = [c.chunk_metadata for c in chunks]
        
        max_retries = 3
        retry_delay = 62 # wait just over a minute for the token bucket to reset
        vectors = None
        
        for attempt in range(max_retries):
            try:
                # Attempt to get embeddings
                vectors = self.embedding_client.embed_text(text=texts, document_type=DocumentTypeEnums.DOCUMENT.value)
                break  # If successful, break out of the retry loop
                
            except Exception as e:
                # Catch the rate limit error (or any other API error)
                logging.warning(f"Embedding attempt {attempt + 1} failed. Error: {e}")
                
                if attempt < max_retries - 1:
                    logging.info(f"Rate limit likely hit. Pausing for {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logging.error("Max retries reached. Aborting embedding process.")
                    raise e  # Crash gracefully if it fails 3 times in a row

        
        # create collection if not existed -> bool
        collection = await self.vectordb_client.create_collection(
                     collection_name=collection_name,
                     embedding_size = self.embedding_client.embedding_size,
                     do_reset = do_reset
                     )

        #insert into database -> list
        points_ids = await self.vectordb_client.insert_many( 
            collection_name = collection_name,
            texts = texts, 
            vectors = vectors,
            metadata =metadata,
            points_ids=points_ids
        )

        

        return {
            "created_collection": collection,
            "points_ids": points_ids
        }

    async def search_vector_db_collection(self, project: Project, text: str, limit: int = 10):

        query_vector = None
        # get collection name
        collection_name = self.create_collection_name(project_id=project.project_id)

        # get text embedding vector
        vectors = self.embedding_client.embed_text(
            text = text, 
            document_type = DocumentTypeEnums.QUERY.value
        )

        # validate vector
        if not vectors or len(vectors) == 0:
            return False

        if isinstance(vectors, list) and len(vectors) > 0:
            query_vector = vectors[0]

        if not query_vector :
            return False
        
        # do semantic search
        results = await self.vectordb_client.search_by_vector(
            collection_name=collection_name,
            vector = query_vector,
            limit = limit
        )

        if not results:
            return False
        
        return results
    
    async def answer_rag_question(self, project: Project, query: str, limit: int = 10):
        answer, full_messages = None, None
        
        # step 1: retrieve related documents
        retrieved_documents = await self.search_vector_db_collection(
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
        
        footer_prompt = self.template_purser.get("rag", "footer_prompt", {
            "query": query
        })

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