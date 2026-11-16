"""
Консольный интерфейс пользователя (main.py).
Точка входа в приложение «ПОС» — Преподавательская Оценка Студентов.

Архитектура Ports & Adapters:
- CLI взаимодействует ТОЛЬКО с PosApplicationFacade;
- Никакой доменной логики в UI;
- Все нарушения инвариантов перехватываются как DomainError с выводом
  понятных сообщений пользователю;
- Поддерживается флаг командной строки `--demo` и пункт меню для сквозного
  демонстрационного сценария.
"""
from __future__ import annotations

import argparse
import os
import sys

# Добавляем корневую директорию проекта в sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.container import Container
from src.domain.value_objects import DomainError
from src.infrastructure.demo import run_pos_demo


# ---------------------------------------------------------------------------
# Утилиты ввода/вывода
# ---------------------------------------------------------------------------

def clear_screen() -> None:
    """Очищает экран консоли."""
    os.system("cls" if os.name == "nt" else "clear")


def print_header(title: str) -> None:
    """Выводит форматированный заголовок."""
    width = 65
    print("\n" + "=" * width)
    print(f"  {title}".center(width))
    print("=" * width)


def print_separator() -> None:
    print("-" * 65)


def input_int(prompt: str, min_val: int = None, max_val: int = None) -> int:
    """Запрашивает целое число с проверкой диапазона."""
    while True:
        try:
            raw = input(prompt).strip()
            value = int(raw)
            if min_val is not None and value < min_val:
                print(f"  ⚠ Число должно быть не меньше {min_val}")
                continue
            if max_val is not None and value > max_val:
                print(f"  ⚠ Число должно быть не больше {max_val}")
                continue
            return value
        except ValueError:
            print("  ⚠ Пожалуйста, введите корректное целое число")


def input_float(prompt: str, min_val: float = None, max_val: float = None) -> float:
    """Запрашивает вещественное число с проверкой диапазона."""
    while True:
        try:
            raw = input(prompt).strip().replace(",", ".")
            value = float(raw)
            if min_val is not None and value < min_val:
                print(f"  ⚠ Значение должно быть не меньше {min_val}")
                continue
            if max_val is not None and value > max_val:
                print(f"  ⚠ Значение должно быть не больше {max_val}")
                continue
            return value
        except ValueError:
            print("  ⚠ Пожалуйста, введите число (например, 8.5)")


def input_str(prompt: str, allow_empty: bool = False) -> str:
    """Запрашивает непустую строку у пользователя."""
    while True:
        value = input(prompt).strip()
        if value or allow_empty:
            return value
        print("  ⚠ Поле не может быть пустым")


def pause() -> None:
    """Ожидает нажатия клавиши Enter."""
    input("\n  [Нажмите Enter для продолжения...]")


def confirm(prompt: str = "Вы уверены?") -> bool:
    """Запрашивает подтверждение действия."""
    answer = input(f"  {prompt} (д/н): ").strip().lower()
    return answer in ("д", "да", "y", "yes")


# ---------------------------------------------------------------------------
# Выбор объектов из списков
# ---------------------------------------------------------------------------

def choose_student(facade) -> str | None:
    """Отображает список студентов и возвращает ID выбранного."""
    students = facade.list_students()
    if not students:
        print("  ⚠ Список студентов пуст")
        return None
    print("\n  Студенты на курсе:")
    for i, s in enumerate(students, 1):
        print(f"  {i}. {s.full_name} ({s.group})")
    print("  0. Отмена")
    idx = input_int("  Выберите номер студента: ", 0, len(students))
    if idx == 0:
        return None
    return students[idx - 1].id.value


def choose_criterion(facade) -> str | None:
    """Отображает список критериев и возвращает ID выбранного."""
    criteria = facade.list_criteria()
    if not criteria:
        print("  ⚠ Рубрикатор пуст")
        return None
    print("\n  Критерии рубрикатора:")
    for i, c in enumerate(criteria, 1):
        print(f"  {i}. {c.name} [макс. {c.max_score} б., вес {c.weight.value}]")
    print("  0. Отмена")
    idx = input_int("  Выберите номер критерия: ", 0, len(criteria))
    if idx == 0:
        return None
    return criteria[idx - 1].id.value


