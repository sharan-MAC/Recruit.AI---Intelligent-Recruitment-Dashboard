from pydantic import BaseModel
from typing import List, Optional

class JobCreate(BaseModel):
    title: str
    description: str
    required_skills: List[str]

class CandidateBase(BaseModel):
    name: str
    email: str
    phone: str
    skills: List[str]
    experience_years: float
    education: str
