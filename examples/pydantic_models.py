"""Pydantic model serialization examples with TOON and PLOON."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from tknpack import Format, decode, encode


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Task(BaseModel):
    id: int
    title: str
    priority: Priority
    completed: bool
    created_at: datetime


class Project(BaseModel):
    name: str
    tasks: list[Task]


# Encode a Pydantic model to TOON
project = Project(
    name="tknpack",
    tasks=[
        Task(id=1, title="Implement encoder", priority=Priority.HIGH, completed=True, created_at=datetime(2024, 1, 15)),
        Task(id=2, title="Write tests", priority=Priority.MEDIUM, completed=True, created_at=datetime(2024, 1, 16)),
        Task(id=3, title="Add docs", priority=Priority.LOW, completed=False, created_at=datetime(2024, 1, 17)),
    ],
)

print("=== Pydantic Model → TOON ===")
toon_str = encode(project)
print(toon_str)
print()

# Decode TOON back to a Pydantic model
print("=== TOON → Pydantic Model ===")
restored = decode(toon_str, Project)
print(f"Project: {restored.name}")
for task in restored.tasks:
    status = "done" if task.completed else "todo"
    print(f"  [{status}] {task.title} ({task.priority.value})")
print()

# Encode the same model to PLOON
print("=== Pydantic Model → PLOON ===")
ploon_str = encode(project, format=Format.PLOON)
print(ploon_str)
print()

# Decode PLOON back to a Pydantic model
print("=== PLOON → Pydantic Model ===")
restored_ploon = decode(ploon_str, Project, format=Format.PLOON)
print(f"Project: {restored_ploon.name}")
for task in restored_ploon.tasks:
    status = "done" if task.completed else "todo"
    print(f"  [{status}] {task.title} ({task.priority.value})")
