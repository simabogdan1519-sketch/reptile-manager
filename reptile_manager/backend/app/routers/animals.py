import os, re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import models, schemas, auth
from ..database import get_db

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/app/uploads")
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
router = APIRouter()

def _next_tracking_id(db: Session) -> str:
    """Nächste freie Nummer als String zurückgeben."""
    existing = [r[0] for r in db.query(models.Animal.tracking_id).all() if r[0]]
    used = set()
    for tid in existing:
        m = re.search(r'^(\d+)$', tid.strip())
        if m:
            used.add(int(m.group(1)))
    i = 1
    while i in used:
        i += 1
    return str(i)

def _enrich_animal(animal: models.Animal, db: Session) -> schemas.AnimalResponse:
    mother = db.query(models.Animal).filter(models.Animal.id == animal.mother_id).first() if animal.mother_id else None
    father = db.query(models.Animal).filter(models.Animal.id == animal.father_id).first() if animal.father_id else None
    data = {k: v for k, v in animal.__dict__.items() if not k.startswith("_")}
    data["mother"] = schemas.AnimalSummary.model_validate(mother) if mother else None
    data["father"] = schemas.AnimalSummary.model_validate(father) if father else None
    data["custom_fields"] = [schemas.CustomFieldResponse.model_validate(cf) for cf in animal.custom_fields]
    # Sync is_active from status for backwards compat
    data["is_active"] = animal.status == "active"
    return schemas.AnimalResponse(**data)

