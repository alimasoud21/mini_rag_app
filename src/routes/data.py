from fastapi import FastAPI, APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from helpers.config import get_settings, Settings
import os 
from controllers import Datacontroller, ProjectController # better way to import files using __init__.py
import aiofiles
from models import Response_signal
import logging

logger = logging.getLogger('uvicorn.error')

data_routes = APIRouter(
    prefix="/api/data",
    tags=["api", "data"]
)

@data_routes.post("/upload/{Project_ID}")
async def upload_data_files(Project_ID: str, file: UploadFile,
                            app_settings : Settings = Depends(get_settings)):
    
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
    
    project_dir_path = ProjectController().get_project_path(Project_ID=Project_ID)

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
            
    return JSONResponse(
            content = {
                "signal" : Response_signal.FILE_UPLOAD_SUCCESS.value
            }
        )
