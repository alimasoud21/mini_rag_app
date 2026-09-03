from fastapi import FastAPI, APIRouter, status, Request 
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse 
import logging

from routes.schemas.nlp import PushRequest, SearchRequest
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from controllers import NLPController
from models import Response_signal


logger = logging.getLogger('uvicorn.error')

nlp_router = APIRouter(
    prefix="/api/nlp",
    tags=["api", "nlp"]
)
@nlp_router.post("/index/push/{project_id}")
async def index_project(request: Request, project_id: int, push_request: PushRequest):

    project_model = await ProjectModel.create_instacne(
            db_client= request.app.db_client
        )
    
    chunk_model = await ChunkModel.create_instacne(
        db_client=request.app.db_client
    )

    project = await project_model.get_project_or_create_one(
        project_id=project_id
    ) 

    if not project:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": Response_signal.PROJECT_NOT_FOUND_ERROR.value
            } 
        )
    
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_purser=request.app.template_purser
    )

    has_chunks = True
    page_number = 1
    total_points_inserted = 0

    while has_chunks:
        Page_chunks = await chunk_model.get_project_chunks(project_id=project.project_id, page_number=page_number)

        if len(Page_chunks):
            page_number += 1

        if not page_number or len(Page_chunks) == 0:
            has_chunks = False
            break

        results = nlp_controller.index_into_vector_db(
            project=project, 
            chunks=Page_chunks,
            do_reset=push_request.do_reset
        )
                                
        my_collection = results["created_collection"] # will be true or false so i just need it to validate and handle errors
        my_points = results["points_ids"] # will be a list of uuids so i should store it outside the for loop or just return its len()

        if not my_collection or len(my_points) == 0 :
            
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": Response_signal.INSERT_INTO_VECTORDB_ERROR.value
                } 
            )

        total_points_inserted += len(my_points)

    return JSONResponse(
        content={
            "signal": Response_signal.INSERT_INTO_VECTORDB_SUCCESS.value,
            "total_points_inserted": total_points_inserted
        } 
    )

@nlp_router.get("/index/info/{project_id}")
async def get_project_index_info(request: Request, project_id: int):

    project_model = await ProjectModel.create_instacne(
                db_client= request.app.db_client
            )
    
    project = await project_model.get_project_or_create_one(
        project_id=project_id
    ) 
    
    nlp_controller = NLPController(
            vectordb_client=request.app.vectordb_client,
            generation_client=request.app.generation_client,
            embedding_client=request.app.embedding_client,
            template_purser=request.app.template_purser
    )

    collection_info = nlp_controller.get_vector_collection_info(project=project)

    return JSONResponse(
        content={
            "signal": Response_signal.VECTORDB_COLLECTION_RETRIVED.value,
            "collection_info": collection_info
        } 
    )

@nlp_router.post("/index/search/{project_id}")
async def search_index(request: Request, project_id: int, search_request: SearchRequest):

    project_model = await ProjectModel.create_instacne(
                    db_client= request.app.db_client
                )
        
    project = await project_model.get_project_or_create_one(
        project_id=project_id
    ) 
    
    nlp_controller = NLPController(
            vectordb_client=request.app.vectordb_client,
            generation_client=request.app.generation_client,
            embedding_client=request.app.embedding_client,
            template_purser = request.app.template_purser,
    )

    results = nlp_controller.search_vector_db_collection(
        project=project,
        text=search_request.text,
        limit=search_request.limit
    )

    if not results:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": Response_signal.VECTORDB_SEARCH_ERROR.value
            } 
        )
        
    return JSONResponse(
        content={
            "signal": Response_signal.VECTORDB_SEARCH_SUCCESS.value,
            "results":  [result.dict() for result in results]
        } 
    )

@nlp_router.post("/index/answer/{project_id}")
async def answer_rag(request: Request, project_id: int, search_request: SearchRequest):

    project_model = await ProjectModel.create_instacne(
        db_client= request.app.db_client
    )
        
    project = await project_model.get_project_or_create_one(
        project_id=project_id
    ) 

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_purser = request.app.template_purser,
    )

    answer, full_messages = nlp_controller.answer_rag_question(
        project=project,
        query= search_request.text,
        limit=search_request.limit
    )

    if not answer:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": Response_signal.ANSWER_GENERATION_ERROR.value
            } 
        )

    return JSONResponse(
        content=jsonable_encoder({
            "siganl" : Response_signal.ANSWER_GENERATION_SUCCESS.value,
            "answer" : answer,
            "full_messages" : full_messages,
        })
    )
       