@router.get("", response_model=List[schemas.AnimalResponse])
@router.get("/", response_model=List[schemas.AnimalResponse], include_in_schema=False)
def list_animals(
    skip: int = 0, limit: int = 100,
    search: Optional[str] = None,
    active_only: bool = True,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    q = db.query(models.Animal)
    if status:
        q = q.filter(models.Animal.status == status)
    elif active_only:
        q = q.filter(models.Animal.status == "active")
    if search:
        t = f"%{search}%"
        q = q.filter(
            models.Animal.name.ilike(t) | models.Animal.species.ilike(t)
            | models.Animal.morph.ilike(t) | models.Animal.common_name.ilike(t)
            | models.Animal.tracking_id.ilike(t)
        )
    animals = q.order_by(models.Animal.name).offset(skip).limit(limit).all()
    return [_enrich_animal(a, db) for a in animals]

@router.post("", response_model=schemas.AnimalResponse, status_code=201)
@router.post("/", response_model=schemas.AnimalResponse, status_code=201, include_in_schema=False)
def create_animal(
    data: schemas.AnimalCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    d = data.model_dump()
    if not d.get("tracking_id"):
        d["tracking_id"] = _next_tracking_id(db)
    # Sync is_active from status
    d["is_active"] = d.get("status", "active") == "active"
    animal = models.Animal(**d)
    db.add(animal)
    db.commit()
    db.refresh(animal)
    return _enrich_animal(animal, db)

@router.post("/bulk", response_model=List[schemas.AnimalResponse], status_code=201)
def create_animals_bulk(
    data: schemas.AnimalBulkCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Create multiple animals at once (e.g. from a clutch/breeding event)."""
    created = []
    for _ in range(data.quantity):
        d = data.animal_data.model_dump()
        d["tracking_id"] = _next_tracking_id(db)
        d["is_active"] = d.get("status", "active") == "active"
        animal = models.Animal(**d)
        db.add(animal)
        db.flush()   # get ID without committing, so _next_tracking_id sees it
        db.refresh(animal)
        created.append(animal)
    db.commit()
    return [_enrich_animal(a, db) for a in created]

@router.get("/{animal_id}", response_model=schemas.AnimalResponse)
def get_animal(
    animal_id: int, db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    a = db.query(models.Animal).filter(models.Animal.id == animal_id).first()
    if not a: raise HTTPException(404, "Animal not found")
    return _enrich_animal(a, db)

@router.put("/{animal_id}", response_model=schemas.AnimalResponse)
def update_animal(
    animal_id: int, data: schemas.AnimalUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    animal = db.query(models.Animal).filter(models.Animal.id == animal_id).first()
    if not animal: raise HTTPException(404, "Animal not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(animal, field, value)
    # Sync is_active from status
    if data.status is not None:
        animal.is_active = data.status == "active"
    db.commit()
    db.refresh(animal)
    return _enrich_animal(animal, db)

@router.delete("/{animal_id}", status_code=204)
def delete_animal(
    animal_id: int, db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    a = db.query(models.Animal).filter(models.Animal.id == animal_id).first()
    if not a: raise HTTPException(404, "Animal not found")
    db.delete(a)
    db.commit()

@router.post("/{animal_id}/photo")
async def upload_photo(
    animal_id: int, file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    animal = db.query(models.Animal).filter(models.Animal.id == animal_id).first()
    if not animal: raise HTTPException(404, "Animal not found")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Only images allowed")
    ext = Path(file.filename).suffix.lower() or ".jpg"
    animal_dir = Path(UPLOAD_DIR) / "animals" / str(animal_id)
    animal_dir.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 10 MB)")
    file_path = animal_dir / f"photo{ext}"
    with open(file_path, "wb") as f:
        f.write(content)
    animal.photo_url = f"/uploads/animals/{animal_id}/photo{ext}"
    db.commit()
    return {"photo_url": animal.photo_url}

@router.delete("/{animal_id}/photo", status_code=204)
def delete_photo(
    animal_id: int, db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    animal = db.query(models.Animal).filter(models.Animal.id == animal_id).first()
    if not animal: raise HTTPException(404, "Animal not found")
    if animal.photo_url:
        try:
            Path(UPLOAD_DIR + animal.photo_url.replace("/uploads", "")).unlink(missing_ok=True)
        except Exception:
            pass
        animal.photo_url = None
        db.commit()

@router.get("/{animal_id}/feedings", response_model=List[schemas.FeedingResponse])
def get_animal_feedings(
    animal_id: int, skip: int = 0, limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    animal = db.query(models.Animal).filter(models.Animal.id == animal_id).first()
    if not animal: raise HTTPException(404, "Animal not found")
    feedings = (db.query(models.Feeding).filter(models.Feeding.animal_id == animal_id)
                .order_by(models.Feeding.date.desc()).offset(skip).limit(limit).all())
    return [schemas.FeedingResponse(**{k: v for k, v in f.__dict__.items() if not k.startswith("_")}, animal_name=animal.name)
            for f in feedings]

@router.get("/{animal_id}/sheddings", response_model=List[schemas.SheddingResponse])
def get_animal_sheddings(
    animal_id: int, skip: int = 0, limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    animal = db.query(models.Animal).filter(models.Animal.id == animal_id).first()
    if not animal: raise HTTPException(404, "Animal not found")
    sheddings = (db.query(models.Shedding).filter(models.Shedding.animal_id == animal_id)
                 .order_by(models.Shedding.date.desc()).offset(skip).limit(limit).all())
    return [schemas.SheddingResponse(**{k: v for k, v in s.__dict__.items() if not k.startswith("_")}, animal_name=animal.name)
            for s in sheddings]

@router.get("/{animal_id}/tree")
def get_family_tree(
    animal_id: int, db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    animal = db.query(models.Animal).filter(models.Animal.id == animal_id).first()
    if not animal: raise HTTPException(404, "Animal not found")

    def node(a):
        if not a: return None
        return {"id": a.id, "name": a.name, "species": a.species, "common_name": a.common_name,
                "morph": a.morph, "sex": a.sex.value if a.sex else "unknown",
                "photo_url": a.photo_url, "tracking_id": a.tracking_id}

    def ancestors(a, depth=3):
        if not a or depth == 0: return node(a)
        n = node(a)
        if n:
            m = db.query(models.Animal).filter(models.Animal.id == a.mother_id).first() if a.mother_id else None
            f = db.query(models.Animal).filter(models.Animal.id == a.father_id).first() if a.father_id else None
            n["mother"] = ancestors(m, depth - 1)
            n["father"] = ancestors(f, depth - 1)
        return n

    maternal = db.query(models.Animal).filter(models.Animal.mother_id == animal_id).all()
    paternal = db.query(models.Animal).filter(models.Animal.father_id == animal_id).all()
    offspring = {a.id: node(a) for a in maternal + paternal}
    return {"animal": ancestors(animal), "offspring": list(offspring.values())}