def choose_evaluation(facade, student_id: str = None) -> str | None:
    """Отображает список оценок и возвращает ID выбранной."""
    evaluations = facade.list_evaluations(student_id)
    if not evaluations:
        print("  ⚠ Оценок не найдено")
        return None

    students = {s.id.value: s for s in facade.list_students()}
    criteria = {c.id.value: c for c in facade.list_criteria()}

    print("\n  Список оценок:")
    for i, ev in enumerate(evaluations, 1):
        st = students.get(ev.student_id.value)
        cr = criteria.get(ev.criterion_id.value)
        st_name = st.full_name if st else str(ev.student_id)
        cr_name = cr.name if cr else str(ev.criterion_id)
        print(f"  {i}. {st_name} | {cr_name}: {ev.score.value} б. ({ev.eval_date})")
    print("  0. Отмена")
    idx = input_int("  Выберите номер оценки: ", 0, len(evaluations))
    if idx == 0:
        return None
    return evaluations[idx - 1].id.value


# ---------------------------------------------------------------------------
# Меню: Студенты
# ---------------------------------------------------------------------------

def menu_students(facade) -> None:
    while True:
        print_header("👤 Управление студентами")
        print("  1. Список всех студентов")
        print("  2. Добавить студента")
        print("  3. Редактировать данные студента")
        print("  4. Удалить студента")
        print("  0. Вернуться в главное меню")
        print_separator()
        choice = input_int("  Выберите действие: ", 0, 4)

        match choice:
            case 0:
                return
            case 1:
                students = facade.list_students()
                if not students:
                    print("\n  ⚠ На курсе пока нет зарегистрированных студентов")
                else:
                    print(f"\n  Всего студентов: {len(students)}")
                    print_separator()
                    for i, s in enumerate(students, 1):
                        print(f"  {i}. {s.full_name} | Группа: {s.group} | ID: {s.id.value}")
                    print_separator()
                pause()

            case 2:
                print_header("Добавление нового студента")
                try:
                    name = input_str("  ФИО студента: ")
                    group = input_str("  Академическая группа: ")
                    student = facade.add_student(name, group)
                    print(f"\n  ✅ Студент успешно добавлен: {student.full_name} ({student.group})")
                except DomainError as err:
                    print(f"\n  ❌ Ошибка домена: {err}")
                pause()

            case 3:
                print_header("Редактирование данных студента")
                sid = choose_student(facade)
                if sid:
                    try:
                        print("  (Нажмите Enter, чтобы оставить поле без изменений)")
                        name = input("  Новое ФИО: ").strip() or None
                        group = input("  Новая группа: ").strip() or None
                        student = facade.update_student(sid, name, group)
                        print(f"\n  ✅ Данные обновлены: {student.full_name} ({student.group})")
                    except DomainError as err:
                        print(f"\n  ❌ Ошибка домена: {err}")
                    pause()

            case 4:
                print_header("Удаление студента")
                sid = choose_student(facade)
                if sid:
                    st_map = {s.id.value: s for s in facade.list_students()}
                    st = st_map.get(sid)
                    if st and confirm(f"Удалить студента «{st.full_name}» и все его оценки?"):
                        try:
                            facade.delete_student(sid)
                            print("  ✅ Студент и все его оценки удалены")
                        except DomainError as err:
                            print(f"  ❌ Ошибка домена: {err}")
                    pause()


# ---------------------------------------------------------------------------
# Меню: Рубрикатор и критерии
# ---------------------------------------------------------------------------

