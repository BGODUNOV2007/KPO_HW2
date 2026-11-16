"""
Фасад приложения (PosApplicationFacade) — паттерн «Фасад» (Facade — GoF Структурный).

Служит единой точкой входа в слой Application для внешних интерфейсов
(CLI, демо-сценарии, веб-контроллеры).
Скрывает сложность оркестрации множества отдельных прецедентов использования
(Use Cases) за простым и понятным интерфейсом.
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional, Tuple

from src.domain.entities import Criterion, Evaluation, Rubric, Student
from src.domain.value_objects import FinalGrade
from .use_cases import (
    AddCriterionUseCase,
    AddStudentUseCase,
    BuildRubricUseCase,
    DeleteCriterionUseCase,
    DeleteEvaluationUseCase,
    DeleteStudentUseCase,
    GetAllResultsUseCase,
    GetFinalResultUseCase,
    GradeStudentUseCase,
    ListCriteriaUseCase,
    ListEvaluationsUseCase,
    ListStudentsUseCase,
    UpdateCriterionUseCase,
    UpdateEvaluationUseCase,
    UpdateStudentUseCase,
)


class PosApplicationFacade:
    """
    Фасад приложения «ПОС» — паттерн «Фасад» (GoF Structural).

    Предоставляет унифицированный интерфейс для взаимодействия с системой:
    консольный UI вызывает только методы фасада и не зависит от внутреннего
    устройства прикладного и доменного слоёв.
    """

    def __init__(
        self,
        add_student: AddStudentUseCase,
        update_student: UpdateStudentUseCase,
        delete_student: DeleteStudentUseCase,
        list_students: ListStudentsUseCase,
        add_criterion: AddCriterionUseCase,
        update_criterion: UpdateCriterionUseCase,
        delete_criterion: DeleteCriterionUseCase,
        list_criteria: ListCriteriaUseCase,
        grade_student: GradeStudentUseCase,
        update_evaluation: UpdateEvaluationUseCase,
        delete_evaluation: DeleteEvaluationUseCase,
        list_evaluations: ListEvaluationsUseCase,
        get_result: GetFinalResultUseCase,
        get_all_results: GetAllResultsUseCase,
        build_rubric: Optional[BuildRubricUseCase] = None,
    ) -> None:
        self._add_student = add_student
        self._update_student = update_student
        self._delete_student = delete_student
        self._list_students = list_students

        self._add_criterion = add_criterion
        self._update_criterion = update_criterion
        self._delete_criterion = delete_criterion
        self._list_criteria = list_criteria
        self._build_rubric = build_rubric

        self._grade_student = grade_student
        self._update_evaluation = update_evaluation
        self._delete_evaluation = delete_evaluation
        self._list_evaluations = list_evaluations

        self._get_result = get_result
        self._get_all_results = get_all_results

    # ------------------------------------------------------------------
    # Студенты
    # ------------------------------------------------------------------

    def add_student(self, full_name: str, group: str) -> Student:
        """Добавляет нового студента."""
        return self._add_student.execute(full_name, group)

    def update_student(
        self,
        student_id: str,
        full_name: Optional[str] = None,
        group: Optional[str] = None,
    ) -> Student:
        """Обновляет ФИО или группу студента."""
        return self._update_student.execute(student_id, full_name, group)

    def delete_student(self, student_id: str) -> None:
        """Удаляет студента и все его оценки."""
        self._delete_student.execute(student_id)

    def list_students(self) -> List[Student]:
        """Возвращает список всех зарегистрированных студентов."""
        return self._list_students.execute()

    # ------------------------------------------------------------------
    # Критерии и Рубрикатор
    # ------------------------------------------------------------------

    def add_criterion(
        self,
        name: str,
        max_score: float,
        weight: float,
        description: str = "",
    ) -> Criterion:
        """Добавляет новый критерий в рубрикатор."""
        return self._add_criterion.execute(name, max_score, weight, description)

    def update_criterion(
        self,
        criterion_id: str,
        name: Optional[str] = None,
        max_score: Optional[float] = None,
        weight: Optional[float] = None,
        description: Optional[str] = None,
    ) -> Criterion:
        """Обновляет параметры критерия."""
        return self._update_criterion.execute(
            criterion_id, name, max_score, weight, description
        )

    def delete_criterion(self, criterion_id: str) -> None:
        """Удаляет критерий и все связанные с ним оценки."""
        self._delete_criterion.execute(criterion_id)

    def list_criteria(self) -> List[Criterion]:
        """Возвращает список всех критериев рубрикатора."""
        return self._list_criteria.execute()

    def get_rubric(self) -> Rubric:
        """Возвращает агрегат Rubric, собранный из текущих критериев."""
        criteria = self.list_criteria()
        return Rubric(criteria)

    def save_rubric(self, rubric: Rubric) -> None:
        """Сохраняет все критерии из переданного агрегата Rubric."""
        existing = {c.name.lower(): c for c in self.list_criteria()}
        for c in rubric.criteria:
            if c.name.lower() in existing:
                self.update_criterion(existing[c.name.lower()].id.value, c.name, c.max_score, c.weight.value, c.description)
            else:
                self._add_criterion.execute(c.name, c.max_score, c.weight.value, c.description)

    # ------------------------------------------------------------------
    # Оценки
    # ------------------------------------------------------------------

    def grade_student(
        self,
        student_id: str,
        criterion_id: str,
        score: float,
        comment: str = "",
        eval_date: Optional[date] = None,
    ) -> Evaluation:
        """Выставляет оценку студенту по критерию через EvaluationFactory."""
        return self._grade_student.execute(
            student_id, criterion_id, score, comment, eval_date
        )

    def update_evaluation(
        self,
        evaluation_id: str,
        new_score: Optional[float] = None,
        new_comment: Optional[str] = None,
    ) -> Evaluation:
        """Обновляет балл или комментарий существующей оценки."""
        return self._update_evaluation.execute(evaluation_id, new_score, new_comment)

    def delete_evaluation(self, evaluation_id: str) -> None:
        """Отменяет (удаляет) оценку."""
        self._delete_evaluation.execute(evaluation_id)

    def list_evaluations(self, student_id: Optional[str] = None) -> List[Evaluation]:
        """Возвращает список оценок (всех или конкретного студента)."""
        return self._list_evaluations.execute(student_id)

    # ------------------------------------------------------------------
    # Итоговый результат (FinalGrade)
    # ------------------------------------------------------------------

    def get_final_result(self, student_id: str) -> FinalGrade:
        """Вычисляет и возвращает итоговый балл студента."""
        return self._get_result.execute(student_id)

    def get_final_grade(self, student_id: str) -> FinalGrade:
        """Синоним get_final_result."""
        return self.get_final_result(student_id)

    def get_all_results(self) -> List[Tuple[Student, FinalGrade]]:
        """Вычисляет итоговые баллы всех студентов."""
        return self._get_all_results.execute()

    def get_all_grades(self) -> List[Tuple[Student, FinalGrade]]:
        """Синоним get_all_results."""
        return self.get_all_results()


# Алиасы для гибкости именования
ApplicationFacade = PosApplicationFacade
PosFacade = PosApplicationFacade
