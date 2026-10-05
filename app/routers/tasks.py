from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, Task, TaskStatus, User
from app.schemas import TaskCreate, TaskList, TaskRead, TaskUpdate
from app.utils import commit_or_http_error, get_or_404

router = APIRouter(prefix="/tasks", tags=["tasks"])

FK_RACE_MSG = "Проект или исполнитель не найден"


@router.post("", response_model=TaskRead, status_code=201)
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    get_or_404(db, Project, data.project_id, "Проект")
    if data.assignee_id is not None:
        get_or_404(db, User, data.assignee_id, "Пользователь")

    task = Task(**data.model_dump())
    db.add(task)
    commit_or_http_error(db, 404, FK_RACE_MSG)
    db.refresh(task)
    return task


@router.get("", response_model=TaskList)
def list_tasks(
    project_id: int | None = None,
    status: TaskStatus | None = None,
    assignee_id: int | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    filters = []
    if project_id is not None:
        filters.append(Task.project_id == project_id)
    if status is not None:
        filters.append(Task.status == status.value)
    if assignee_id is not None:
        filters.append(Task.assignee_id == assignee_id)
        
    total = db.scalar(select(func.count()).select_from(Task).where(*filters))

    stmt = (
        select(Task)
        .where(*filters)
        .order_by(Task.created_at.desc(), Task.id.desc())  # id — стабильный tie-breaker
        .limit(limit)
        .offset(offset)
    )
    items = db.scalars(stmt).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Task, task_id, "Задача")


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    task = get_or_404(db, Task, task_id, "Задача")
    changes = data.model_dump(exclude_unset=True)

    # Проверяем существование только если значение реально задаётся (не None)
    if changes.get("project_id") is not None:
        get_or_404(db, Project, changes["project_id"], "Проект")
    if changes.get("assignee_id") is not None:
        get_or_404(db, User, changes["assignee_id"], "Пользователь")

    for field, value in changes.items():
        setattr(task, field, value)  # None у assignee_id/deadline/description = очистка
    commit_or_http_error(db, 404, FK_RACE_MSG)
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = get_or_404(db, Task, task_id, "Задача")
    db.delete(task)
    db.commit()
    return Response(status_code=204)
