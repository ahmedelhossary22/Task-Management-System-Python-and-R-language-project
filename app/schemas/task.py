from pydantic import BaseModel
from typing import Optional, Literal


class TaskCreate(BaseModel):
    title: str
    description: str
    priority: Literal["Low", "Medium", "High"]
    project_id: int
    assigned_to: int


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Literal["To Do", "In Progress", "Done"]] = None
    priority: Optional[Literal["Low", "Medium", "High"]] = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    status: str
    priority: str
    project_id: int
    assigned_to: int

    class Config:
        from_attributes = True