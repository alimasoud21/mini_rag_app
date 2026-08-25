from fastapi import FastAPI, APIRouter, Depends
from helpers.config import get_settings, Settings
import os 

base_router = APIRouter(
    prefix="/api",
    tags=["api"]
)

@base_router.get("/base")
async def base(app_settings: Settings = Depends(get_settings)):

    app_name = app_settings.APP_NAME
    app_version = app_settings.APP_VERSION

    return {
        "app_name": app_name,
        "app_version": app_version
    }


