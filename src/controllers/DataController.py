from .BaseController import BaseController
from .ProjectContoller import ProjectController
from fastapi import UploadFile
from models import Response_signal
import os
import re


class Datacontroller(BaseController):

    def __init__(self):

        super().__init__()
        self.size_scale = 1024*1024 # to convert from MB to Bytes

    def validate_uploaded_file(self, file: UploadFile):
        
        if file.content_type not in self.app_setting.FILE_ALLOWED_TYPES:
            return False, Response_signal.FILE_TYPE_NOT_SUPPORTED.value
        
        #since file.size returnes the app size in bytes we need to convert file max size to byts as well
        if file.size > self.app_setting.FILE_MAX_SIZE * self.size_scale: 
            return False, Response_signal.FILE_SIZE_EXCEEDED.value
        
        return True , Response_signal.FILE_VALIDATED_SUCCESS.value
    

    def generate_unique_file_path(self, orig_file_name: str, Project_ID: str):
        
        project_path = ProjectController().get_project_path(Project_ID=Project_ID)

        random_key = self.generate_random_key()

        clean_file_name = self.get_clean_file_name(orig_file_name=orig_file_name)

        new_file_path = os.path.join(
            project_path,
            random_key + "_" + clean_file_name
        )

        while os.path.exists(new_file_path):

            random_key = self.generate_random_key()

            new_file_path = os.path.join(
            project_path,
            random_key + "_" + clean_file_name
        )
        

        return new_file_path, random_key + "_" + clean_file_name

    def get_clean_file_name(self, orig_file_name: str):

        # remove any special characters, except underscore and .
        cleaned_file_name = re.sub(r'[^\w.]', '', orig_file_name.strip())

        # replace spaces with underscore
        cleaned_file_name = cleaned_file_name.replace(" ", "_")

        return cleaned_file_name
    