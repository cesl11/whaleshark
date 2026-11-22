"""Where all the models for organizations and their components are defined."""

from pydantic import BaseModel
from typing import Iterable, Any, Optional, List
from langchain import tools


class StaffMember(BaseModel):
    llm: Any # change this later
    tools: Optional[List[tools.BaseTool]] = None


class Team(BaseModel):
    name: str
    members: Iterable[StaffMember]
    
