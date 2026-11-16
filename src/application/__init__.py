"""
Прикладной слой (Application Layer) системы «ПОС».
Содержит прецеденты использования (Use Cases) и фасад (PosApplicationFacade).
"""
from .facade import ApplicationFacade, PosApplicationFacade, PosFacade
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

__all__ = [
    "PosApplicationFacade",
    "ApplicationFacade",
    "PosFacade",
    "AddStudentUseCase",
    "UpdateStudentUseCase",
    "DeleteStudentUseCase",
    "ListStudentsUseCase",
    "AddCriterionUseCase",
    "UpdateCriterionUseCase",
    "DeleteCriterionUseCase",
    "ListCriteriaUseCase",
    "BuildRubricUseCase",
    "GradeStudentUseCase",
    "UpdateEvaluationUseCase",
    "DeleteEvaluationUseCase",
    "ListEvaluationsUseCase",
    "GetFinalResultUseCase",
    "GetAllResultsUseCase",
]
