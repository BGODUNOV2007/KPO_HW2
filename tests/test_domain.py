"""
Тесты доменного слоя (Domain Layer).
Проверяют инварианты объектов-значений (Value Objects), сущностей (Entities),
агрегата Rubric, порождающих паттернов (EvaluationFactory, RubricBuilder),
стратегий и декораторов расчёта итоговой оценки.
"""
from datetime import date
import pytest

from src.domain.entities import Evaluation, Rubric, Student
from src.domain.factory import EvaluationFactory, RubricBuilder
from src.domain.services import (
    BonusCapGradeDecorator,
    GradeCalculationService,
    GradingService,
    NormalizedGradeStrategy,
    RoundedScoreDecorator,
    RoundingGradeDecorator,
    SimpleAverageStrategy,
    WeightedAverageStrategy,
    WeightedGradeStrategy,
)
from src.domain.value_objects import (
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


# ---------------------------------------------------------------------------
# Тесты Value Object: Score
# ---------------------------------------------------------------------------

class TestScore:
    """Тесты инвариантов объекта-значения Score."""

    def test_valid_score_created(self):
        score = Score(7.5)
        assert score.value == 7.5

    def test_zero_score_is_valid(self):
        score = Score(0.0)
        assert score.value == 0.0

    def test_negative_score_raises_domain_error(self):
        with pytest.raises(DomainError, match="отрицательной"):
            Score(-1.0)

    def test_large_negative_score_raises_domain_error(self):
        with pytest.raises(DomainError):
            Score(-100.5)

    def test_validate_against_max_ok(self):
        score = Score(8.0)
        score.validate_against_max(10.0)

    def test_validate_against_max_equal(self):
        score = Score(10.0)
        score.validate_against_max(10.0)

    def test_validate_against_max_exceeds(self):
        score = Score(11.0)
        with pytest.raises(DomainError, match="превышает максимум"):
            score.validate_against_max(10.0)

    def test_score_immutability(self):
        score = Score(5.0)
        with pytest.raises(Exception):
            score.value = 6.0  # type: ignore

    def test_nan_score_raises_domain_error(self):
        with pytest.raises(DomainError):
            Score(float("nan"))

    def test_inf_score_raises_domain_error(self):
        with pytest.raises(DomainError):
            Score(float("inf"))


# ---------------------------------------------------------------------------
# Тесты Value Object: Weight
# ---------------------------------------------------------------------------

class TestWeight:
    """Тесты инвариантов объекта-значения Weight."""

    def test_valid_weight_created(self):
        w = Weight(0.5)
        assert w.value == 0.5

    def test_weight_one_is_valid(self):
        w = Weight(1.0)
        assert w.value == 1.0

    def test_weight_zero_raises_domain_error(self):
        with pytest.raises(DomainError, match="диапазоне"):
            Weight(0.0)

    def test_negative_weight_raises_domain_error(self):
        with pytest.raises(DomainError):
            Weight(-0.1)

    def test_weight_exceeding_one_raises_domain_error(self):
        with pytest.raises(DomainError):
            Weight(1.001)

    def test_weight_immutability(self):
        w = Weight(0.3)
        with pytest.raises(Exception):
            w.value = 0.5  # type: ignore

    def test_nan_weight_raises_domain_error(self):
        with pytest.raises(DomainError):
            Weight(float("nan"))


# ---------------------------------------------------------------------------
# Тесты Value Object: Criterion
# ---------------------------------------------------------------------------

class TestCriterion:
    """Тесты объекта-значения Criterion."""

    def test_valid_criterion_created(self):
        c = Criterion(
            id=CriterionId("crit-1"),
            name="Оформление",
            max_score=10.0,
            weight=Weight(0.3),
        )
        assert c.name == "Оформление"
        assert c.max_score == 10.0
        assert c.weight.value == 0.3

    def test_empty_name_raises_domain_error(self):
        with pytest.raises(DomainError, match="пустым"):
            Criterion(
                id=CriterionId("crit-1"),
                name="",
                max_score=10.0,
                weight=Weight(0.3),
            )

    def test_zero_max_score_raises_domain_error(self):
        with pytest.raises(DomainError, match="положительным"):
            Criterion(
                id=CriterionId("crit-1"),
                name="Тест",
                max_score=0.0,
                weight=Weight(0.3),
            )

    def test_negative_max_score_raises_domain_error(self):
        with pytest.raises(DomainError):
            Criterion(
                id=CriterionId("crit-1"),
                name="Тест",
                max_score=-5.0,
                weight=Weight(0.3),
            )

    def test_nan_max_score_raises_domain_error(self):
        with pytest.raises(DomainError):
            Criterion(
                id=CriterionId("crit-1"),
                name="Тест",
                max_score=float("nan"),
                weight=Weight(0.3),
            )

    def test_criterion_immutability(self):
        c = Criterion(CriterionId("c1"), "Тест", 10.0, Weight(0.5))
        with pytest.raises(Exception):
            c.name = "Новое имя"  # type: ignore

    def test_criterion_update_returns_new_instance(self):
        c = Criterion(CriterionId("c1"), "Старое имя", 10.0, Weight(0.5))
        updated = c.update(name="Новое имя", max_score=15.0)
        assert updated.name == "Новое имя"
        assert updated.max_score == 15.0
        assert updated.weight == c.weight
        assert c.name == "Старое имя"  # исходный неизменен


# ---------------------------------------------------------------------------
# Тесты Entity: Student
# ---------------------------------------------------------------------------

class TestStudent:
    """Тесты сущности Student."""

    def test_valid_student_created(self):
        s = Student(id=StudentId("s1"), full_name="Иванов Иван", group="БПИ-21-1")
        assert s.full_name == "Иванов Иван"
        assert s.group == "БПИ-21-1"

    def test_empty_name_raises_domain_error(self):
        with pytest.raises(DomainError, match="пустым"):
            Student(id=StudentId("s1"), full_name="", group="БПИ-21-1")

    def test_empty_group_raises_domain_error(self):
        with pytest.raises(DomainError, match="пустой"):
            Student(id=StudentId("s1"), full_name="Иванов И.И.", group="")

    def test_rename_and_change_group(self):
        s = Student(id=StudentId("s1"), full_name="Иванов И.И.", group="Гр-1")
        s.rename("Петров П.П.")
        s.change_group("Гр-2")
        assert s.full_name == "Петров П.П."
        assert s.group == "Гр-2"

    def test_student_identity_equality(self):
        """Сущности равны тогда и только тогда, когда совпадают их ID."""
        s1 = Student(StudentId("id-same"), "Иванов", "Гр-1")
        s2 = Student(StudentId("id-same"), "Совершенно Другое Имя", "Гр-2")
        s3 = Student(StudentId("id-different"), "Иванов", "Гр-1")

        assert s1 == s2
        assert hash(s1) == hash(s2)
        assert s1 != s3


# ---------------------------------------------------------------------------
# Тесты Aggregate Root: Rubric
# ---------------------------------------------------------------------------

class TestRubricAggregate:
    """Тесты агрегата Rubric."""

    def test_rubric_add_and_find_criterion(self):
        rubric = Rubric()
        crit = Criterion(CriterionId("c1"), "Теория", 10.0, Weight(0.4))
        rubric.add_criterion(crit)

        assert len(rubric) == 1
        assert rubric.find_criterion(CriterionId("c1")) == crit
        assert rubric.find_by_name("теория") == crit

    def test_rubric_prevents_duplicate_id_and_name(self):
        rubric = Rubric()
        crit1 = Criterion(CriterionId("c1"), "Теория", 10.0, Weight(0.4))
        rubric.add_criterion(crit1)

        crit_dup_id = Criterion(CriterionId("c1"), "Практика", 10.0, Weight(0.4))
        with pytest.raises(DomainError, match="уже существует"):
            rubric.add_criterion(crit_dup_id)

        crit_dup_name = Criterion(CriterionId("c2"), "ТЕОРИЯ", 10.0, Weight(0.4))
        with pytest.raises(DomainError, match="уже есть в рубрикаторе"):
            rubric.add_criterion(crit_dup_name)

    def test_rubric_total_weight_and_validation(self):
        rubric = Rubric()
        rubric.add_criterion(Criterion(CriterionId("c1"), "К1", 10.0, Weight(0.6)))
        rubric.add_criterion(Criterion(CriterionId("c2"), "К2", 10.0, Weight(0.4)))

        assert rubric.total_weight() == pytest.approx(1.0)
        rubric.validate_weights()  # не выбрасывает исключение

    def test_rubric_validate_weights_fails_when_not_one(self):
        rubric = Rubric()
        rubric.add_criterion(Criterion(CriterionId("c1"), "К1", 10.0, Weight(0.5)))
        with pytest.raises(DomainError, match="должен быть равен 1.0"):
            rubric.validate_weights()


# ---------------------------------------------------------------------------
# Тесты GoF Builder: RubricBuilder
# ---------------------------------------------------------------------------

class TestRubricBuilder:
    """Тесты порождающего паттерна Builder для сборки рубрикатора."""

    def test_builder_builds_valid_rubric(self):
        builder = RubricBuilder()
        rubric = (
            builder
            .add("ДЗ №1", max_score=10.0, weight=0.3)
            .add("ДЗ №2", max_score=10.0, weight=0.3)
            .add("Проект", max_score=10.0, weight=0.4)
            .build(strict_weights=True)
        )
        assert len(rubric) == 3
        assert rubric.total_weight() == pytest.approx(1.0)

    def test_builder_strict_weights_fails_when_sum_invalid(self):
        builder = RubricBuilder()
        builder.add("Критерий 1", max_score=10.0, weight=0.5)
        with pytest.raises(DomainError, match="должна быть равна 1.0"):
            builder.build(strict_weights=True)

    def test_builder_prevents_duplicate_names(self):
        builder = RubricBuilder()
        builder.add("Код", max_score=10.0, weight=0.5)
        with pytest.raises(DomainError, match="уже добавлен"):
            builder.add("код", max_score=10.0, weight=0.5)

    def test_builder_empty_build_fails(self):
        builder = RubricBuilder()
        with pytest.raises(DomainError, match="не может быть пустым"):
            builder.build()


# ---------------------------------------------------------------------------
# Тесты GoF Factory: EvaluationFactory
# ---------------------------------------------------------------------------

class TestEvaluationFactory:
    """Тесты фабрики оценок."""

    @pytest.fixture
    def criterion(self):
        return Criterion(
            id=CriterionId("crit-1"),
            name="Код",
            max_score=10.0,
            weight=Weight(0.5),
        )

    @pytest.fixture
    def student_id(self):
        return StudentId("student-1")

    def test_create_valid_evaluation(self, criterion, student_id):
        ev = EvaluationFactory.create(
            student_id=student_id,
            criterion_id=criterion.id,
            score_value=8.0,
            criteria=[criterion],
            existing_evaluations=[],
        )
        assert ev.score.value == 8.0
        assert ev.student_id == student_id
        assert ev.criterion_id == criterion.id

    def test_create_with_zero_score(self, criterion, student_id):
        ev = EvaluationFactory.create(
            student_id=student_id,
            criterion_id=criterion.id,
            score_value=0.0,
            criteria=[criterion],
            existing_evaluations=[],
        )
        assert ev.score.value == 0.0

    def test_create_with_max_score(self, criterion, student_id):
        ev = EvaluationFactory.create(
            student_id=student_id,
            criterion_id=criterion.id,
            score_value=10.0,
            criteria=[criterion],
            existing_evaluations=[],
        )
        assert ev.score.value == 10.0

    def test_create_exceeding_max_raises_error(self, criterion, student_id):
        with pytest.raises(DomainError, match="превышает максимум"):
            EvaluationFactory.create(
                student_id=student_id,
                criterion_id=criterion.id,
                score_value=12.0,  # 12 из 10
                criteria=[criterion],
                existing_evaluations=[],
            )

    def test_create_negative_score_raises_error(self, criterion, student_id):
        with pytest.raises(DomainError, match="отрицательной"):
            EvaluationFactory.create(
                student_id=student_id,
                criterion_id=criterion.id,
                score_value=-1.0,
                criteria=[criterion],
                existing_evaluations=[],
            )

    def test_create_with_nonexistent_criterion_raises_error(self, student_id):
        with pytest.raises(DomainError, match="не найден"):
            EvaluationFactory.create(
                student_id=student_id,
                criterion_id=CriterionId("nonexistent"),
                score_value=5.0,
                criteria=[],
                existing_evaluations=[],
            )

    def test_create_duplicate_evaluation_raises_error(self, criterion, student_id):
        existing = EvaluationFactory.create(
            student_id=student_id,
            criterion_id=criterion.id,
            score_value=7.0,
            criteria=[criterion],
            existing_evaluations=[],
        )
        with pytest.raises(DomainError, match="уже имеет оценку"):
            EvaluationFactory.create(
                student_id=student_id,
                criterion_id=criterion.id,
                score_value=8.0,
                criteria=[criterion],
                existing_evaluations=[existing],
            )

    def test_update_score_via_factory(self, criterion, student_id):
        ev = EvaluationFactory.create(
            student_id=student_id,
            criterion_id=criterion.id,
            score_value=7.0,
            criteria=[criterion],
            existing_evaluations=[],
        )
        EvaluationFactory.update_score(ev, 9.5, criterion)
        assert ev.score.value == 9.5

        with pytest.raises(DomainError, match="превышает максимум"):
            EvaluationFactory.update_score(ev, 11.0, criterion)


# ---------------------------------------------------------------------------
# Тесты GradeCalculationService, стратегий и декораторов
# ---------------------------------------------------------------------------

class TestGradeCalculationService:
    """Тесты доменного сервиса расчёта итоговой оценки."""

    @pytest.fixture
    def criteria(self):
        return [
            Criterion(CriterionId("c1"), "Код", 10.0, Weight(0.6)),
            Criterion(CriterionId("c2"), "Дизайн", 10.0, Weight(0.4)),
        ]

    @pytest.fixture
    def student_id(self):
        return StudentId("s1")

    def _make_eval(self, sid, cid, score_val):
        return Evaluation(
            id=EvaluationId(f"e-{cid.value}"),
            student_id=sid,
            criterion_id=cid,
            score=Score(score_val),
            eval_date=date.today(),
        )

    def test_weighted_average_calculation(self, criteria, student_id):
        evals = [
            self._make_eval(student_id, CriterionId("c1"), 8.0),
            self._make_eval(student_id, CriterionId("c2"), 6.0),
        ]
        service = GradeCalculationService(WeightedGradeStrategy())
        res = service.calculate_result(student_id, evals, criteria)

        # (8 * 0.6 + 6 * 0.4) / 1.0 = 7.2
        assert res.total_score == pytest.approx(7.2, abs=0.01)
        assert res.percentage == pytest.approx(72.0, abs=0.1)
        assert res.hse_10_grade() == 7

    def test_normalized_strategy_calculation(self, criteria, student_id):
        evals = [
            self._make_eval(student_id, CriterionId("c1"), 10.0),
            self._make_eval(student_id, CriterionId("c2"), 5.0),
        ]
        service = GradeCalculationService(NormalizedGradeStrategy())
        res = service.calculate_result(student_id, evals, criteria)
        # (1.0 * 0.6 + 0.5 * 0.4) / 1.0 * 10 = 8.0
        assert res.total_score == pytest.approx(8.0, abs=0.01)

    def test_simple_average_calculation(self, criteria, student_id):
        evals = [
            self._make_eval(student_id, CriterionId("c1"), 8.0),
            self._make_eval(student_id, CriterionId("c2"), 6.0),
        ]
        service = GradeCalculationService(SimpleAverageStrategy())
        res = service.calculate_result(student_id, evals, criteria)
        assert res.total_score == pytest.approx(7.0, abs=0.01)

    def test_rounding_decorator(self, criteria, student_id):
        evals = [
            self._make_eval(student_id, CriterionId("c1"), 7.333333),
        ]
        base = WeightedGradeStrategy()
        decorated = RoundingGradeDecorator(base, decimals=2)
        service = GradeCalculationService(decorated)
        res = service.calculate_result(student_id, evals, [criteria[0]])
        assert res.total_score == 7.33

    def test_bonus_cap_decorator(self, criteria, student_id):
        evals = [
            self._make_eval(student_id, CriterionId("c1"), 10.0),
        ]
        # Стратегия выдает 10.5 баллов (бонусы)
        class MockOverMaxStrategy(WeightedGradeStrategy):
            def calculate(self, evaluations, criteria):
                return 10.5, 10.0

        capped = BonusCapGradeDecorator(MockOverMaxStrategy())
        service = GradeCalculationService(capped)
        res = service.calculate_result(student_id, evals, criteria)
        assert res.total_score == 10.0  # ограничено максимумом 10.0

    def test_no_evaluations_raises_error(self, criteria, student_id):
        service = GradeCalculationService(WeightedGradeStrategy())
        with pytest.raises(DomainError, match="нет ни одной оценки"):
            service.calculate_result(student_id, [], criteria)


# ---------------------------------------------------------------------------
# Тесты FinalGrade / FinalResult
# ---------------------------------------------------------------------------

class TestFinalGrade:
    """Тесты объекта-значения FinalGrade."""

    def test_letter_grade_a(self):
        res = FinalGrade(StudentId("s1"), 9.5, 10.0, 95.0, {})
        assert "A" in res.letter_grade()
        assert res.hse_10_grade() == 10

    def test_letter_grade_f(self):
        res = FinalGrade(StudentId("s1"), 4.0, 10.0, 40.0, {})
        assert "F" in res.letter_grade()
        assert res.hse_10_grade() == 4
