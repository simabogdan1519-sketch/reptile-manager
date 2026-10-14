from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, auth
from ..database import get_db
from ..access import get_animal_or_404

router = APIRouter()

@router.get("/animal/{animal_id}", response_model=List[schemas.CustomFieldResponse])
def get_animal_fields(
    animal_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    animal = get_animal_or_404(db, animal_id, current_user)
    return animal.custom_fields

@router.post("/animal/{animal_id}", response_model=schemas.CustomFieldResponse, status_code=201)
def create_field(
    animal_id: int,
    data: schemas.CustomFieldCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    animal = get_animal_or_404(db, animal_id, current_user)
    field = models.CustomField(animal_id=animal_id, **data.model_dump())
    db.add(field)
    db.commit()
    db.refresh(field)
    return field

@router.put("/{field_id}", response_model=schemas.CustomFieldResponse)
def update_field(
    field_id: int,
    data: schemas.CustomFieldUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    field = db.query(models.CustomField).filter(models.CustomField.id == field_id).first()
    if not field:
        raise HTTPException(404, "Field not found")
    get_animal_or_404(db, field.animal_id, current_user)
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(field, key, val)
    db.commit()
    db.refresh(field)
    return field

@router.delete("/{field_id}", status_code=204)
def delete_field(
    field_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    field = db.query(models.CustomField).filter(models.CustomField.id == field_id).first()
    if not field:
        raise HTTPException(404, "Field not found")
    get_animal_or_404(db, field.animal_id, current_user)
    db.delete(field)
    db.commit()
