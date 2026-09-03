from .BaseDataModel import BaseDataModel
from .db_schemas import Project
from sqlalchemy.future import select
from sqlalchemy import func
import math
class ProjectModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_client = db_client

    @classmethod
    async def create_instacne(cls, db_client: object):
        #call init
        instance=cls(db_client) 
        return instance

    async def create_project(self, project: Project):
        async with self.db_client() as session:
            async with session.begin():
                session.add(project)
            await session.commit()
            await session.refresh(project)

        return project
    
    async def get_project_or_create_one(self, project_id: str):
        async with self.db_client() as session:
            async with session.begin():
                query = select(Project).where(Project.project_id == project_id)
                result = await session.execute(query)
                project = result.scalar_one_or_none()
                if project is None:
                    project_record = Project(
                        project_id = project_id
                    )
                    project = await self.create_project(project= project_record)
                    return project
                else:
                    return project 

    async def get_all_projects(self, page_number : int = 1, page_size: int = 10):

        async with self.db_client() as session:
            async with session.begin():
                #count total numberr of documents
                total_documents = await session.execute(select(
                    func.count(Project.project_id)
                ))
                total_documents = total_documents.scalar_one()

                #calclute total number of pages
                total_pages = math.ceil(total_documents / page_size) if total_documents > 0 else 0

                query = select(Project).offset((page_number - 1) * page_size).limit(page_size)
                projects = (await session.execute(query)).scalars().all()

                return projects, total_pages

