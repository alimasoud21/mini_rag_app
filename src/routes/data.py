from fastapi import FastAPI, APIRouter, Depends, UploadFile, status, Request  # type: ignore
from fastapi.responses import JSONResponse   # type: ignore
from helpers.config import get_settings, Settings
import os 
import logging
import aiofiles   # type: ignore

from controllers import Datacontroller, ProjectController, ProcessController # better way to import files using __init__.py

from models import Response_signal

from .schemas.data import ProcessRequest
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from models.db_schemas import DataChunk, Asset
from models.AssetModel import AssetModel

logger = logging.getLogger('uvicorn.error')

data_router = APIRouter(
    prefix="/api/data",
    tags=["api", "data"]
)

@data_router.post("/upload/{Project_ID}")
async def upload_data_files(request: Request, Project_ID: str, file: UploadFile,
                            app_settings : Settings = Depends(get_settings)):
    
    #retrive project form database 
    project_model = await ProjectModel.create_instacne(
        db_client= request.app.db_client
    )
    project = await project_model.get_project_or_create_one(
        Project_ID=Project_ID
    )

    #validate data

    data_controller = Datacontroller()
    is_valid , result_signal= data_controller.validate_uploaded_file(file= file)

    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                "signal" :result_signal
            }
        )
    
    #project_dir_path = ProjectController().get_project_path(Project_ID=Project_ID)

    file_path, file_id = data_controller.generate_unique_file_path(
        orig_file_name = file.filename,
        Project_ID=Project_ID
        )

    try:
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
                await f.write(chunk)

    except Exception as e:

        logger.error(f"Error while uploading file: {e}")

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": Response_signal.FILE_UPLOAD_FAILED.value
            }
        )

    asset_model = await AssetModel.create_instance(
        db_client=request.app.db_client
    )     
    asset =  Asset(
        asset_project_id = project.id ,
        asset_type = "file", # shoud be imported from enum file
        asset_name = file_id,
        asset_size = os.path.getsize(file_path)

    )

    asset_reocrd = await asset_model.create_asset(asset=asset)


    return JSONResponse(
            content = {
                "signal" : Response_signal.FILE_UPLOAD_SUCCESS.value,
                "file_id" : str(asset_reocrd.id),
            }
        )

@data_router.post("/process/{Project_ID}")
async def process_endpoint(request: Request, Project_ID: str, process_request: ProcessRequest):

    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset

    #retrive project form database 
    project_model = await ProjectModel.create_instacne(
        db_client= request.app.db_client
    )

    project = await project_model.get_project_or_create_one(
        Project_ID=Project_ID
    )


    chunk_model = await ChunkModel.create_instacne(
        db_client= request.app.db_client
    )

    asset_model = await AssetModel.create_instance(
            db_client=request.app.db_client
        )
    
    project_assets_ids = {}

    if process_request.file_id :
        
        asset = await asset_model.get_asset(
            asset_project_id=project.id,
            asset_name=process_request.file_id
            )

        if asset is None:
            return JSONResponse(
                status_code = status.HTTP_400_BAD_REQUEST,
                content={
                     "signal": Response_signal.FILE_ID_ERROR.value
                }
            )

        project_assets_ids = {
            asset.id: asset.asset_name
        }
    
    else:

        project_assets = await asset_model.get_all_project_assets(
            asset_project_id=project.id,
            asset_type="file" #this should be adde to enum file
        )

        project_assets_ids={
            asset.id: asset.asset_name
            for asset in project_assets
        }

    if len(project_assets_ids) == 0:
        return JSONResponse(
            status_code = status.HTTP_400_BAD_REQUEST,
            content={
                 "signal": Response_signal.NO_FILES_ERROR.value
            }
        )

    process_controller = ProcessController(Project_ID= Project_ID)

    no_records = 0
    no_files = 0

    #retrive project form database 
    if do_reset == 1:
        await chunk_model.delete_chunks_by_project_id(
            Project_ID=project.id
        )

    for asset_id, file_id in project_assets_ids.items():

        file_content = process_controller.get_file_content(file_id= file_id)

        if file_content is None:
            logger.error(f"Error while processing file: {file_id} ")
            continue

        file_chunks = process_controller.process_file_content(
            file_content= file_content,
            file_id= file_id,
            chunk_size=chunk_size,
            chunk_overlap= overlap_size

        )
        
        if file_chunks is None or len(file_chunks) == 0:
            return JSONResponse(
                status_code = status.HTTP_400_BAD_REQUEST,
                content={
                    "signal" : Response_signal.PROCESSING_FAILED.value
                }
            )
        
        file_chunks_records = [
            DataChunk(
                chunk_text=chunk.page_content,
                chunk_metadata=chunk.metadata,
                chunk_order=i + 1,
                chunk_Project_ID=project.id,
                chunk_asset_id=asset_id
            )
            for i, chunk in enumerate(file_chunks)
        ]

        no_records += await chunk_model.insert_many_chunks(chunks=file_chunks_records)
        no_files += 1

    return JSONResponse({
        "signal": Response_signal.PROCESSING_SUCCESS.value,
        "number_of_records": no_records,
        "number_of_files": no_files
    })


