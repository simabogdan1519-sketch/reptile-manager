"""
User and group management (admin only, except listing own groups / changing own password).
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..access import require_admin
from ..database import get_db

users_router = APIRouter()
groups_router = APIRouter()


def _groups_by_ids(db: Session, ids: List[int]) -> List[models.Group]:
    ids = list(dict.fromkeys(ids or []))
    groups = db.query(models.Group).filter(models.Group.id.in_(ids)).all() if ids else []
    if len(groups) != len(ids):
        raise HTTPException(400, "Unknown group id")
    return groups


def _users_by_ids(db: Session, ids: List[int]) -> List[models.User]:
    ids = list(dict.fromkeys(ids or []))
    users = db.query(models.User).filter(models.User.id.in_(ids)).all() if ids else []
    if len(users) != len(ids):
        raise HTTPException(400, "Unknown user id")
    return users


def _active_admins(db: Session) -> int:
    return db.query(models.User).filter(models.User.is_admin.is_(True),
                                        models.User.is_active.is_(True)).count()


# ── Users ─────────────────────────────────────────────────────────────────────

@users_router.get("", response_model=List[schemas.UserResponse])
@users_router.get("/", response_model=List[schemas.UserResponse], include_in_schema=False)
def list_users(db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    return db.query(models.User).order_by(models.User.username).all()


@users_router.post("", response_model=schemas.UserResponse, status_code=201)
@users_router.post("/", response_model=schemas.UserResponse, status_code=201, include_in_schema=False)
def create_user(data: schemas.UserAdminCreate, db: Session = Depends(get_db),
                _: models.User = Depends(require_admin)):
    username = data.username.strip()
    if not username or not data.password:
        raise HTTPException(400, "Username and password are required")
    if len(data.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if db.query(models.User).filter(models.User.username == username).first():
        raise HTTPException(400, "Username already exists")
    user = models.User(
        username=username,
        email=data.email or None,
        hashed_password=auth.get_password_hash(data.password),
        is_admin=data.is_admin,
        is_active=data.is_active,
    )
    user.groups = _groups_by_ids(db, data.group_ids)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@users_router.put("/{user_id}", response_model=schemas.UserResponse)
def update_user(user_id: int, data: schemas.UserAdminUpdate, db: Session = Depends(get_db),
                current: models.User = Depends(require_admin)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    d = data.model_dump(exclude_unset=True)

    # Never lock everybody out
    losing_admin = (d.get("is_admin") is False or d.get("is_active") is False) and user.is_admin and user.is_active
    if losing_admin and _active_admins(db) <= 1:
        raise HTTPException(400, "At least one active admin must remain")

    if "username" in d and d["username"]:
        new = d["username"].strip()
        if new != user.username and db.query(models.User).filter(models.User.username == new).first():
            raise HTTPException(400, "Username already exists")
        user.username = new
    if d.get("password"):
        if len(d["password"]) < 6:
            raise HTTPException(400, "Password must be at least 6 characters")
        user.hashed_password = auth.get_password_hash(d["password"])
    if "email" in d:
        user.email = d["email"] or None
    if d.get("is_admin") is not None:
        user.is_admin = d["is_admin"]
    if d.get("is_active") is not None:
        user.is_active = d["is_active"]
    if d.get("group_ids") is not None:
        user.groups = _groups_by_ids(db, d["group_ids"])
    db.commit()
    db.refresh(user)
    return user


@users_router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db),
                current: models.User = Depends(require_admin)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == current.id:
        raise HTTPException(400, "You cannot delete yourself")
    if user.is_admin and user.is_active and _active_admins(db) <= 1:
        raise HTTPException(400, "At least one active admin must remain")
    db.delete(user)
    db.commit()


# ── Groups ────────────────────────────────────────────────────────────────────

def _group_out(g: models.Group, db: Session) -> schemas.GroupResponse:
    count = db.query(func.count(models.Animal.id)).filter(models.Animal.group_id == g.id).scalar()
    return schemas.GroupResponse(
        id=g.id, name=g.name, description=g.description,
        member_ids=[u.id for u in g.members], animal_count=count or 0,
    )


@groups_router.get("", response_model=List[schemas.GroupResponse])
@groups_router.get("/", response_model=List[schemas.GroupResponse], include_in_schema=False)
def list_groups(db: Session = Depends(get_db),
                current: models.User = Depends(auth.get_current_user)):
    """Admins get all groups; regular users get the groups they belong to."""
    if current.is_admin:
        groups = db.query(models.Group).order_by(models.Group.name).all()
    else:
        groups = sorted(current.groups, key=lambda g: g.name.lower())
    out = [_group_out(g, db) for g in groups]
    if not current.is_admin:
        for g in out:
            g.member_ids = []
    return out


@groups_router.post("", response_model=schemas.GroupResponse, status_code=201)
@groups_router.post("/", response_model=schemas.GroupResponse, status_code=201, include_in_schema=False)
def create_group(data: schemas.GroupCreate, db: Session = Depends(get_db),
                 _: models.User = Depends(require_admin)):
    name = data.name.strip()
    if not name:
        raise HTTPException(400, "Name is required")
    if db.query(models.Group).filter(models.Group.name == name).first():
        raise HTTPException(400, "Group already exists")
    g = models.Group(name=name, description=data.description or None)
    g.members = _users_by_ids(db, data.member_ids)
    db.add(g)
    db.commit()
    db.refresh(g)
    return _group_out(g, db)


@groups_router.put("/{group_id}", response_model=schemas.GroupResponse)
def update_group(group_id: int, data: schemas.GroupUpdate, db: Session = Depends(get_db),
                 _: models.User = Depends(require_admin)):
    g = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not g:
        raise HTTPException(404, "Group not found")
    d = data.model_dump(exclude_unset=True)
    if d.get("name"):
        name = d["name"].strip()
        if name != g.name and db.query(models.Group).filter(models.Group.name == name).first():
            raise HTTPException(400, "Group already exists")
        g.name = name
    if "description" in d:
        g.description = d["description"] or None
    if d.get("member_ids") is not None:
        g.members = _users_by_ids(db, d["member_ids"])
    db.commit()
    db.refresh(g)
    return _group_out(g, db)


@groups_router.delete("/{group_id}", status_code=204)
def delete_group(group_id: int, db: Session = Depends(get_db),
                 _: models.User = Depends(require_admin)):
    g = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not g:
        raise HTTPException(404, "Group not found")
    # Animals become unassigned (admin-only) — they are NOT deleted
    db.query(models.Animal).filter(models.Animal.group_id == g.id).update({models.Animal.group_id: None})
    db.delete(g)
    db.commit()
