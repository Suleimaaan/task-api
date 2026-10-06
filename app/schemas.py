from datetime import datetime
from typing import Annotated, ClassVar

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    EmailStr,
    StringConstraints,
    model_validator,
)

from app.models import TaskStatus

NonBlank200 = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
NonBlank100 = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PatchModel(BaseModel):
    non_nullable: ClassVar[tuple[str, ...]] = ()

    @model_validator(mode="after")
    def _reject_explicit_null(self):
        for field in self.non_nullable:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"Поле '{field}' не может быть null")
        return self


# Users
class UserCreate(BaseModel):
    name: NonBlank100
    email: EmailStr


class UserRead(ORMModel):
    id: int
    name: str
    email: str
    created_at: datetime


# Projects
class ProjectCreate(BaseModel):
    name: NonBlank200
    description: str | None = None


class ProjectUpdate(PatchModel):
    non_nullable = ("name",)
    name: NonBlank200 | None = None
    description: str | None = None


class ProjectRead(ORMModel):
    id: int
    name: str
    description: str | None
    created_at: datetime


# Tasks 
class TaskCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)  # status -> "todo" (str)

    title: NonBlank200
    description: str | None = None
    status: TaskStatus = TaskStatus.todo
    project_id: int
    assignee_id: int | None = None
    deadline: AwareDatetime | None = None


class TaskUpdate(PatchModel):
    model_config = ConfigDict(use_enum_values=True)

    non_nullable = ("title", "status", "project_id")
    title: NonBlank200 | None = None
    description: str | None = None
    status: TaskStatus | None = None
    project_id: int | None = None
    assignee_id: int | None = None
    deadline: AwareDatetime | None = None


class TaskRead(ORMModel):
    id: int
    title: str
    description: str | None
    status: TaskStatus
    project_id: int
    assignee_id: int | None
    deadline: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskList(BaseModel):
    items: list[TaskRead]
    total: int
    limit: int
    offset: int
