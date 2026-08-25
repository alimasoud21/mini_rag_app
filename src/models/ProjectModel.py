from .BaseDataModel import BaseDataModel
from .db_schemas import Project
from .enums.DataBaseEnum import DataBaseEnum

class ProjectModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        #it does not create the collection in the actual database. 
        #It simply creates a local Python object that acts as a pointer 
        self.collection = self.db_client[DataBaseEnum.COLLECTION_PROJECT_NAME.value]

    @classmethod
    async def create_instacne(cls, db_client: object):
        #call init
        instance=cls(db_client) 
        await instance.init_collection()
        return instance


    async def init_collection(self):
        all_collections = await self.db_client.list_collection_names()
        if DataBaseEnum.COLLECTION_PROJECT_NAME.value not in all_collections:
            self.collection = self.db_client[DataBaseEnum.COLLECTION_PROJECT_NAME.value]
            indexes =  Project.get_indexes()
            for index in indexes:
                await self.collection.create_index(
                    index["key"],
                    name = index["name"],
                    unique = index["unique"]

                )


    async def create_project(self, project: Project):

        #insert_one is motor function that only takes dict
        result = await self.collection.insert_one(project.dict(by_alias= True, exclude_unset=True))
        project.id = result.inserted_id
        
        return project
    
    async def get_project_or_create_one(self, Project_ID: str):

        record = await self.collection.find_one({
            
            'Project_ID': Project_ID
        })

        if record is None:
            #create new projcet
            project = Project(Project_ID= Project_ID)
            project = await self.create_project(project=project)

            return project
        #recored is dict type so convert it into Project type

        return Project(**record)
    
    async def get_all_projects(self, page_number : int = 1, page_size: int = 10):

        #count total numberr of documents
        total_documents = await self.collection.count_documents({})

        #calclute total number of pages
        total_pages = total_documents // page_size
        if ( total_documents % page_size ) > 0:
            total_pages += 1

        curser = self.collection.find().skip( (page_number - 1) * page_size).limit(page_size)
        projects = []

        async for document in curser:
            projects.append(
                Project(**document)
            )

        return projects, total_pages