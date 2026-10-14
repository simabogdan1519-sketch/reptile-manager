"""
Group-based access control.

Rules:
- Admins see and edit everything.
- Regular users see and edit only animals whose group_id is one of their groups
  (plus the feedings / sheddings / breeding events / custom fields of those animals).
- Animals without a group are visible to admins only.
"""
from typing import Optional, Set
from fastapi import Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, Query

from . import models, auth


def require_admin(current_user: models.User = Depends(auth.get_current_user)) -> models.User:
    if not current_user.is_admin:
        raise HTTPException(403, "Admin rights required")
    return current_user


def group_ids(user: models.User) -> Optional[Set[int]]:
    """None = unrestricted (admin); otherwise the set of the user's group ids."""
    if user.is_admin:
        return None
    return {g.id for g in user.groups}


def scope_animals(q: Query, user: models.User) -> Query:
    ids = group_ids(user)
    if ids is None:
        return q
    if not ids:
        return q.filter(False)
    return q.filter(models.Animal.group_id.in_(ids))


def visible_animal_ids_subq(db: Session, user: models.User):
    return scope_animals(db.query(models.Animal.id), user).subquery()


def can_access_animal(animal: Optional[models.Animal], user: models.User) -> bool:
    if animal is None:
        return False
    ids = group_ids(user)
    return ids is None or (animal.group_id is not None and animal.group_id in ids)


def get_animal_or_404(db: Session, animal_id: int, user: models.User) -> models.Animal:
    a = db.query(models.Animal).filter(models.Animal.id == animal_id).first()
    if not can_access_animal(a, user):
        raise HTTPException(404, "Animal not found")
    return a


def scope_by_animal(q: Query, column, db: Session, user: models.User) -> Query:
    """Filter a query on a table with an animal_id column."""
    if user.is_admin:
        return q
    sub = visible_animal_ids_subq(db, user)
    return q.filter(column.in_(db.query(sub.c.id)))


def scope_breeding(q: Query, db: Session, user: models.User) -> Query:
    if user.is_admin:
        return q
    sub = db.query(visible_animal_ids_subq(db, user).c.id)
    return q.filter(or_(models.BreedingEvent.female_id.in_(sub),
                        models.BreedingEvent.male_id.in_(sub)))


def check_breeding(event: Optional[models.BreedingEvent], db: Session, user: models.User):
    if event is None:
        raise HTTPException(404, "Breeding event not found")
    if user.is_admin:
        return event
    f = db.query(models.Animal).filter(models.Animal.id == event.female_id).first()
    m = db.query(models.Animal).filter(models.Animal.id == event.male_id).first()
    if not (can_access_animal(f, user) or can_access_animal(m, user)):
        raise HTTPException(404, "Breeding event not found")
    return event


def resolve_group_for_write(db: Session, user: models.User, requested: Optional[int], *, is_create: bool,
                            current: Optional[int] = None) -> Optional[int]:
    """Validate the group a user wants to put an animal into."""
    if requested is not None and not db.query(models.Group).filter(models.Group.id == requested).first():
        raise HTTPException(400, "Group does not exist")
    if user.is_admin:
        return requested
    ids = group_ids(user)
    if requested is None:
        if is_create:
            if len(ids) == 1:
                return next(iter(ids))
            raise HTTPException(400, "Please choose a group for this animal")
        raise HTTPException(400, "Only admins can remove an animal from its group")
    if requested not in ids:
        raise HTTPException(403, "You are not a member of this group")
    return requested
