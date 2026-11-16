"""
DI-контейнер (Container) — корень компоновки (Composition Root).

В соответствии с архитектурой Ports & Adapters (Hexagonal):
- DI-контейнер собирает граф зависимостей на краю системы.
- Инфраструктурные зависимости (адаптеры) связываются с портами домена.
- Поддерживает два режима работы:
  * 'memory' — хранение в оперативной памяти (для быстрых изолированных тестов и demo);
  * 'json' — персистентное файловое хранилище (для стандартной работы).
"""
from __future__ import annotations

import os
from typing import Literal

from src.application.facade import ApplicationFacade, PosApplicationFacade
from src.application.use_cases import (
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
from src.domain.repositories import (
    ICriterionRepository,
    IEvaluationRepository,
    IStudentRepository,
)
from src.domain.services import (
    BonusCapGradeDecorator,
    GradeCalculationService,
    GradingService,
    RoundingGradeDecorator,
    WeightedGradeStrategy,
)
from src.infrastructure.export import (
    CsvExporter,
    CsvReportExporter,
    JsonExporter,
    JsonReportExporter,
)
from src.infrastructure.repositories import (
    InMemoryCriterionRepository,
    InMemoryEvaluationRepository,
    InMemoryStudentRepository,
    JsonFileCriterionRepository,
    JsonFileEvaluationRepository,
    JsonFileStudentRepository,
)

StorageMode = Literal["memory", "json"]


class Container:
    """
    DI-контейнер приложения — корень компоновки (Composition Root).
    Собирает и связывает все компоненты Clean Architecture / Ports and Adapters.
    """

    def __init__(
        self,
        storage_mode: StorageMode = "json",
        data_dir: str = "data",
    ) -> None:
        self._storage_mode = storage_mode
        self._data_dir = data_dir

        # 1. Адаптеры репозиториев (Infrastructure -> Domain Ports)
        self._student_repo: IStudentRepository = self._build_student_repo()
        self._criterion_repo: ICriterionRepository = self._build_criterion_repo()
        self._eval_repo: IEvaluationRepository = self._build_eval_repo()

        # 2. Доменный сервис и GoF-стратегия с декораторами
        # Базовая стратегия: взвешенное среднее по критериям рубрикатора
        base_strategy = WeightedGradeStrategy()
        # Декоратор 1: ограничение максимумом (BonusCap)
        capped_strategy = BonusCapGradeDecorator(base_strategy)
        # Декоратор 2: регламентное округление (Rounding Decorator по правилам ВШЭ)
        rounded_strategy = RoundingGradeDecorator(capped_strategy, decimals=2)

        self._grading_service = GradeCalculationService(strategy=rounded_strategy)

        # 3. Прецеденты использования (Application Use Cases)
        self._add_student = AddStudentUseCase(self._student_repo)
        self._update_student = UpdateStudentUseCase(self._student_repo)
        self._delete_student = DeleteStudentUseCase(self._student_repo, self._eval_repo)
        self._list_students = ListStudentsUseCase(self._student_repo)

        self._add_criterion = AddCriterionUseCase(self._criterion_repo)
        self._update_criterion = UpdateCriterionUseCase(self._criterion_repo)
        self._delete_criterion = DeleteCriterionUseCase(self._criterion_repo, self._eval_repo)
        self._list_criteria = ListCriteriaUseCase(self._criterion_repo)
        self._build_rubric = BuildRubricUseCase(self._criterion_repo)

        self._grade_student = GradeStudentUseCase(
            self._eval_repo, self._student_repo, self._criterion_repo
        )
        self._update_evaluation = UpdateEvaluationUseCase(self._eval_repo, self._criterion_repo)
        self._delete_evaluation = DeleteEvaluationUseCase(self._eval_repo)
        self._list_evaluations = ListEvaluationsUseCase(self._eval_repo)

        self._get_result = GetFinalResultUseCase(
            self._student_repo, self._eval_repo, self._criterion_repo, self._grading_service
        )
        self._get_all_results = GetAllResultsUseCase(
            self._student_repo, self._eval_repo, self._criterion_repo, self._grading_service
        )

        # 4. Фасад приложения (GoF Facade)
        self._facade = PosApplicationFacade(
            add_student=self._add_student,
            update_student=self._update_student,
            delete_student=self._delete_student,
            list_students=self._list_students,
            add_criterion=self._add_criterion,
            update_criterion=self._update_criterion,
            delete_criterion=self._delete_criterion,
            list_criteria=self._list_criteria,
            build_rubric=self._build_rubric,
            grade_student=self._grade_student,
            update_evaluation=self._update_evaluation,
            delete_evaluation=self._delete_evaluation,
            list_evaluations=self._list_evaluations,
            get_result=self._get_result,
            get_all_results=self._get_all_results,
        )

        # 5. Адаптеры экспортёров (GoF Template Method)
        self._csv_exporter = CsvReportExporter()
        self._json_exporter = JsonReportExporter()

    # ------------------------------------------------------------------
    # Фабричные методы создания адаптеров хранения
    # ------------------------------------------------------------------

    def _build_student_repo(self) -> IStudentRepository:
        if self._storage_mode == "memory":
            return InMemoryStudentRepository()
        path = os.path.join(self._data_dir, "students.json")
        return JsonFileStudentRepository(path)

    def _build_criterion_repo(self) -> ICriterionRepository:
        if self._storage_mode == "memory":
            return InMemoryCriterionRepository()
        path = os.path.join(self._data_dir, "criteria.json")
        return JsonFileCriterionRepository(path)

    def _build_eval_repo(self) -> IEvaluationRepository:
        if self._storage_mode == "memory":
            return InMemoryEvaluationRepository()
        path = os.path.join(self._data_dir, "evaluations.json")
        return JsonFileEvaluationRepository(path)

    # ------------------------------------------------------------------
    # Публичные геттеры
    # ------------------------------------------------------------------

    @property
    def facade(self) -> PosApplicationFacade:
        """Единая точка входа в систему (Application Facade)."""
        return self._facade

    @property
    def csv_exporter(self) -> CsvReportExporter:
        """Экспортёр отчётов в CSV."""
        return self._csv_exporter

    @property
    def json_exporter(self) -> JsonReportExporter:
        """Экспортёр отчётов в JSON."""
        return self._json_exporter

    @property
    def grading_service(self) -> GradeCalculationService:
        """Доменный сервис расчёта оценок."""
        return self._grading_service

    @property
    def student_repo(self) -> IStudentRepository:
        return self._student_repo

    @property
    def criterion_repo(self) -> ICriterionRepository:
        return self._criterion_repo

    @property
    def eval_repo(self) -> IEvaluationRepository:
        return self._eval_repo
