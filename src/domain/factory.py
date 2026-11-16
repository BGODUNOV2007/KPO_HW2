"""
Порождающие паттерны GoF (Creational Patterns):
1. Фабрика (EvaluationFactory — GoF Factory Method / Factory).
2. Строитель (RubricBuilder — GoF Builder).

EvaluationFactory:
- Единая точка создания Evaluation, гарантирующая охрану доменных инвариантов:
  * критерий обязательно существует в рубрикаторе;
  * балл score попадает в диапазон [0, max_score];
  * отсутствует дублирующая оценка студента по тому же критерию.

RubricBuilder:
- Пошаговая сборка агрегата Rubric с валидацией целостности:
  * проверка уникальности названий критериев;
  * валидация весов и максимумов каждого критерия;
  * проверка суммарного веса на этапе build().
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional, Union

from .entities import Criterion, Evaluation, Rubric
from .value_objects import (
    CriterionId,
    DomainError,
    EvaluationId,
    Score,
    StudentId,
    Weight,
)


# ---------------------------------------------------------------------------
# Паттерн «Фабрика» (Factory — GoF Порождающий)
# ---------------------------------------------------------------------------

class EvaluationFactory:
    """
    Фабрика создания оценок.
    Паттерн «Фабрика» (GoF Creational).

    Гарантирует, что ни один объект Evaluation не будет создан
    с нарушением бизнес-инвариантов предметной области.
    """

    @staticmethod
    def create(
        student_id: StudentId,
        criterion_id: CriterionId,
        score_value: float,
        criteria: Union[List[Criterion], Rubric],
        existing_evaluations: List[Evaluation],
        comment: str = "",
        eval_date: Optional[date] = None,
    ) -> Evaluation:
        """
        Создаёт новый объект Evaluation с проверкой всех инвариантов.

        :param student_id: Идентификатор оцениваемого студента
        :param criterion_id: Идентификатор критерия
        :param score_value: Числовой балл
        :param criteria: Список критериев или агрегат Rubric
        :param existing_evaluations: Текущие оценки студента (для проверки на дубли)
        :param comment: Комментарий преподавателя
        :param eval_date: Дата оценивания (по умолчанию — сегодня)
        :return: Валидный объект Evaluation
        :raises DomainError: при нарушении любого инварианта
        """
        # Инвариант 1: критерий должен реально существовать в рубрикаторе
        criteria_list = criteria.criteria if isinstance(criteria, Rubric) else criteria
        criterion = next((c for c in criteria_list if c.id == criterion_id), None)
        if criterion is None:
            raise DomainError(
                f"Критерий с id={criterion_id} не найден в рубрикаторе"
            )

        # Инвариант 2: балл не выходит за пределы [0, criterion.max_score]
        score = Score(score_value)  # проверяет score >= 0
        score.validate_against_max(criterion.max_score)  # проверяет score <= max_score

        # Инвариант 3: оценка студенту по данному критерию ещё не выставлена
        duplicate = next(
            (
                ev
                for ev in existing_evaluations
                if ev.student_id == student_id and ev.criterion_id == criterion_id
            ),
            None,
        )
        if duplicate is not None:
            raise DomainError(
                f"Студент {student_id} уже имеет оценку по критерию {criterion_id}. "
                f"Используйте функцию изменения существующей оценки."
            )

        evaluation_id = EvaluationId(str(uuid.uuid4()))
        actual_date = eval_date or date.today()

        return Evaluation(
            id=evaluation_id,
            student_id=student_id,
            criterion_id=criterion_id,
            score=score,
            eval_date=actual_date,
            comment=comment,
        )

    @staticmethod
    def update_score(
        evaluation: Evaluation,
        new_score_value: float,
        criterion: Criterion,
    ) -> None:
        """
        Обновляет балл существующей оценки с делегированием инварианта сущности.

        :param evaluation: Обновляемая оценка
        :param new_score_value: Новое числовое значение
        :param criterion: Критерий для проверки диапазона
        :raises DomainError: при нарушении инварианта диапазона
        """
        new_score = Score(new_score_value)
        evaluation.update_score(new_score, criterion.max_score)


# ---------------------------------------------------------------------------
# Паттерн «Строитель» (Builder — GoF Порождающий)
# ---------------------------------------------------------------------------

class RubricBuilder:
    """
    Строитель рубрикатора курса.
    Паттерн «Строитель» (Builder — GoF Creational).

    Предоставляет удобный Fluent API для пошаговой сборки и валидации
    сложного агрегата Rubric.

    Решает боль домена: исключает создание некорректного или неполного
    рубрикатора с некорректным распределением весов критериев или дублями.

    Пример использования:
        rubric = (
            RubricBuilder()
            .add("ДЗ №1", max_score=10.0, weight=0.3)
            .add("ДЗ №2", max_score=10.0, weight=0.3)
            .add("Проект", max_score=10.0, weight=0.4)
            .build(strict_weights=True)
        )
    """

    def __init__(self) -> None:
        self._criteria: List[Criterion] = []
        self._names: set[str] = set()

    def add(
        self,
        name: str,
        max_score: float,
        weight: float,
        description: str = "",
        criterion_id: Optional[str] = None,
    ) -> "RubricBuilder":
        """
        Добавляет новый критерий в строящийся рубрикатор.

        :param name: Название критерия (не пустое, уникальное)
        :param max_score: Максимальный балл (> 0)
        :param weight: Вклад критерия в итог (0 < weight <= 1)
        :param description: Описание критерия
        :param criterion_id: Опциональный идентификатор
        :return: self для построения цепочки вызовов
        :raises DomainError: при нарушении инвариантов
        """
        clean_name = name.strip()
        if not clean_name:
            raise DomainError("Название критерия не может быть пустым")

        if clean_name.lower() in self._names:
            raise DomainError(
                f"Критерий с названием «{clean_name}» уже добавлен в рубрикатор"
            )

        cid = CriterionId(criterion_id or str(uuid.uuid4()))
        w = Weight(weight)

        criterion = Criterion(
            id=cid,
            name=clean_name,
            max_score=max_score,
            weight=w,
            description=description,
        )

        self._criteria.append(criterion)
        self._names.add(clean_name.lower())
        return self

    def build(self, strict_weights: bool = True) -> Rubric:
        """
        Собирает и возвращает агрегат Rubric.

        :param strict_weights: если True — проверяет, что сумма весов равна 1.0
        :return: Сконструированный агрегат Rubric
        :raises DomainError: если рубрикатор пуст или сумма весов != 1.0
        """
        if not self._criteria:
            raise DomainError("Рубрикатор не может быть пустым: добавьте хотя бы один критерий")

        total_weight = sum(c.weight.value for c in self._criteria)

        if strict_weights and abs(total_weight - 1.0) > 0.01:
            raise DomainError(
                f"Сумма весов критериев должна быть равна 1.0, текущая сумма: {total_weight:.4f}"
            )

        rubric = Rubric()
        for criterion in self._criteria:
            rubric.add_criterion(criterion)
        return rubric

    def reset(self) -> "RubricBuilder":
        """Сбрасывает накопленное состояние билдера."""
        self._criteria.clear()
        self._names.clear()
        return self

    @property
    def criteria_count(self) -> int:
        """Число добавленных критериев."""
        return len(self._criteria)

    @property
    def current_total_weight(self) -> float:
        """Текущая сумма весов."""
        return sum(c.weight.value for c in self._criteria)
