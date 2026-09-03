from .BaseDataModel import BaseDataModel
from .db_schemas import Asset
from sqlalchemy.future import select
from sqlalchemy import func, insert, delete

class AssetModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance
    
    async def create_asset(self, asset: Asset):
        async with self.db_client() as session:
            async with session.begin():
                session.add(asset)
        return asset
    
    async def get_asset(self, project_id: str, asset_name: str):
            async with self.db_client() as session:
                result  = await session.execute(select(Asset).where(
                    Asset.asset_project_id == project_id,
                    Asset.asset_name == asset_name,
                    ))
                asset = result.scaler_one_or_none()
            return asset 
    
    async def get_all_project_assets(self, project_id: str, asset_type: str ):
        
        async with self.db_client() as session:
            query = select(Asset).where(Asset.asset_project_id == project_id)
            result = await session.execute(query)
            records = result.scalars().all()
        return records
    
    

       
    