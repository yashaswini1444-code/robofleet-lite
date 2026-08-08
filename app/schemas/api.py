from pydantic import BaseModel, Field

class Point(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)

class TaskCreate(BaseModel):
    pickup: Point
    delivery: Point

class ObstacleCreate(BaseModel):
    position: Point

class CompareRequest(BaseModel):
    start: Point
    goal: Point

