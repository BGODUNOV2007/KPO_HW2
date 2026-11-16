"""
Адаптеры репозиториев — инфраструктурный слой.
Реализует порты (интерфейсы) из доменного слоя.

Предоставляет две реализации:
- InMemory* — хранение в оперативной памяти (для тестов)
- JsonFile* — персистентное хранение в JSON-файлах (для продакшна)
"""
from __future__ import annotations

import json
import os
from datetime import date
from typing import Dict, List, Optional

from src.domain.entities import Criterion, Evaluation, Student
from src.domain.repositories import (
    ICriterionRepository,
    IEvaluationRepository,
    IStudentRepository,
)
from src.domain.value_objects import (
    CriterionId,
    EvaluationId,
    Score,
    StudentId,
    Weight,
)


# ---------------------------------------------------------------------------
# Вспомогательные функции сериализации/десериализации
# ---------------------------------------------------------------------------

def _student_to_dict(s: Student) -> dict:
    """Преобразует Student в словарь для JSON-сериализации."""
    return {
        "id": s.id.value,
        "full_name": s.full_name,
        "group": s.group,
    }


def _student_from_dict(d: dict) -> Student:
    """Восстанавливает Student из словаря."""
    return Student(
        id=StudentId(d["id"]),
        full_name=d["full_name"],
        group=d["group"],
    )


def _criterion_to_dict(c: Criterion) -> dict:
    """Преобразует Criterion в словарь для JSON-сериализации."""
    return {
        "id": c.id.value,
        "name": c.name,
        "max_score": c.max_score,
        "weight": c.weight.value,
        "description": c.description,
    }


def _criterion_from_dict(d: dict) -> Criterion:
    """Восстанавливает Criterion из словаря."""
    return Criterion(
        id=CriterionId(d["id"]),
        name=d["name"],
        max_score=float(d["max_score"]),
        weight=Weight(float(d["weight"])),
        description=d.get("description", ""),
    )


def _evaluation_to_dict(ev: Evaluation) -> dict:
    """Преобразует Evaluation в словарь для JSON-сериализации."""
    return {
        "id": ev.id.value,
        "student_id": ev.student_id.value,
        "criterion_id": ev.criterion_id.value,
        "score": ev.score.value,
        "eval_date": ev.eval_date.isoformat(),
        "comment": ev.comment,
    }


def _evaluation_from_dict(d: dict) -> Evaluation:
    """Восстанавливает Evaluation из словаря."""
    return Evaluation(
        id=EvaluationId(d["id"]),
        student_id=StudentId(d["student_id"]),
        criterion_id=CriterionId(d["criterion_id"]),
        score=Score(float(d["score"])),
        eval_date=date.fromisoformat(d["eval_date"]),
        comment=d.get("comment", ""),
    )


# ---------------------------------------------------------------------------
# In-Memory репозитории (для тестов и временного использования)
# ---------------------------------------------------------------------------

class InMemoryStudentRepository(IStudentRepository):
    """Хранилище студентов в оперативной памяти."""

    def __init__(self) -> None:
        self._store: Dict[str, Student] = {}

    def save(self, student: Student) -> None:
        self._store[student.id.value] = student

    def find_by_id(self, student_id: StudentId) -> Optional[Student]:
        return self._store.get(student_id.value)

    def find_all(self) -> List[Student]:
        return list(self._store.values())

    def delete(self, student_id: StudentId) -> None:
        self._store.pop(student_id.value, None)


class InMemoryCriterionRepository(ICriterionRepository):
    """Хранилище критериев в оперативной памяти."""

    def __init__(self) -> None:
        self._store: Dict[str, Criterion] = {}

    def save(self, criterion: Criterion) -> None:
        self._store[criterion.id.value] = criterion

    def find_by_id(self, criterion_id: CriterionId) -> Optional[Criterion]:
        return self._store.get(criterion_id.value)

    def find_all(self) -> List[Criterion]:
        return list(self._store.values())

    def delete(self, criterion_id: CriterionId) -> None:
        self._store.pop(criterion_id.value, None)


