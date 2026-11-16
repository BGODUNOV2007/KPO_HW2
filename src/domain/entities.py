"""
Доменные сущности (Entities) и Агрегаты (Aggregates).

В соответствии с принципами DDD:
- Сущности обладают уникальным жизненным циклом и идентичностью (ID).
- Сравнение сущностей производится ТОЛЬКО по идентичности (__eq__ и __hash__ по ID).
- Состояние инкапсулировано через приватные атрибуты (_attribute) и защищено
  бизнес-методами с проверкой инвариантов.
- Никаких анемичных DTO: сущность сама управляет изменениями своего состояния.
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from .value_objects import (
    Criterion,
    CriterionId,
    DomainError,
    EvaluationId,
    Score,
    StudentId,
    Weight,
)


# ---------------------------------------------------------------------------
# Сущность «Студент» (Student)
# ---------------------------------------------------------------------------

class Student:
    """
    Сущность «Студент».
    Представляет собой обучающегося на курсе, чья работа оценивается.

    Идентифицируется уникальным StudentId.
    Инкапсулирует ФИО и группу, не допуская пустых значений.
    """

    def __init__(self, id: StudentId, full_name: str, group: str) -> None:
        if not full_name.strip():
            raise DomainError("ФИО студента не может быть пустым")
        if not group.strip():
            raise DomainError("Группа студента не может быть пустой")
        self._id = id
        self._full_name = full_name.strip()
        self._group = group.strip()

    # --- Свойства только для чтения ---

    @property
    def id(self) -> StudentId:
        return self._id

    @property
    def full_name(self) -> str:
        return self._full_name

    @property
    def group(self) -> str:
        return self._group

    # --- Бизнес-методы изменения состояния ---

    def rename(self, new_name: str) -> None:
        """Изменяет ФИО студента с валидацией инварианта."""
        if not new_name.strip():
            raise DomainError("Новое ФИО не может быть пустым")
        self._full_name = new_name.strip()

    def change_group(self, new_group: str) -> None:
        """Переводит студента в другую группу с валидацией инварианта."""
        if not new_group.strip():
            raise DomainError("Название группы не может быть пустым")
        self._group = new_group.strip()

    # --- Сравнение по идентичности (Identity equality) ---

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Student):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __str__(self) -> str:
        return f"{self._full_name} ({self._group})"

    def __repr__(self) -> str:
        return f"Student(id={self._id!r}, full_name={self._full_name!r}, group={self._group!r})"


# ---------------------------------------------------------------------------
# Сущность «Оценка» (Evaluation)
# ---------------------------------------------------------------------------

class Evaluation:
    """
    Сущность «Оценка».
    Фиксирует факт выставления студенту балла по конкретному критерию
    с датой и опциональным комментарием преподавателя.

    Идентифицируется уникальным EvaluationId.
    Инварианты балла охраняются через метод update_score() и EvaluationFactory.
    """

    def __init__(
        self,
        id: EvaluationId,
        student_id: StudentId,
        criterion_id: CriterionId,
        score: Score,
        eval_date: date,
        comment: str = "",
    ) -> None:
        self._id = id
        self._student_id = student_id
        self._criterion_id = criterion_id
        self._score = score
        self._eval_date = eval_date
        self._comment = comment.strip()

    # --- Свойства только для чтения ---

    @property
    def id(self) -> EvaluationId:
        return self._id

    @property
    def student_id(self) -> StudentId:
        return self._student_id

    @property
    def criterion_id(self) -> CriterionId:
        return self._criterion_id

    @property
    def score(self) -> Score:
        return self._score

    @property
    def eval_date(self) -> date:
        return self._eval_date

    @property
    def comment(self) -> str:
        return self._comment

    # --- Бизнес-методы изменения состояния ---

    def update_score(self, new_score: Score, max_score: float) -> None:
        """Обновляет выставленный балл с обязательной проверкой максимума критерия."""
        new_score.validate_against_max(max_score)
        self._score = new_score

    def update_comment(self, new_comment: str) -> None:
        """Обновляет комментарий преподавателя."""
        self._comment = new_comment.strip()

    # --- Сравнение по идентичности (Identity equality) ---

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Evaluation):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __str__(self) -> str:
        return (
            f"Оценка {self._score.value} за критерий {self._criterion_id} "
            f"(студент {self._student_id}, {self._eval_date})"
        )

    def __repr__(self) -> str:
        return (
            f"Evaluation(id={self._id!r}, student_id={self._student_id!r}, "
            f"criterion_id={self._criterion_id!r}, score={self._score!r})"
        )


# ---------------------------------------------------------------------------
# Агрегат «Рубрикатор» (Rubric — Aggregate Root)
# ---------------------------------------------------------------------------

class Rubric:
    """
    Корневой агрегат «Рубрикатор» (Aggregate Root).
    Управляет согласованным набором критериев курса, защищая целостность
    схемы оценивания и инварианты схемы.

    Инварианты агрегата:
    - критерии в рубрикаторе имеют уникальные ID и уникальные названия;
    - критерии не могут дублироваться;
    - агрегат предоставляет единую точку добавления, удаления и обновления критериев.
    """

    def __init__(self, criteria: Optional[List[Criterion]] = None) -> None:
        self._criteria: List[Criterion] = []
        if criteria:
            for c in criteria:
                self.add_criterion(c)

    @property
    def criteria(self) -> List[Criterion]:
        """Возвращает защищённую копию списка критериев."""
        return list(self._criteria)

    def add_criterion(self, criterion: Criterion) -> None:
        """Добавляет критерий в рубрикатор с контролем уникальности ID и имени."""
        if any(c.id == criterion.id for c in self._criteria):
            raise DomainError(f"Критерий с id={criterion.id} уже существует в рубрикаторе")
        if any(c.name.lower() == criterion.name.lower() for c in self._criteria):
            raise DomainError(f"Критерий с названием «{criterion.name}» уже есть в рубрикаторе")
        self._criteria.append(criterion)

    def update_criterion(self, updated_criterion: Criterion) -> None:
        """Обновляет критерий внутри рубрикатора."""
        idx = next((i for i, c in enumerate(self._criteria) if c.id == updated_criterion.id), None)
        if idx is None:
            raise DomainError(f"Критерий с id={updated_criterion.id} не найден в рубрикаторе")
        # Проверяем уникальность нового имени среди других критериев
        for i, c in enumerate(self._criteria):
            if i != idx and c.name.lower() == updated_criterion.name.lower():
                raise DomainError(f"Критерий с названием «{updated_criterion.name}» уже есть в рубрикаторе")
        self._criteria[idx] = updated_criterion

    def remove_criterion(self, criterion_id: CriterionId) -> None:
        """Удаляет критерий из рубрикатора."""
        before = len(self._criteria)
        self._criteria = [c for c in self._criteria if c.id != criterion_id]
        if len(self._criteria) == before:
            raise DomainError(f"Критерий {criterion_id} не найден в рубрикаторе")

    def find_criterion(self, criterion_id: CriterionId) -> Optional[Criterion]:
        """Возвращает критерий по его идентификатору или None."""
        return next((c for c in self._criteria if c.id == criterion_id), None)

    def find_by_name(self, name: str) -> Optional[Criterion]:
        """Возвращает критерий по его названию (без учёта регистра) или None."""
        clean = name.strip().lower()
        return next((c for c in self._criteria if c.name.lower() == clean), None)

    def total_weight(self) -> float:
        """Суммарный вес всех критериев рубрикатора."""
        return sum(c.weight.value for c in self._criteria)

    def validate_weights(self) -> None:
        """Проверяет, что суммарный вес критериев равен 1.0 (с учётом погрешности float)."""
        tot = self.total_weight()
        if abs(tot - 1.0) > 0.01:
            raise DomainError(f"Суммарный вес критериев должен быть равен 1.0 (текущий: {tot:.4f})")

    def __len__(self) -> int:
        return len(self._criteria)

    def __contains__(self, criterion_id: CriterionId) -> bool:
        return any(c.id == criterion_id for c in self._criteria)

    def __str__(self) -> str:
        return f"Рубрикатор ({len(self._criteria)} критериев, суммарный вес: {self.total_weight():.2f})"
