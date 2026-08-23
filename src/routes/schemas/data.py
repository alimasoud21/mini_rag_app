from pydantic import BaseModel
from typing import Optional

class ProcessRequest(BaseModel):
    file_id : str = None
    chunk_size: Optional[int] = 100
    overlap_size: Optional[int] = 20
    # why not make it just true and false the do_ is indicating that it takes action
    do_reset: Optional[int] = 0 