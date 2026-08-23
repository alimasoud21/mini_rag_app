from .BaseController import BaseController
from .ProjectContoller import ProjectController
import os
from models import ProcessingEnum
from langchain_community.document_loaders import TextLoader # type: ignore
from langchain_community.document_loaders import PyMuPDFLoader # type: ignore
from langchain_text_splitters import RecursiveCharacterTextSplitter # type: ignore

class ProcessController(BaseController):
    
    def __init__(self, Project_ID: str):
        super().__init__()

        self.Project_ID = Project_ID
        self.project_path = ProjectController().get_project_path(Project_ID=Project_ID)

    def get_file_extention(self, file_id: str) :#file id is the same as file name
        return os.path.splitext(file_id)[-1]

    def get_file_loader(self, file_id: str):

        file_ext = self.get_file_extention(file_id= file_id)
        file_path = os.path.join(
            self.project_path,
            file_id
        )

        if not os.path.exists(file_path):
            return None
        
        if file_ext == ProcessingEnum.TXT.value:
            return TextLoader(file_path, encoding="utf-8")

        if file_ext == ProcessingEnum.PDF.value:
            return PyMuPDFLoader(file_path) 

        return None
    
    def get_file_content(self, file_id: str):
        
        loader = self.get_file_loader(file_id= file_id)
        
        if loader:
            return loader.load()
        
        return None
    
    def process_file_content(self, file_content: list, file_id: str,
                             chunk_size: int=100, chunk_overlap: int=20 ):
        
        text_splitter = RecursiveCharacterTextSplitter( 
            chunk_size= chunk_size,
            chunk_overlap = chunk_overlap,
            length_function = len,
        )

        # this is a python feature called list comprehension and it's faster than regular for loop
        file_content_text = [
            rec.page_content
            for rec in file_content
        ]
        
        file_content_metadata = [
            rec.metadata
            for rec in file_content
        ]

        chunks = text_splitter.create_documents(
            file_content_text,
            metadatas= file_content_metadata
        )

        return chunks