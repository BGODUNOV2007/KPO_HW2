"""
Объекты-значения (Value Objects) доменного слоя.

В соответствии с принципами DDD:
- Все Value Objects неизменяемы (@dataclass(frozen=True)).
- Не имеют отдельной идентичности (сравниваются по значению всех полей).
- Несут в себе доменные инварианты, проверяемые в __post_init__.
- Не допускают невалидного состояния в домене.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


class DomainError(Exception):
    """Базовое исключение для нарушений доменных инвариантов."""
    pass


# ---------------------------------------------------------------------------
# Идентификаторы (Value Objects — обёртки над типизированными строками UUID)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StudentId:
    """Идентификатор студента."""
    value: str

    def __post_init__(self) -> None:
        if not str(self.value).strip():
            raise DomainError("StudentId не может быть пустым")

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class CriterionId:
    """Идентификатор критерия."""
    value: str

    def __post_init__(self) -> None:
        if not str(self.value).strip():
            raise DomainError("CriterionId не может быть пустым")

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class EvaluationId:
    """Идентификатор оценки."""
    value: str

    def __post_init__(self) -> None:
        if not str(self.value).strip():
            raise DomainError("EvaluationId не может быть пустым")

    def __str__(self) -> str:
        return str(self.value)


# ---------------------------------------------------------------------------
# Оценка (Score) — Value Object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Score:
    """
    Оценка студента по критерию — Value Object.

    Инвариант:
    - значение не может быть отрицательным (score >= 0) и не может быть NaN/Inf.
    Дополнительная контекстная валидация:
    - validate_against_max(max_score): проверка score <= max_score.
    """
    value: float

    def __post_init__(self) -> None:
        if math.isnan(self.value) or math.isinf(self.value):
            raise DomainError(f"Оценка не может быть NaN или бесконечностью: {self.value}")
        if self.value < 0:
            raise DomainError(f"Оценка не может быть отрицательной: {self.value}")

    def validate_against_max(self, max_score: float) -> None:
        """Проверяет, что оценка не превышает максимально допустимый балл критерия."""
        if self.value > max_score:
            raise DomainError(
                f"Оценка {self.value} превышает максимум {max_score}"
            )

    def __str__(self) -> str:
        return str(self.value)


# ---------------------------------------------------------------------------
# Вес критерия (Weight) — Value Object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Weight:
    """
    Вес критерия при расчёте итоговой оценки — Value Object.

    Инвариант:
    - значение строго в диапазоне (0; 1].
    """
    value: float

    def __post_init__(self) -> None:
        if math.isnan(self.value) or math.isinf(self.value) or not (0 < self.value <= 1):
            raise DomainError(
                f"Вес критерия должен быть в диапазоне (0; 1]: {self.value}"
            )

    def __str__(self) -> str:
        return str(self.value)


# ---------------------------------------------------------------------------
# Критерий (Criterion) — Value Object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Criterion:
    """
    Критерий оценивания — Value Object.
    Определяет параметр оценивания: уникальный id, название, максимум и вес.

    Инварианты:
    - название не может быть пустым;
    - максимальный балл max_score > 0;
    - вес weight является валидным Value Object Weight (0 < weight <= 1).

    Так как объект неизменяем (frozen=True), метод update() возвращает
    новый экземпляр Criterion.
    """
    id: CriterionId
    name: str
    max_score: float
    weight: Weight
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DomainError("Название критерия не может быть пустым")
        if math.isnan(self.max_score) or math.isinf(self.max_score) or self.max_score <= 0:
            raise DomainError(
                f"Максимальный балл должен быть положительным: {self.max_score}"
            )

    def update(
        self,
        name: Optional[str] = None,
        max_score: Optional[float] = None,
        weight: Optional[Weight] = None,
        description: Optional[str] = None,
    ) -> "Criterion":
        """
        Возвращает новый объект Criterion с обновлёнными полями
        (функциональное обновление Value Object).
        """
        return Criterion(
            id=self.id,
            name=name.strip() if name is not None else self.name,
            max_score=max_score if max_score is not None else self.max_score,
            weight=weight if weight is not None else self.weight,
            description=description if description is not None else self.description,
        )

    def __str__(self) -> str:
        return f"{self.name} [0..{self.max_score}] (вес {self.weight.value})"


# ---------------------------------------------------------------------------
# Итоговый результат (FinalGrade / TotalScore) — Value Object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FinalGrade:
    """
    Итоговый результат оценивания студента (FinalGrade / TotalScore) — Value Object.
    Всегда вычисляется динамически в Domain Service (GradeCalculationService).
    Никогда не задаётся как произвольное статическое число.

    Содержит:
    - student_id: идентификатор студента;
    - total_score: набранный итоговый балл;
    - max_possible: максимально возможный итоговый балл;
    - percentage: процент выполнения (0..100%);
    - breakdown: расшифровка баллов по критериям.
    """
    student_id: StudentId
    total_score: float
    max_possible: float
    percentage: float
    breakdown: dict = field(default_factory=dict)

    def letter_grade(self) -> str:
        """Возвращает буквенную оценку по шкале ECTS/HSE."""
        p = self.percentage
        if p >= 90:
            return "A (Отлично)"
        elif p >= 80:
            return "B (Очень хорошо)"
        elif p >= 70:
            return "C (Хорошо)"
        elif p >= 60:
            return "D (Удовлетворительно)"
        elif p >= 50:
            return "E (Посредственно)"
        else:
            return "F (Неудовлетворительно)"

    def hse_10_grade(self) -> int:
        """Возвращает округлённую оценку по 10-балльной шкале НИУ ВШЭ."""
        if self.max_possible <= 0:
            return 0
        norm = (self.total_score / self.max_possible) * 10.0
        return max(0, min(10, round(norm)))

    def __str__(self) -> str:
        return (
            f"Итог: {self.total_score:.2f}/{self.max_possible:.2f} "
            f"({self.percentage:.1f}%, 10-балльная: {self.hse_10_grade()}) — {self.letter_grade()}"
        )


# Алиас для обратной совместимости
FinalResult = FinalGrade
