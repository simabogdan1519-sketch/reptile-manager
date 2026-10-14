from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import models, schemas, auth
from ..database import get_db
from ..access import scope_by_animal, get_animal_or_404
from ..ha_client import notify_ha

router = APIRouter()

def _enrich(f: models.Feeding, db: Session) -> schemas.FeedingResponse:
    animal = db.query(models.Animal).filter(models.Animal.id == f.animal_id).first()
    return schemas.FeedingResponse(
        **{k: v for k, v in f.__dict__.items() if not k.startswith("_")},
        animal_name=animal.name if animal else None,
    )

@router.get("", response_model=List[schemas.FeedingResponse])
@router.get("/", response_model=List[schemas.FeedingResponse], include_in_schema=False)
def list_feedings(
    skip: int = 0,
    limit: int = 100,
    animal_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    q = scope_by_animal(db.query(models.Feeding), models.Feeding.animal_id, db, current_user)
    if animal_id:
        q = q.filter(models.Feeding.animal_id == animal_id)
    feedings = q.order_by(models.Feeding.date.desc()).offset(skip).limit(limit).all()
    return [_enrich(f, db) for f in feedings]

@router.post("", response_model=schemas.FeedingResponse, status_code=201)
@router.post("/", response_model=schemas.FeedingResponse, status_code=201, include_in_schema=False)
async def create_feeding(
    data: schemas.FeedingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    animal = get_animal_or_404(db, data.animal_id, current_user)

    feeding = models.Feeding(**data.model_dump())
    db.add(feeding)
    db.commit()
    db.refresh(feeding)

    # Push to Home Assistant
    ha_cfg = db.query(models.HAConfig).first()
    if ha_cfg and (ha_cfg.enabled or ha_cfg.entity_sync is not False) and ha_cfg.notify_feeding:
        await notify_ha(
            ha_cfg,
            "reptile_feeding",
            {
                "animal_id": animal.id,
                "animal_name": animal.name,
                "food_type": data.food_type,
                "food_size": data.food_size,
                "food_count": data.food_count,
                "accepted": data.accepted,
                "live": data.live,
                "date": data.date.isoformat(),
            },
        )

    return _enrich(feeding, db)

@router.put("/{feeding_id}", response_model=schemas.FeedingResponse)
def update_feeding(
    feeding_id: int,
    data: schemas.FeedingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    feeding = db.query(models.Feeding).filter(models.Feeding.id == feeding_id).first()
    if not feeding:
        raise HTTPException(404, "Feeding not found")
    get_animal_or_404(db, feeding.animal_id, current_user)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("animal_id") is not None:
        get_animal_or_404(db, changes["animal_id"], current_user)
    for field, value in changes.items():
        setattr(feeding, field, value)
    db.commit()
    db.refresh(feeding)
    return _enrich(feeding, db)

@router.delete("/{feeding_id}", status_code=204)
def delete_feeding(
    feeding_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    feeding = db.query(models.Feeding).filter(models.Feeding.id == feeding_id).first()
    if not feeding:
        raise HTTPException(404, "Feeding not found")
    get_animal_or_404(db, feeding.animal_id, current_user)
    db.delete(feeding)
    db.commit()