class InMemoryEvaluationRepository(IEvaluationRepository):
    """Хранилище оценок в оперативной памяти."""

    def __init__(self) -> None:
        self._store: Dict[str, Evaluation] = {}

    def save(self, evaluation: Evaluation) -> None:
        self._store[evaluation.id.value] = evaluation

    def find_by_id(self, evaluation_id: EvaluationId) -> Optional[Evaluation]:
        return self._store.get(evaluation_id.value)

    def find_by_student(self, student_id: StudentId) -> List[Evaluation]:
        return [ev for ev in self._store.values() if ev.student_id == student_id]

    def find_all(self) -> List[Evaluation]:
        return list(self._store.values())

    def delete(self, evaluation_id: EvaluationId) -> None:
        self._store.pop(evaluation_id.value, None)


# ---------------------------------------------------------------------------
# JSON-файловые репозитории (персистентное хранение)
# ---------------------------------------------------------------------------

class JsonFileStudentRepository(IStudentRepository):
    """Хранилище студентов в JSON-файле."""

    def __init__(self, file_path: str) -> None:
        self._path = file_path
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Создаёт файл с пустым массивом, если он не существует."""
        dir_name = os.path.dirname(self._path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        if not os.path.exists(self._path):
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump([], f)

    def _load(self) -> Dict[str, Student]:
        with open(self._path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {d["id"]: _student_from_dict(d) for d in data}

    def _save_all(self, store: Dict[str, Student]) -> None:
        tmp_path = f"{self._path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump([_student_to_dict(s) for s in store.values()], f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self._path)

    def save(self, student: Student) -> None:
        store = self._load()
        store[student.id.value] = student
        self._save_all(store)

    def find_by_id(self, student_id: StudentId) -> Optional[Student]:
        return self._load().get(student_id.value)

    def find_all(self) -> List[Student]:
        return list(self._load().values())

    def delete(self, student_id: StudentId) -> None:
        store = self._load()
        store.pop(student_id.value, None)
        self._save_all(store)


class JsonFileCriterionRepository(ICriterionRepository):
    """Хранилище критериев в JSON-файле."""

    def __init__(self, file_path: str) -> None:
        self._path = file_path
        self._ensure_file()

    def _ensure_file(self) -> None:
        dir_name = os.path.dirname(self._path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        if not os.path.exists(self._path):
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump([], f)

    def _load(self) -> Dict[str, Criterion]:
        with open(self._path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {d["id"]: _criterion_from_dict(d) for d in data}

    def _save_all(self, store: Dict[str, Criterion]) -> None:
        tmp_path = f"{self._path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump([_criterion_to_dict(c) for c in store.values()], f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self._path)

    def save(self, criterion: Criterion) -> None:
        store = self._load()
        store[criterion.id.value] = criterion
        self._save_all(store)

    def find_by_id(self, criterion_id: CriterionId) -> Optional[Criterion]:
        return self._load().get(criterion_id.value)

    def find_all(self) -> List[Criterion]:
        return list(self._load().values())

    def delete(self, criterion_id: CriterionId) -> None:
        store = self._load()
        store.pop(criterion_id.value, None)
        self._save_all(store)


class JsonFileEvaluationRepository(IEvaluationRepository):
    """Хранилище оценок в JSON-файле."""

    def __init__(self, file_path: str) -> None:
        self._path = file_path
        self._ensure_file()

    def _ensure_file(self) -> None:
        dir_name = os.path.dirname(self._path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        if not os.path.exists(self._path):
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump([], f)

    def _load(self) -> Dict[str, Evaluation]:
        with open(self._path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {d["id"]: _evaluation_from_dict(d) for d in data}

    def _save_all(self, store: Dict[str, Evaluation]) -> None:
        tmp_path = f"{self._path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump([_evaluation_to_dict(ev) for ev in store.values()], f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self._path)

    def save(self, evaluation: Evaluation) -> None:
        store = self._load()
        store[evaluation.id.value] = evaluation
        self._save_all(store)

    def find_by_id(self, evaluation_id: EvaluationId) -> Optional[Evaluation]:
        return self._load().get(evaluation_id.value)

    def find_by_student(self, student_id: StudentId) -> List[Evaluation]:
        return [ev for ev in self._load().values() if ev.student_id == student_id]

    def find_all(self) -> List[Evaluation]:
        return list(self._load().values())

    def delete(self, evaluation_id: EvaluationId) -> None:
        store = self._load()
        store.pop(evaluation_id.value, None)
        self._save_all(store)