def menu_criteria(facade) -> None:
    while True:
        print_header("📋 Управление критериями (Рубрикатор)")
        print("  1. Просмотреть текущий рубрикатор")
        print("  2. Добавить критерий оценивания")
        print("  3. Редактировать критерий")
        print("  4. Удалить критерий")
        print("  0. Вернуться в главное меню")
        print_separator()
        choice = input_int("  Выберите действие: ", 0, 4)

        match choice:
            case 0:
                return
            case 1:
                criteria = facade.list_criteria()
                if not criteria:
                    print("\n  ⚠ Рубрикатор пуст. Добавьте критерии оценивания.")
                else:
                    tot_weight = sum(c.weight.value for c in criteria)
                    print(f"\n  Рубрикатор курса ({len(criteria)} критериев):")
                    print(f"  Суммарный вес критериев: {tot_weight:.2f}" + (" (норма)" if abs(tot_weight - 1.0) <= 0.01 else " ⚠ (рекомендуется 1.0)"))
                    print_separator()
                    for i, c in enumerate(criteria, 1):
                        print(f"  {i}. {c.name}")
                        print(f"     Максимальный балл: {c.max_score}")
                        print(f"     Вклад в итог (вес): {c.weight.value}")
                        if c.description:
                            print(f"     Описание: {c.description}")
                        print(f"     ID: {c.id.value}")
                        print_separator()
                pause()

            case 2:
                print_header("Добавление критерия в рубрикатор")
                try:
                    name = input_str("  Название критерия: ")
                    max_score = input_float("  Максимальный балл (> 0): ", 0.01)
                    weight = input_float("  Вес критерия (в диапазоне (0, 1]): ", 0.0001, 1.0)
                    desc = input("  Описание критерия (необязательно): ").strip()
                    crit = facade.add_criterion(name, max_score, weight, desc)
                    print(f"\n  ✅ Критерий успешно добавлен: {crit.name} (вес {crit.weight.value})")
                except DomainError as err:
                    print(f"\n  ❌ Ошибка домена: {err}")
                pause()

            case 3:
                print_header("Редактирование критерия")
                cid = choose_criterion(facade)
                if cid:
                    try:
                        print("  (Нажмите Enter, чтобы оставить поле без изменений)")
                        name = input("  Новое название: ").strip() or None
                        max_s_str = input("  Новый максимум: ").strip()
                        max_s = float(max_s_str.replace(",", ".")) if max_s_str else None
                        w_str = input("  Новый вес: ").strip()
                        w = float(w_str.replace(",", ".")) if w_str else None
                        desc = input("  Новое описание: ").strip() or None

                        crit = facade.update_criterion(cid, name, max_s, w, desc)
                        print(f"\n  ✅ Критерий обновлён: {crit.name} [0..{crit.max_score}] вес={crit.weight.value}")
                    except (DomainError, ValueError) as err:
                        print(f"\n  ❌ Ошибка: {err}")
                    pause()

            case 4:
                print_header("Удаление критерия")
                cid = choose_criterion(facade)
                if cid:
                    crit_map = {c.id.value: c for c in facade.list_criteria()}
                    c = crit_map.get(cid)
                    if c and confirm(f"Удалить критерий «{c.name}» и все выставленные по нему оценки?"):
                        try:
                            facade.delete_criterion(cid)
                            print("  ✅ Критерий и связанные оценки удалены")
                        except DomainError as err:
                            print(f"  ❌ Ошибка домена: {err}")
                    pause()


# ---------------------------------------------------------------------------
# Меню: Оценки
# ---------------------------------------------------------------------------

