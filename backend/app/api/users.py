from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid
from typing import List

from app.database.postgres import get_db
from app.database import models

router = APIRouter(prefix="/users", tags=["Users"])

class UserCreate(BaseModel):
    name: str
    email: str
    organization_id: uuid.UUID

class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str
    organization_id: uuid.UUID

    class Config:
        from_attributes = True

@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_org = db.query(models.Organization).filter(models.Organization.id == user.organization_id).first()
    if not db_org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    db_user = models.User(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()
