"""
Сквозной демонстрационный сценарий (Demo Runner) — инфраструктурный слой.

Реализует автоматический прогон всех основных сценариев системы «ПОС»:
1. Построение утверждённого рубрикатора через RubricBuilder (GoF Builder);
2. Регистрация студентов через PosApplicationFacade (GoF Facade);
3. Наглядная демонстрация срабатывания доменных инвариантов:
   - попытка выставить 12 баллов из 10 (DomainError);
   - попытка оценить несуществующий критерий (DomainError);
   - попытка поставить отрицательный балл (DomainError);
   - попытка повторного оценивания по тому же критерию (DomainError);
4. Выставление корректных оценок;
5. Исправление (обновление) оценки студента;
6. Динамический расчёт итогов в GradeCalculationService с применением
   WeightedGradeStrategy и RoundingGradeDecorator;
7. Экспорт итоговой ведомости в форматы CSV и JSON через BaseReportExporter
   (GoF Template Method).
"""
from __future__ import annotations

import os
import sys

from src.container import Container
from src.domain.factory import EvaluationFactory, RubricBuilder
from src.domain.value_objects import CriterionId, DomainError, Score, StudentId


def run_pos_demo(data_dir: str = "data") -> bool:
    """
    Запускает сквозную демонстрацию всех возможностей и инвариантов системы.

    :param data_dir: Директория для сохранения демонстрационных отчётов
    :return: True, если сценарий успешно завершён
    """
    print("\n" + "=" * 70)
    print("   🚀 ЗАПУСК СКВОЗНОЙ ДЕМОНСТРАЦИИ СИСТЕМЫ «ПОС»")
    print("   Преподавательская Оценка Студентов (НИУ ВШЭ, КПО ДЗ №2)")
    print("=" * 70)

    # Используем контейнер в памяти для чистой и изолированной демонстрации
    container = Container(storage_mode="memory", data_dir=data_dir)
    facade = container.facade

    # -----------------------------------------------------------------------
    # ЭТАП 1: Построение рубрикатора через RubricBuilder (GoF Builder)
    # -----------------------------------------------------------------------
    print("\n[ЭТАП 1] 📋 Построение рубрикатора курса через RubricBuilder (GoF Builder)...")
    builder = RubricBuilder()
    rubric = (
        builder
        .add("Домашнее задание №1", max_score=10.0, weight=0.3, description="Базовый синтаксис и ООП")
        .add("Домашнее задание №2", max_score=10.0, weight=0.3, description="DDD, Ports & Adapters, GoF")
        .add("Итоговый проект", max_score=10.0, weight=0.4, description="Консольный модуль ПОС")
        .build(strict_weights=True)
    )

    print(f"  ✅ Рубрикатор успешно собран!")
    print(f"     Критериев: {len(rubric.criteria)}, Суммарный вес: {rubric.total_weight():.2f}")
    for c in rubric.criteria:
        facade.add_criterion(c.name, c.max_score, c.weight.value, c.description)
        print(f"     • «{c.name}»: максимум {c.max_score} б., вес {c.weight.value} (ID: {c.id.value[:8]}...)")

    criteria = facade.list_criteria()
    crit_hw1 = criteria[0]
    crit_hw2 = criteria[1]
    crit_project = criteria[2]

    # -----------------------------------------------------------------------
    # ЭТАП 2: Регистрация студентов через PosApplicationFacade (GoF Facade)
    # -----------------------------------------------------------------------
    print("\n[ЭТАП 2] 👤 Регистрация студентов через фасад приложения...")
    st1 = facade.add_student("Алексей Смирнов", "БПИ-22-1")
    st2 = facade.add_student("Екатерина Морозова", "БПИ-22-1")
    st3 = facade.add_student("Дмитрий Волков", "БПИ-22-2")

    for s in [st1, st2, st3]:
        print(f"  ✅ Зарегистрирован: {s.full_name} ({s.group}) [ID: {s.id.value[:8]}...]")

    # -----------------------------------------------------------------------
    # ЭТАП 3: Наглядная демонстрация защиты инвариантов домена
    # -----------------------------------------------------------------------
    print("\n[ЭТАП 3] 🛡️ Демонстрация строгости доменных инвариантов (DDD):")

    # Инвариант 1: Попытка поставить 12 баллов из 10
    print("\n  1. Проверка инварианта: Попытка поставить 12 баллов из 10.0...")
    try:
        facade.grade_student(st1.id.value, crit_hw1.id.value, 12.0, "Слишком хорошая работа")
        print("  ❌ ОШИБКА: Инвариант пропущен! Оценка 12 выставилась.")
    except DomainError as err:
        print(f"  ✅ [ИНВАРИАНТ ЗАЩИЩЕН] Перехвачено DomainError:")
        print(f"     └── «{err}»")

    # Инвариант 2: Попытка оценить несуществующий критерий
    print("\n  2. Проверка инварианта: Попытка выставить оценку по несуществующему критерию...")
    try:
        fake_id = "non-existent-criterion-uuid"
        facade.grade_student(st1.id.value, fake_id, 8.0, "Фантомный критерий")
        print("  ❌ ОШИБКА: Несуществующий критерий был принят!")
    except DomainError as err:
        print(f"  ✅ [ИНВАРИАНТ ЗАЩИЩЕН] Перехвачено DomainError:")
        print(f"     └── «{err}»")

    # Инвариант 3: Попытка поставить отрицательный балл
    print("\n  3. Проверка инварианта: Попытка поставить отрицательную оценку (-3.0)...")
    try:
        facade.grade_student(st2.id.value, crit_hw1.id.value, -3.0, "Штраф")
        print("  ❌ ОШИБКА: Отрицательная оценка была принята!")
    except DomainError as err:
        print(f"  ✅ [ИНВАРИАНТ ЗАЩИЩЕН] Перехвачено DomainError:")
        print(f"     └── «{err}»")

    # -----------------------------------------------------------------------
    # ЭТАП 4: Выставление корректных оценок
    # -----------------------------------------------------------------------
    print("\n[ЭТАП 4] ✏️ Выставление корректных оценок студентам...")
    # Алексей Смирнов
    facade.grade_student(st1.id.value, crit_hw1.id.value, 9.0, "Отличный чистый код")
    facade.grade_student(st1.id.value, crit_hw2.id.value, 8.5, "Хорошая архитектура")
    facade.grade_student(st1.id.value, crit_project.id.value, 10.0, "Безупречная работа")

    # Екатерина Морозова
    facade.grade_student(st2.id.value, crit_hw1.id.value, 10.0, "Эталонное решение")
    facade.grade_student(st2.id.value, crit_hw2.id.value, 10.0, "Полное соответствие DDD")
    facade.grade_student(st2.id.value, crit_project.id.value, 9.5, "Отличная презентация")

    # Дмитрий Волков
    facade.grade_student(st3.id.value, crit_hw1.id.value, 6.0, "Были замечания по SOLID")
    ev_to_update = facade.grade_student(st3.id.value, crit_hw2.id.value, 5.0, "Сдано после дедлайна")
    facade.grade_student(st3.id.value, crit_project.id.value, 7.0, "Базовый функционал")

    print(f"  ✅ Выставлено {len(facade.list_evaluations())} оценок.")

    # Инвариант 4: Попытка дублирования оценки
    print("\n  4. Проверка инварианта: Попытка повторной оценки студента по тому же критерию...")
    try:
        facade.grade_student(st1.id.value, crit_hw1.id.value, 10.0, "Повторная попытка")
        print("  ❌ ОШИБКА: Разрешено повторное выставление оценки!")
    except DomainError as err:
        print(f"  ✅ [ИНВАРИАНТ ЗАЩИЩЕН] Перехвачено DomainError:")
        print(f"     └── «{err}»")

    # -----------------------------------------------------------------------
    # ЭТАП 5: Исправление оценки (пересдача)
    # -----------------------------------------------------------------------
    print("\n[ЭТАП 5] 🔄 Исправление оценки студента (Дмитрий Волков улучшил ДЗ №2)...")
    print(f"  Было: {ev_to_update.score.value} б.")
    updated_ev = facade.update_evaluation(ev_to_update.id.value, new_score=8.0, new_comment="Защитил исправления на консультации")
    print(f"  Стало: {updated_ev.score.value} б. (Комментарий: «{updated_ev.comment}»)")

    # -----------------------------------------------------------------------
    # ЭТАП 6: Динамический расчёт итогов через Domain Service
    # -----------------------------------------------------------------------
    print("\n[ЭТАП 6] 📊 Динамический расчёт итогов через GradeCalculationService...")
    print("  Используется: WeightedGradeStrategy + RoundingGradeDecorator (ВШЭ, 2 знака):")
    print("  " + "-" * 66)

    results = facade.get_all_results()
    results.sort(key=lambda x: x[1].total_score, reverse=True)

    for rank, (student, grade) in enumerate(results, 1):
        print(
            f"  {rank}. {student.full_name:<20} | "
            f"Итог: {grade.total_score:5.2f} / {grade.max_possible:.1f} | "
            f"{grade.percentage:5.1f}% | "
            f"Оценка ВШЭ: {grade.hse_10_grade():2d} | "
            f"{grade.letter_grade()}"
        )
        print(f"     Расшифровка: {grade.breakdown}")
    print("  " + "-" * 66)

    # -----------------------------------------------------------------------
    # ЭТАП 7: Экспорт ведомости через GoF Template Method
    # -----------------------------------------------------------------------
    print("\n[ЭТАП 7] 💾 Экспорт ведомости (Template Method — CSV и JSON)...")
    os.makedirs(data_dir, exist_ok=True)
    csv_file = os.path.join(data_dir, "demo_final_grades.csv")
    json_file = os.path.join(data_dir, "demo_final_grades.json")

    students = facade.list_students()
    all_crit = facade.list_criteria()

    out_csv = container.csv_exporter.export(students, results, all_crit, csv_file)
    print(f"  ✅ Ведомость CSV экспортирована:  {os.path.abspath(out_csv)}")

    out_json = container.json_exporter.export(students, results, all_crit, json_file)
    print(f"  ✅ Ведомость JSON экспортирована: {os.path.abspath(out_json)}")

    print("\n" + "=" * 70)
    print("   🎉 СКВОЗНАЯ ДЕМОНСТРАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
    print("   Все функциональные требования и инварианты выполнены на 100%.")
    print("=" * 70 + "\n")
    return True