def menu_evaluations(facade) -> None:
    while True:
        print_header("✏️  Управление оценками")
        print("  1. Просмотреть все оценки")
        print("  2. Просмотреть оценки конкретного студента")
        print("  3. Выставить оценку студенту")
        print("  4. Исправить оценку")
        print("  5. Отменить (удалить) оценку")
        print("  0. Вернуться в главное меню")
        print_separator()
        choice = input_int("  Выберите действие: ", 0, 5)

        match choice:
            case 0:
                return
            case 1 | 2:
                student_id = None
                if choice == 2:
                    student_id = choose_student(facade)
                    if not student_id:
                        pause()
                        continue

                evaluations = facade.list_evaluations(student_id)
                students_map = {s.id.value: s for s in facade.list_students()}
                criteria_map = {c.id.value: c for c in facade.list_criteria()}

                if not evaluations:
                    print("\n  ⚠ Оценок пока нет")
                else:
                    print(f"\n  Найдено оценок: {len(evaluations)}")
                    print_separator()
                    for ev in evaluations:
                        st = students_map.get(ev.student_id.value)
                        cr = criteria_map.get(ev.criterion_id.value)
                        st_name = st.full_name if st else f"ID:{ev.student_id}"
                        cr_name = cr.name if cr else f"ID:{ev.criterion_id}"
                        max_s = f"/{cr.max_score}" if cr else ""
                        print(f"  {st_name} | {cr_name}: {ev.score.value}{max_s} б.")
                        if ev.comment:
                            print(f"    Комментарий: «{ev.comment}»")
                        print(f"    Дата: {ev.eval_date} | ID: {ev.id.value}")
                        print_separator()
                pause()

            case 3:
                print_header("Выставление оценки студенту")
                sid = choose_student(facade)
                if not sid:
                    pause()
                    continue
                cid = choose_criterion(facade)
                if not cid:
                    pause()
                    continue

                crit_map = {c.id.value: c for c in facade.list_criteria()}
                crit = crit_map.get(cid)
                max_s = crit.max_score if crit else 10.0

                try:
                    score = input_float(f"  Оценка в баллах [0..{max_s}]: ")
                    comment = input("  Комментарий преподавателя (необязательно): ").strip()
                    ev = facade.grade_student(sid, cid, score, comment)
                    print(f"\n  ✅ Оценка {ev.score.value} б. успешно выставлена!")
                except DomainError as err:
                    print(f"\n  ❌ Ошибка домена: {err}")
                pause()

            case 4:
                print_header("Исправление (обновление) оценки")
                sid = choose_student(facade)
                if not sid:
                    pause()
                    continue
                eid = choose_evaluation(facade, sid)
                if not eid:
                    pause()
                    continue

                evals = facade.list_evaluations(sid)
                ev_obj = next((e for e in evals if e.id.value == eid), None)
                crit_map = {c.id.value: c for c in facade.list_criteria()}
                crit = crit_map.get(ev_obj.criterion_id.value) if ev_obj else None
                max_s = crit.max_score if crit else 10.0

                try:
                    score_str = input(f"  Новый балл [0..{max_s}] (или Enter, чтобы не менять): ").strip()
                    new_score = float(score_str.replace(",", ".")) if score_str else None
                    new_comment = input("  Новый комментарий (или Enter): ").strip() or None

                    ev = facade.update_evaluation(eid, new_score, new_comment)
                    print(f"\n  ✅ Оценка успешно обновлена: {ev.score.value} б.")
                except (DomainError, ValueError) as err:
                    print(f"\n  ❌ Ошибка: {err}")
                pause()

            case 5:
                print_header("Отмена (удаление) оценки")
                sid = choose_student(facade)
                if not sid:
                    pause()
                    continue
                eid = choose_evaluation(facade, sid)
                if not eid:
                    pause()
                    continue

                if confirm("Удалить выбранную оценку?"):
                    try:
                        facade.delete_evaluation(eid)
                        print("  ✅ Оценка удалена")
                    except DomainError as err:
                        print(f"  ❌ Ошибка домена: {err}")
                pause()


# ---------------------------------------------------------------------------
# Меню: Итоги
# ---------------------------------------------------------------------------

def menu_results(facade) -> None:
    while True:
        print_header("📊 Расчёт итоговых результатов")
        print("  1. Итоговый балл студента")
        print("  2. Сводная ведомость всех студентов")
        print("  0. Вернуться в главное меню")
        print_separator()
        choice = input_int("  Выберите действие: ", 0, 2)

        match choice:
            case 0:
                return
            case 1:
                sid = choose_student(facade)
                if sid:
                    st_map = {s.id.value: s for s in facade.list_students()}
                    st = st_map.get(sid)
                    try:
                        result = facade.get_final_result(sid)
                        print_header(f"Результат: {st.full_name if st else sid}")
                        print(f"  Группа:               {st.group if st else '—'}")
                        print(f"  Итоговый балл:        {result.total_score:.2f} из {result.max_possible:.2f}")
                        print(f"  Процент выполнения:   {result.percentage:.1f}%")
                        print(f"  Оценка ВШЭ (10-балл): {result.hse_10_grade()}")
                        print(f"  Буквенная оценка:     {result.letter_grade()}")
                        print_separator()
                        print("  Расшифровка по критериям:")
                        for c_name, val in result.breakdown.items():
                            print(f"    • {c_name}: {val} б.")
                        print_separator()
                    except DomainError as err:
                        print(f"\n  ❌ {err}")
                pause()

            case 2:
                try:
                    all_res = facade.get_all_results()
                    if not all_res:
                        print("\n  ⚠ Нет данных для расчёта (выставьте оценки студентам)")
                    else:
                        all_res.sort(key=lambda x: x[1].total_score, reverse=True)
                        print(f"\n  Сводная ведомость курса ({len(all_res)} студентов):")
                        print_separator()
                        print(f"  {'№':<3} {'ФИО Студента':<25} {'Группа':<10} {'Итог':<10} {'%':<8} {'ВШЭ':<5} {'Оценка'}")
                        print_separator()
                        for i, (student, res) in enumerate(all_res, 1):
                            score_str = f"{res.total_score:.2f}/{res.max_possible:.1f}"
                            pct_str = f"{res.percentage:.1f}%"
                            print(
                                f"  {i:<3} {student.full_name:<25} {student.group:<10} "
                                f"{score_str:<10} {pct_str:<8} {res.hse_10_grade():<5} {res.letter_grade()}"
                            )
                        print_separator()
                except DomainError as err:
                    print(f"\n  ❌ {err}")
                pause()


