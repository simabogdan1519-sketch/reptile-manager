from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import models, schemas, auth
from ..database import get_db
from ..ha_client import notify_ha

router = APIRouter()

def _enrich(s: models.Shedding, db: Session) -> schemas.SheddingResponse:
    animal = db.query(models.Animal).filter(models.Animal.id == s.animal_id).first()
    return schemas.SheddingResponse(
        **{k: v for k, v in s.__dict__.items() if not k.startswith("_")},
        animal_name=animal.name if animal else None,
    )

@router.get("", response_model=List[schemas.SheddingResponse])
@router.get("/", response_model=List[schemas.SheddingResponse], include_in_schema=False)
def list_sheddings(
    skip: int = 0,
    limit: int = 100,
    animal_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    q = db.query(models.Shedding)
    if animal_id:
        q = q.filter(models.Shedding.animal_id == animal_id)
    sheddings = q.order_by(models.Shedding.date.desc()).offset(skip).limit(limit).all()
    return [_enrich(s, db) for s in sheddings]

@router.post("", response_model=schemas.SheddingResponse, status_code=201)
@router.post("/", response_model=schemas.SheddingResponse, status_code=201, include_in_schema=False)
async def create_shedding(
    data: schemas.SheddingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    animal = db.query(models.Animal).filter(models.Animal.id == data.animal_id).first()
    if not animal:
        raise HTTPException(404, "Animal not found")

    shedding = models.Shedding(**data.model_dump())
    db.add(shedding)
    db.commit()
    db.refresh(shedding)

    ha_cfg = db.query(models.HAConfig).first()
    if ha_cfg and ha_cfg.enabled and ha_cfg.notify_shedding:
        await notify_ha(
            ha_cfg,
            "reptile_shedding",
            {
                "animal_id": animal.id,
                "animal_name": animal.name,
                "complete": data.complete,
                "in_one_piece": data.in_one_piece,
                "date": data.date.isoformat(),
            },
        )

    return _enrich(shedding, db)

@router.put("/{shedding_id}", response_model=schemas.SheddingResponse)
def update_shedding(
    shedding_id: int,
    data: schemas.SheddingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    shedding = db.query(models.Shedding).filter(models.Shedding.id == shedding_id).first()
    if not shedding:
        raise HTTPException(404, "Shedding not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(shedding, field, value)
    db.commit()
    db.refresh(shedding)
    return _enrich(shedding, db)

@router.delete("/{shedding_id}", status_code=204)
def delete_shedding(
    shedding_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    shedding = db.query(models.Shedding).filter(models.Shedding.id == shedding_id).first()
    if not shedding:
        raise HTTPException(404, "Shedding not found")
    db.delete(shedding)
    db.commit()
