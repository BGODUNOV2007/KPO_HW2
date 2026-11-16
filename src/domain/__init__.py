"""
Доменный слой (Domain Layer) системы «ПОС».
Содержит богатую модель предметной области:
- Value Objects (Score, Weight, Criterion, FinalGrade, StudentId, CriterionId, EvaluationId)
- Entities & Aggregates (Student, Evaluation, Rubric)
- Domain Services (GradeCalculationService)
- Domain Factory & Builder (EvaluationFactory, RubricBuilder)
- Strategy & Decorator patterns
- Repository Ports (IStudentRepository, ICriterionRepository, IRubricRepository, IEvaluationRepository)
"""
from .value_objects import (
    Criterion,
    CriterionId,
    DomainError,
    EvaluationId,
    FinalGrade,
    FinalResult,
    Score,
    StudentId,
    Weight,
)
from .entities import Evaluation, Rubric, Student
from .factory import EvaluationFactory, RubricBuilder
from .repositories import (
    ICriterionRepository,
    IEvaluationRepository,
    IRubricRepository,
    IStudentRepository,
)
from .services import (
    BonusCapGradeDecorator,
    GradeCalculationService,
    GradingService,
    IGradeCalculationStrategy,
    NormalizedGradeStrategy,
    RoundedScoreDecorator,
    RoundingGradeDecorator,
    ScoringStrategy,
    SimpleAverageStrategy,
    WeightedAverageStrategy,
    WeightedGradeStrategy,
)

__all__ = [
    # Value Objects & Errors
    "DomainError",
    "StudentId",
    "CriterionId",
    "EvaluationId",
    "Score",
    "Weight",
    "Criterion",
    "FinalGrade",
    "FinalResult",
    # Entities & Aggregates
    "Student",
    "Evaluation",
    "Rubric",
    # Factory & Builder
    "EvaluationFactory",
    "RubricBuilder",
    # Ports
    "IStudentRepository",
    "ICriterionRepository",
    "IRubricRepository",
    "IEvaluationRepository",
    # Domain Service & Strategies
    "GradeCalculationService",
    "GradingService",
    "IGradeCalculationStrategy",
    "ScoringStrategy",
    "WeightedGradeStrategy",
    "WeightedAverageStrategy",
    "NormalizedGradeStrategy",
    "SimpleAverageStrategy",
    "RoundingGradeDecorator",
    "RoundedScoreDecorator",
    "BonusCapGradeDecorator",
]
