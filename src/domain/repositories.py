"""
Порты репозиториев (Outbound Ports) — доменный слой (Ports and Adapters).

Доменный слой определяет абстрактные интерфейсы хранения данных через abc.ABC.
Конкретные адаптеры хранилищ (InMemory, JSON-файлы, БД) реализуются
исключительно во внешнем инфраструктурном слое (Infrastructure).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from .entities import Criterion, Evaluation, Rubric, Student
from .value_objects import CriterionId, EvaluationId, StudentId


class IStudentRepository(ABC):
    """Порт: хранилище сущностей Студент."""

    @abstractmethod
    def save(self, student: Student) -> None:
        """Сохраняет или обновляет студента."""
        ...

    @abstractmethod
    def find_by_id(self, student_id: StudentId) -> Optional[Student]:
        """Возвращает студента по его идентификатору или None."""
        ...

    @abstractmethod
    def find_all(self) -> List[Student]:
        """Возвращает список всех студентов."""
        ...

    @abstractmethod
    def delete(self, student_id: StudentId) -> None:
        """Удаляет студента по его идентификатору."""
        ...


class ICriterionRepository(ABC):
    """Порт: хранилище критериев рубрикатора."""

    @abstractmethod
    def save(self, criterion: Criterion) -> None:
        """Сохраняет или обновляет критерий."""
        ...

    @abstractmethod
    def find_by_id(self, criterion_id: CriterionId) -> Optional[Criterion]:
        """Возвращает критерий по его идентификатору или None."""
        ...

    @abstractmethod
    def find_all(self) -> List[Criterion]:
        """Возвращает все критерии."""
        ...

    @abstractmethod
    def delete(self, criterion_id: CriterionId) -> None:
        """Удаляет критерий по его идентификатору."""
        ...


class IRubricRepository(ABC):
    """Порт: хранилище агрегата Рубрикатор."""

    @abstractmethod
    def get_rubric(self) -> Rubric:
        """Возвращает текущий агрегат Rubric."""
        ...

    @abstractmethod
    def save_rubric(self, rubric: Rubric) -> None:
        """Сохраняет состояние рубрикатора."""
        ...


class IEvaluationRepository(ABC):
    """Порт: хранилище сущностей Оценка."""

    @abstractmethod
    def save(self, evaluation: Evaluation) -> None:
        """Сохраняет или обновляет оценку."""
        ...

    @abstractmethod
    def find_by_id(self, evaluation_id: EvaluationId) -> Optional[Evaluation]:
        """Возвращает оценку по идентификатору или None."""
        ...

    @abstractmethod
    def find_by_student(self, student_id: StudentId) -> List[Evaluation]:
        """Возвращает все оценки конкретного студента."""
        ...

    @abstractmethod
    def find_all(self) -> List[Evaluation]:
        """Возвращает все оценки."""
        ...

    @abstractmethod
    def delete(self, evaluation_id: EvaluationId) -> None:
        """Удаляет оценку по идентификатору."""
        ...
