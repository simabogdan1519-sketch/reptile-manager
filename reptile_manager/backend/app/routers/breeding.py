from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import models, schemas, auth
from ..database import get_db
from ..ha_client import notify_ha

router = APIRouter()

def _enrich(event: models.BreedingEvent, db: Session) -> schemas.BreedingEventResponse:
    female = db.query(models.Animal).filter(models.Animal.id == event.female_id).first()
    male   = db.query(models.Animal).filter(models.Animal.id == event.male_id).first()
    # Fallback if an animal was deleted
    if not female:
        female = models.Animal(id=event.female_id, name=f"[gelöscht #{event.female_id}]",
                               species="?", sex=models.Sex.unknown, status="inactive")
    if not male:
        male   = models.Animal(id=event.male_id,   name=f"[gelöscht #{event.male_id}]",
                               species="?", sex=models.Sex.unknown, status="inactive")
    data = {k: v for k, v in event.__dict__.items() if not k.startswith("_")}
    data["female"] = schemas.AnimalSummary.model_validate(female)
    data["male"]   = schemas.AnimalSummary.model_validate(male)
    return schemas.BreedingEventResponse(**data)

@router.get("", response_model=List[schemas.BreedingEventResponse])
@router.get("/", response_model=List[schemas.BreedingEventResponse], include_in_schema=False)
def list_breeding(
    skip: int = 0,
    limit: int = 100,
    female_id: Optional[int] = None,
    male_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    q = db.query(models.BreedingEvent)
    if female_id:
        q = q.filter(models.BreedingEvent.female_id == female_id)
    if male_id:
        q = q.filter(models.BreedingEvent.male_id == male_id)
    events = q.order_by(models.BreedingEvent.created_at.desc()).offset(skip).limit(limit).all()
    return [_enrich(e, db) for e in events]

@router.post("", response_model=schemas.BreedingEventResponse, status_code=201)
@router.post("/", response_model=schemas.BreedingEventResponse, status_code=201, include_in_schema=False)
async def create_breeding(
    data: schemas.BreedingEventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    female = db.query(models.Animal).filter(models.Animal.id == data.female_id).first()
    male = db.query(models.Animal).filter(models.Animal.id == data.male_id).first()
    if not female:
        raise HTTPException(404, "Female animal not found")
    if not male:
        raise HTTPException(404, "Male animal not found")

    event = models.BreedingEvent(**data.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)

    ha_cfg = db.query(models.HAConfig).first()
    if ha_cfg and ha_cfg.enabled and ha_cfg.notify_breeding:
        await notify_ha(
            ha_cfg,
            "reptile_breeding",
            {
                "female_name": female.name,
                "male_name": male.name,
                "date_paired": str(data.date_paired) if data.date_paired else None,
            },
        )

    return _enrich(event, db)

@router.get("/{event_id}", response_model=schemas.BreedingEventResponse)
def get_breeding(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    event = db.query(models.BreedingEvent).filter(models.BreedingEvent.id == event_id).first()
    if not event:
        raise HTTPException(404, "Breeding event not found")
    return _enrich(event, db)

@router.put("/{event_id}", response_model=schemas.BreedingEventResponse)
def update_breeding(
    event_id: int,
    data: schemas.BreedingEventUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    event = db.query(models.BreedingEvent).filter(models.BreedingEvent.id == event_id).first()
    if not event:
        raise HTTPException(404, "Breeding event not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return _enrich(event, db)

@router.delete("/{event_id}", status_code=204)
def delete_breeding(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    event = db.query(models.BreedingEvent).filter(models.BreedingEvent.id == event_id).first()
    if not event:
        raise HTTPException(404, "Breeding event not found")
    db.delete(event)
    db.commit()
