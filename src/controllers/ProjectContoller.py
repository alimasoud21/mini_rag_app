from .BaseController import BaseContorller
import os

class ProjectController(BaseContorller):

    def __init__(self):
        super().__init__()

    def get_project_path(self, Project_ID: str):

        project_dir = os.path.join(
            self.files_dir,
            Project_ID
        )

        if not os.path.exists(project_dir):
            os.makedirs(project_dir)
        
        return project_dir