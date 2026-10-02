from typing import TypeVar

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

T = TypeVar("T")


def get_or_404(db: Session, model: type[T], obj_id: int, label: str) -> T:
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(404, f"{label} с id={obj_id} не найден")
    return obj


def commit_or_http_error(db: Session, status_code: int, detail: str) -> None:
    """commit(); при нарушении ограничения БД откатывает транзакцию и
    превращает ошибку в HTTP-ответ. Защищает от гонок (проверка прошла,
    а запись успели изменить/удалить до commit)."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code, detail)
