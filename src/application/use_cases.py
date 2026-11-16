"""
Прецеденты использования (Use Cases) — прикладной слой (Application Layer).

Оркестрирует работу доменных сущностей, сервисов и портов репозиториев.
Слой Application не содержит бизнес-правил (они в Domain), а управляет
потоком выполнения сценариев предметной области.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional, Tuple

from src.domain.entities import Criterion, Evaluation, Rubric, Student
from src.domain.factory import EvaluationFactory, RubricBuilder
from src.domain.repositories import (
    ICriterionRepository,
    IEvaluationRepository,
    IStudentRepository,
)
from src.domain.services import GradeCalculationService
from src.domain.value_objects import (
    CriterionId,
    DomainError,
    EvaluationId,
    FinalGrade,
    Score,
    StudentId,
    Weight,
)


# ---------------------------------------------------------------------------
# Прецеденты для сущности Студент
# ---------------------------------------------------------------------------

class AddStudentUseCase:
    """Добавляет нового студента в систему."""

    def __init__(self, student_repo: IStudentRepository) -> None:
        self._repo = student_repo

    def execute(self, full_name: str, group: str) -> Student:
        student = Student(
            id=StudentId(str(uuid.uuid4())),
            full_name=full_name.strip(),
            group=group.strip(),
        )
        self._repo.save(student)
        return student


class UpdateStudentUseCase:
    """Обновляет данные существующего студента."""

    def __init__(self, student_repo: IStudentRepository) -> None:
        self._repo = student_repo

    def execute(
        self,
        student_id: str,
        full_name: Optional[str] = None,
        group: Optional[str] = None,
    ) -> Student:
        sid = StudentId(student_id)
        student = self._repo.find_by_id(sid)
        if student is None:
            raise DomainError(f"Студент с id={student_id} не найден")
        if full_name:
            student.rename(full_name)
        if group:
            student.change_group(group)
        self._repo.save(student)
        return student


class DeleteStudentUseCase:
    """Удаляет студента и все связанные с ним оценки."""

    def __init__(
        self,
        student_repo: IStudentRepository,
        eval_repo: IEvaluationRepository,
    ) -> None:
        self._student_repo = student_repo
        self._eval_repo = eval_repo

    def execute(self, student_id: str) -> None:
        sid = StudentId(student_id)
        student = self._student_repo.find_by_id(sid)
        if student is None:
            raise DomainError(f"Студент с id={student_id} не найден")
        # Каскадное удаление оценок студента
        for ev in self._eval_repo.find_by_student(sid):
            self._eval_repo.delete(ev.id)
        self._student_repo.delete(sid)


class ListStudentsUseCase:
    """Возвращает список всех зарегистрированных студентов."""

    def __init__(self, student_repo: IStudentRepository) -> None:
        self._repo = student_repo

    def execute(self) -> List[Student]:
        return self._repo.find_all()


# ---------------------------------------------------------------------------
# Прецеденты для критериев и рубрикатора
# ---------------------------------------------------------------------------

class AddCriterionUseCase:
    """Добавляет критерий оценивания в рубрикатор."""

    def __init__(self, criterion_repo: ICriterionRepository) -> None:
        self._repo = criterion_repo

    def execute(
        self,
        name: str,
        max_score: float,
        weight: float,
        description: str = "",
    ) -> Criterion:
        clean_name = name.strip()
        # Проверка на дублирование названия среди уже сохранённых
        for c in self._repo.find_all():
            if c.name.lower() == clean_name.lower():
                raise DomainError(f"Критерий с названием «{clean_name}» уже существует")

        criterion = Criterion(
            id=CriterionId(str(uuid.uuid4())),
            name=clean_name,
            max_score=max_score,
            weight=Weight(weight),
            description=description.strip(),
        )
        self._repo.save(criterion)
        return criterion


class UpdateCriterionUseCase:
    """Обновляет параметры критерия в рубрикаторе."""

    def __init__(self, criterion_repo: ICriterionRepository) -> None:
        self._repo = criterion_repo

    def execute(
        self,
        criterion_id: str,
        name: Optional[str] = None,
        max_score: Optional[float] = None,
        weight: Optional[float] = None,
        description: Optional[str] = None,
    ) -> Criterion:
        cid = CriterionId(criterion_id)
        criterion = self._repo.find_by_id(cid)
        if criterion is None:
            raise DomainError(f"Критерий с id={criterion_id} не найден")

        # Если меняется имя — проверяем уникальность
        if name is not None and name.strip():
            clean_name = name.strip()
            for c in self._repo.find_all():
                if c.id != cid and c.name.lower() == clean_name.lower():
                    raise DomainError(f"Критерий с названием «{clean_name}» уже существует")

        updated = criterion.update(
            name=name,
            max_score=max_score,
            weight=Weight(weight) if weight is not None else None,
            description=description,
        )
        self._repo.save(updated)
        return updated


class DeleteCriterionUseCase:
    """Удаляет критерий и все выставленные по нему оценки."""

    def __init__(
        self,
        criterion_repo: ICriterionRepository,
        eval_repo: IEvaluationRepository,
    ) -> None:
        self._criterion_repo = criterion_repo
        self._eval_repo = eval_repo

    def execute(self, criterion_id: str) -> None:
        cid = CriterionId(criterion_id)
        criterion = self._criterion_repo.find_by_id(cid)
        if criterion is None:
            raise DomainError(f"Критерий с id={criterion_id} не найден")
        # Удаляем связанные оценки
        for ev in self._eval_repo.find_all():
            if ev.criterion_id == cid:
                self._eval_repo.delete(ev.id)
        self._criterion_repo.delete(cid)


class ListCriteriaUseCase:
    """Возвращает список всех критериев рубрикатора."""

    def __init__(self, criterion_repo: ICriterionRepository) -> None:
        self._repo = criterion_repo

    def execute(self) -> List[Criterion]:
        return self._repo.find_all()


class BuildRubricUseCase:
    """Собирает рубрикатор из сохранённых критериев или с помощью RubricBuilder."""

    def __init__(self, criterion_repo: ICriterionRepository) -> None:
        self._criterion_repo = criterion_repo

    def execute(self) -> Rubric:
        criteria = self._criterion_repo.find_all()
        return Rubric(criteria)


# ---------------------------------------------------------------------------
# Прецеденты для оценок
# ---------------------------------------------------------------------------

class GradeStudentUseCase:
    """
    Выставляет студенту оценку по конкретному критерию.
    Использует EvaluationFactory для централизованной охраны инвариантов.
    """

    def __init__(
        self,
        eval_repo: IEvaluationRepository,
        student_repo: IStudentRepository,
        criterion_repo: ICriterionRepository,
    ) -> None:
        self._eval_repo = eval_repo
        self._student_repo = student_repo
        self._criterion_repo = criterion_repo

    def execute(
        self,
        student_id: str,
        criterion_id: str,
        score_value: float,
        comment: str = "",
        eval_date: Optional[date] = None,
    ) -> Evaluation:
        sid = StudentId(student_id)
        cid = CriterionId(criterion_id)

        # Проверка существования студента
        if self._student_repo.find_by_id(sid) is None:
            raise DomainError(f"Студент с id={student_id} не найден")

        criteria = self._criterion_repo.find_all()
        existing = self._eval_repo.find_by_student(sid)

        # Создание через GoF-фабрику с полной валидацией инвариантов
        evaluation = EvaluationFactory.create(
            student_id=sid,
            criterion_id=cid,
            score_value=score_value,
            criteria=criteria,
            existing_evaluations=existing,
            comment=comment,
            eval_date=eval_date,
        )
        self._eval_repo.save(evaluation)
        return evaluation


class UpdateEvaluationUseCase:
    """Обновляет существующую оценку (балл и/или комментарий)."""

    def __init__(
        self,
        eval_repo: IEvaluationRepository,
        criterion_repo: ICriterionRepository,
    ) -> None:
        self._eval_repo = eval_repo
        self._criterion_repo = criterion_repo

    def execute(
        self,
        evaluation_id: str,
        new_score: Optional[float] = None,
        new_comment: Optional[str] = None,
    ) -> Evaluation:
        eid = EvaluationId(evaluation_id)
        evaluation = self._eval_repo.find_by_id(eid)
        if evaluation is None:
            raise DomainError(f"Оценка с id={evaluation_id} не найдена")

        if new_score is not None:
            criterion = self._criterion_repo.find_by_id(evaluation.criterion_id)
            if criterion is None:
                raise DomainError("Критерий для данной оценки не найден в рубрикаторе")
            EvaluationFactory.update_score(evaluation, new_score, criterion)

        if new_comment is not None:
            evaluation.update_comment(new_comment)

        self._eval_repo.save(evaluation)
        return evaluation


class DeleteEvaluationUseCase:
    """Удаляет (отменяет) оценку."""

    def __init__(self, eval_repo: IEvaluationRepository) -> None:
        self._eval_repo = eval_repo

    def execute(self, evaluation_id: str) -> None:
        eid = EvaluationId(evaluation_id)
        if self._eval_repo.find_by_id(eid) is None:
            raise DomainError(f"Оценка с id={evaluation_id} не найдена")
        self._eval_repo.delete(eid)


class ListEvaluationsUseCase:
    """Возвращает все оценки или оценки конкретного студента."""

    def __init__(self, eval_repo: IEvaluationRepository) -> None:
        self._eval_repo = eval_repo

    def execute(self, student_id: Optional[str] = None) -> List[Evaluation]:
        if student_id:
            return self._eval_repo.find_by_student(StudentId(student_id))
        return self._eval_repo.find_all()


# ---------------------------------------------------------------------------
# Прецеденты расчёта итогов
# ---------------------------------------------------------------------------

class GetFinalResultUseCase:
    """
    Рассчитывает итоговый балл студента (FinalGrade) динамически
    через Domain Service (GradeCalculationService).
    """

    def __init__(
        self,
        student_repo: IStudentRepository,
        eval_repo: IEvaluationRepository,
        criterion_repo: ICriterionRepository,
        grading_service: GradeCalculationService,
    ) -> None:
        self._student_repo = student_repo
        self._eval_repo = eval_repo
        self._criterion_repo = criterion_repo
        self._grading_service = grading_service

    def execute(self, student_id: str) -> FinalGrade:
        sid = StudentId(student_id)
        if self._student_repo.find_by_id(sid) is None:
            raise DomainError(f"Студент с id={student_id} не найден")

        evaluations = self._eval_repo.find_by_student(sid)
        criteria = self._criterion_repo.find_all()

        return self._grading_service.calculate_result(sid, evaluations, criteria)


class GetAllResultsUseCase:
    """Рассчитывает итоговые результаты для всех студентов с оценками."""

    def __init__(
        self,
        student_repo: IStudentRepository,
        eval_repo: IEvaluationRepository,
        criterion_repo: ICriterionRepository,
        grading_service: GradeCalculationService,
    ) -> None:
        self._student_repo = student_repo
        self._eval_repo = eval_repo
        self._criterion_repo = criterion_repo
        self._grading_service = grading_service

    def execute(self) -> List[Tuple[Student, FinalGrade]]:
        students = self._student_repo.find_all()
        criteria = self._criterion_repo.find_all()
        results: List[Tuple[Student, FinalGrade]] = []

        for student in students:
            evaluations = self._eval_repo.find_by_student(student.id)
            if not evaluations:
                continue
            try:
                res = self._grading_service.calculate_result(
                    student.id, evaluations, criteria
                )
                results.append((student, res))
            except DomainError:
                pass

        return results
