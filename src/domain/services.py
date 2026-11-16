"""
Доменный сервис расчёта оценок и поведенческие/структурные паттерны GoF:
- Паттерн «Стратегия» (Strategy — GoF Behavioral):
  * IGradeCalculationStrategy — интерфейс стратегии подсчёта;
  * WeightedGradeStrategy — подсчёт по весам критериев;
  * NormalizedGradeStrategy — нормализованный процентный подсчёт;
  * SimpleAverageStrategy — простое среднее арифметическое.
- Паттерн «Декоратор» (Decorator — GoF Structural):
  * RoundingGradeDecorator — округление результата по правилам ВШЭ;
  * BonusCapGradeDecorator — ограничение итогового балла максимальным значением.
- Доменный сервис (Domain Service):
  * GradeCalculationService — инкапсулирует расчёт итогового балла (FinalGrade).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Union

from .entities import Criterion, Evaluation, Rubric
from .value_objects import DomainError, FinalGrade, StudentId


# ---------------------------------------------------------------------------
# Паттерн «Стратегия» (Strategy — GoF Поведенческий)
# ---------------------------------------------------------------------------

class IGradeCalculationStrategy(ABC):
    """
    Интерфейс стратегии подсчёта итоговой оценки.
    Паттерн «Стратегия» (Strategy — GoF Behavioral).

    Позволяет изолировать и свободно подменять математический алгоритм
    подсчёта итогового балла без изменения Domain Service.
    """

    @abstractmethod
    def calculate(
        self,
        evaluations: List[Evaluation],
        criteria: List[Criterion],
    ) -> tuple[float, float]:
        """
        Вычисляет итоговый балл и максимально возможный балл.

        :param evaluations: Список выставленных студенту оценок
        :param criteria: Список критериев рубрикатора
        :return: кортеж (итоговый_набранный_балл, максимально_возможный_балл)
        """
        ...


class WeightedGradeStrategy(IGradeCalculationStrategy):
    """
    Стратегия взвешенного среднего (Weighted Grade Strategy).
    Итоговый балл = sum(score_i * weight_i) / sum(weight_i).
    Учитывает веса каждого критерия из утверждённого рубрикатора.
    """

    def calculate(
        self,
        evaluations: List[Evaluation],
        criteria: List[Criterion],
    ) -> tuple[float, float]:
        criterion_map = {c.id: c for c in criteria}
        total = 0.0
        weight_sum = 0.0
        max_total = 0.0
        max_weight_sum = 0.0

        for ev in evaluations:
            crit = criterion_map.get(ev.criterion_id)
            if crit is None:
                continue
            w = crit.weight.value
            total += ev.score.value * w
            weight_sum += w
            max_total += crit.max_score * w
            max_weight_sum += w

        if weight_sum == 0:
            return 0.0, 0.0

        return total / weight_sum, max_total / max_weight_sum


class NormalizedGradeStrategy(IGradeCalculationStrategy):
    """
    Стратегия нормализованного выполнения (Normalized Grade Strategy).
    Каждый балл нормализуется в долю от своего максимума (score_i / max_i),
    после чего берётся взвешенная сумма с масштабированием на 10-балльную шкалу.
    """

    def calculate(
        self,
        evaluations: List[Evaluation],
        criteria: List[Criterion],
    ) -> tuple[float, float]:
        criterion_map = {c.id: c for c in criteria}
        weighted_norm_sum = 0.0
        weight_sum = 0.0

        for ev in evaluations:
            crit = criterion_map.get(ev.criterion_id)
            if crit is None or crit.max_score <= 0:
                continue
            w = crit.weight.value
            norm_ratio = ev.score.value / crit.max_score
            weighted_norm_sum += norm_ratio * w
            weight_sum += w

        if weight_sum == 0:
            return 0.0, 10.0

        # Нормализованный балл по 10-балльной шкале
        normalized_score = (weighted_norm_sum / weight_sum) * 10.0
        return normalized_score, 10.0


class SimpleAverageStrategy(IGradeCalculationStrategy):
    """
    Стратегия простого среднего (арифметического без учёта весов).
    Итоговый балл = sum(score_i) / N.
    """

    def calculate(
        self,
        evaluations: List[Evaluation],
        criteria: List[Criterion],
    ) -> tuple[float, float]:
        criterion_map = {c.id: c for c in criteria}

        scores: List[float] = []
        max_scores: List[float] = []
        for ev in evaluations:
            crit = criterion_map.get(ev.criterion_id)
            if crit is None:
                continue
            scores.append(ev.score.value)
            max_scores.append(crit.max_score)

        if not scores:
            return 0.0, 0.0

        return sum(scores) / len(scores), sum(max_scores) / len(max_scores)


# ---------------------------------------------------------------------------
# Паттерн «Декоратор» (Decorator — GoF Структурный)
# ---------------------------------------------------------------------------

class RoundingGradeDecorator(IGradeCalculationStrategy):
    """
    Декоратор округления итогового балла.
    Паттерн «Декоратор» (Decorator — GoF Structural).

    Оборачивает любую стратегию IGradeCalculationStrategy и применяет
    правила округления (например, до 2 знаков по регламенту ВШЭ)
    без загрязнения базового алгоритма расчёта.
    """

    def __init__(self, wrapped: IGradeCalculationStrategy, decimals: int = 2) -> None:
        self._wrapped = wrapped
        self._decimals = decimals

    def calculate(
        self,
        evaluations: List[Evaluation],
        criteria: List[Criterion],
    ) -> tuple[float, float]:
        score, max_score = self._wrapped.calculate(evaluations, criteria)
        return round(score, self._decimals), round(max_score, self._decimals)


class BonusCapGradeDecorator(IGradeCalculationStrategy):
    """
    Декоратор ограничения итогового балла (Cap Decorator).
    Паттерн «Декоратор» (Decorator — GoF Structural).

    Ограничивает итоговый результат максимальным баллом, чтобы бонусные
    баллы или округление не превышали допустимый максимум курса.
    """

    def __init__(self, wrapped: IGradeCalculationStrategy) -> None:
        self._wrapped = wrapped

    def calculate(
        self,
        evaluations: List[Evaluation],
        criteria: List[Criterion],
    ) -> tuple[float, float]:
        score, max_score = self._wrapped.calculate(evaluations, criteria)
        capped_score = min(score, max_score)
        return capped_score, max_score


# ---------------------------------------------------------------------------
# Доменный сервис расчёта итоговой оценки (GradeCalculationService)
# ---------------------------------------------------------------------------

class GradeCalculationService:
    """
    Доменный сервис расчёта итогового результата студента.
    В соответствии с DDD:
    - инкапсулирует бизнес-правило, которое не принадлежит одной сущности;
    - гарантирует, что итоговый балл (FinalGrade) всегда вычисляется динамически
      и строго согласован с текущим набором оценок и рубрикатором;
    - использует внедрённую стратегию IGradeCalculationStrategy.
    """

    def __init__(self, strategy: IGradeCalculationStrategy) -> None:
        self._strategy = strategy

    @property
    def strategy(self) -> IGradeCalculationStrategy:
        return self._strategy

    def calculate_result(
        self,
        student_id: StudentId,
        evaluations: List[Evaluation],
        criteria: Union[List[Criterion], Rubric],
    ) -> FinalGrade:
        """
        Рассчитывает итоговый результат студента.

        :param student_id: Идентификатор студента
        :param evaluations: Список выставленных студенту оценок
        :param criteria: Список критериев или агрегат Rubric
        :return: Неизменяемый объект FinalGrade
        :raises DomainError: если у студента нет ни одной оценки
        """
        if not evaluations:
            raise DomainError(
                f"У студента {student_id} нет ни одной оценки для расчёта итога"
            )

        criteria_list = criteria.criteria if isinstance(criteria, Rubric) else criteria
        total_score, max_possible = self._strategy.calculate(evaluations, criteria_list)

        percentage = (total_score / max_possible * 100.0) if max_possible > 0 else 0.0

        # Формируем расшифровку набранных баллов по критериям
        criterion_map = {c.id: c for c in criteria_list}
        breakdown: dict[str, float] = {}
        for ev in evaluations:
            crit = criterion_map.get(ev.criterion_id)
            name = crit.name if crit else str(ev.criterion_id)
            breakdown[name] = ev.score.value

        return FinalGrade(
            student_id=student_id,
            total_score=total_score,
            max_possible=max_possible,
            percentage=round(percentage, 2),
            breakdown=breakdown,
        )


# ---------------------------------------------------------------------------
# Алиасы для полной обратной совместимости
# ---------------------------------------------------------------------------

ScoringStrategy = IGradeCalculationStrategy
WeightedAverageStrategy = WeightedGradeStrategy
RoundedScoreDecorator = RoundingGradeDecorator
GradingService = GradeCalculationService