# ---------------------------------------------------------------------------
# Меню: Экспорт
# ---------------------------------------------------------------------------

def menu_export(container: Container) -> None:
    facade = container.facade
    while True:
        print_header("💾 Экспорт итоговой ведомости")
        print("  1. Экспорт в CSV (табличный отчёт)")
        print("  2. Экспорт в JSON (структурированный отчёт)")
        print("  0. Вернуться в главное меню")
        print_separator()
        choice = input_int("  Выберите действие: ", 0, 2)

        match choice:
            case 0:
                return
            case 1 | 2:
                students = facade.list_students()
                criteria = facade.list_criteria()
                results = facade.get_all_results()

                ext = "csv" if choice == 1 else "json"
                default_path = os.path.join("data", f"pos_final_report.{ext}")
                user_path = input(f"  Путь для сохранения [{default_path}]: ").strip()
                target_path = user_path or default_path

                try:
                    if choice == 1:
                        saved_path = container.csv_exporter.export(students, results, criteria, target_path)
                    else:
                        saved_path = container.json_exporter.export(students, results, criteria, target_path)
                    print(f"\n  ✅ Ведомость успешно экспортирована: {os.path.abspath(saved_path)}")
                except Exception as err:
                    print(f"\n  ❌ Ошибка экспорта: {err}")
                pause()


# ---------------------------------------------------------------------------
# Главное меню
# ---------------------------------------------------------------------------

def main_menu(container: Container) -> None:
    facade = container.facade
    while True:
        students_cnt = len(facade.list_students())
        criteria_cnt = len(facade.list_criteria())
        evals_cnt = len(facade.list_evaluations())

        print_header("ПОС — Преподавательская Оценка Студентов")
        print(f"  📊 Статус: {students_cnt} студентов | {criteria_cnt} критериев | {evals_cnt} оценок")
        print_separator()
        print("  1. 👤 Управление студентами")
        print("  2. 📋 Управление критериями (Рубрикатор)")
        print("  3. ✏️  Управление оценками")
        print("  4. 📊 Итоги и сводная ведомость")
        print("  5. 💾 Экспорт ведомости (CSV / JSON)")
        print("  6. 🚀 Запустить сквозную демонстрацию (Demo)")
        print("  0. 🚪 Выход из программы")
        print_separator()
        choice = input_int("  Выберите раздел меню: ", 0, 6)

        match choice:
            case 0:
                print("\n  Работа с системой ПОС завершена. До встречи! 👋\n")
                break
            case 1:
                menu_students(facade)
            case 2:
                menu_criteria(facade)
            case 3:
                menu_evaluations(facade)
            case 4:
                menu_results(facade)
            case 5:
                menu_export(container)
            case 6:
                run_pos_demo()
                pause()


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="ПОС — Преподавательская Оценка Студентов (НИУ ВШЭ, КПО ДЗ №2)"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Запустить автоматический сквозной демонстрационный сценарий и выйти",
    )
    parser.add_argument(
        "--storage",
        choices=["json", "memory"],
        default="json",
        help="Режим хранилища: 'json' (по умолчанию) или 'memory'",
    )
    args = parser.parse_args()

    if args.demo:
        run_pos_demo()
        sys.exit(0)

    print("\n  Инициализация контейнера зависимостей системы ПОС...")
    container = Container(storage_mode=args.storage, data_dir="data")
    print("  Система готова к работе!")
    try:
        main_menu(container)
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Работа с системой ПОС прервана пользователем. До встречи! 👋\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
