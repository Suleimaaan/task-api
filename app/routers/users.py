from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserRead
from app.utils import commit_or_http_error, get_or_404

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    # email приводим к нижнему регистру, чтобы a@x.com и A@x.com считались одним адресом
    user = User(name=data.name, email=data.email.lower())
    db.add(user)
    # Уникальность гарантирует БД (UNIQUE), поэтому гонок нет
    commit_or_http_error(db, 409, "Пользователь с таким email уже существует")
    db.refresh(user)
    return user


@router.get("", response_model=list[UserRead])
def list_users(
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(User).order_by(User.id).limit(limit).offset(offset)
    return db.scalars(stmt).all()


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, User, user_id, "Пользователь")
