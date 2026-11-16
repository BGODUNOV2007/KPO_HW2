"""
Адаптеры экспорта ведомостей — инфраструктурный слой (Infrastructure / Adapters).

Реализация паттерна «Шаблонный метод» (Template Method — GoF Behavioral):
- BaseReportExporter: абстрактный базовый класс, определяющий скелет алгоритма экспорта:
    1. Проверка и создание выходной директории (step 1);
    2. Вызов абстрактного метода _serialize(...) для форматирования данных (step 2 — hook);
    3. Запись результата в файл на диске с кодировкой UTF-8 (step 3);
    4. Возврат пути к сохранённому файлу (step 4).
- CsvReportExporter: конкретный адаптер, переопределяющий шаг сериализации в CSV;
- JsonReportExporter: конкретный адаптер, переопределяющий шаг сериализации в JSON.
"""
from __future__ import annotations

import csv
import json
import os
from abc import ABC, abstractmethod
from io import StringIO
from typing import List, Tuple

from src.domain.entities import Criterion, Student
from src.domain.value_objects import FinalGrade


class BaseReportExporter(ABC):
    """
    Абстрактный базовый экспортёр ведомостей.
    Паттерн «Шаблонный метод» (Template Method — GoF Behavioral).

    Определяет неизменный скелет алгоритма сохранения отчёта,
    делегируя подклассам лишь конкретный формат сериализации.
    """

    def export(
        self,
        students: List[Student],
        results: List[Tuple[Student, FinalGrade]],
        criteria: List[Criterion],
        output_path: str,
    ) -> str:
        """
        Шаблонный метод: выполняет полный цикл подготовки и сохранения отчёта.

        :param students: Список всех студентов
        :param results: Список пар (Student, FinalGrade)
        :param criteria: Список критериев рубрикатора
        :param output_path: Путь к сохраняемому файлу
        :return: Абсолютный или нормализованный путь к созданному файлу
        """
        # Шаг 1: Подготовка директории
        dir_name = os.path.dirname(os.path.abspath(output_path))
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        # Шаг 2: Сериализация данных (делегируется подклассу через абстрактный метод)
        content = self._serialize(students, results, criteria)

        # Шаг 3: Запись на диск
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

        return output_path

    @abstractmethod
    def _serialize(
        self,
        students: List[Student],
        results: List[Tuple[Student, FinalGrade]],
        criteria: List[Criterion],
    ) -> str:
        """
        Преобразует данные ведомости в строковое представление нужного формата.
        Обязательно переопределяется в подклассах.
        """
        ...

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Расширение файла отчёта (csv, json и т.д.)."""
        ...


class CsvReportExporter(BaseReportExporter):
    """
    Экспортёр ведомости в формат CSV (Comma-Separated Values).
    Реализует шаг _serialize для табличного представления ведомости.
    """

    @property
    def file_extension(self) -> str:
        return "csv"

    def _serialize(
        self,
        students: List[Student],
        results: List[Tuple[Student, FinalGrade]],
        criteria: List[Criterion],
    ) -> str:
        result_map = {str(r.student_id): r for _, r in results}
        output = StringIO()

        # Формируем заголовок таблицы
        criterion_names = [c.name for c in criteria]
        fieldnames = (
            ["ФИО", "Группа"]
            + criterion_names
            + ["Итоговый балл", "Максимум", "Процент", "10-балльная оценка", "Буквенная оценка"]
        )

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for student in students:
            row: dict = {
                "ФИО": student.full_name,
                "Группа": student.group,
            }
            # По умолчанию все баллы пустые
            for name in criterion_names:
                row[name] = ""

            result = result_map.get(student.id.value)
            if result:
                for crit_name, score_val in result.breakdown.items():
                    if crit_name in row:
                        row[crit_name] = score_val
                row["Итоговый балл"] = f"{result.total_score:.2f}"
                row["Максимум"] = f"{result.max_possible:.2f}"
                row["Процент"] = f"{result.percentage:.1f}%"
                row["10-балльная оценка"] = result.hse_10_grade()
                row["Буквенная оценка"] = result.letter_grade()
            else:
                row["Итоговый балл"] = ""
                row["Максимум"] = ""
                row["Процент"] = ""
                row["10-балльная оценка"] = ""
                row["Буквенная оценка"] = "Нет оценок"

            writer.writerow(row)

        return output.getvalue()


class JsonReportExporter(BaseReportExporter):
    """
    Экспортёр ведомости в формат JSON.
    Реализует шаг _serialize для иерархического представления данных.
    """

    @property
    def file_extension(self) -> str:
        return "json"

    def _serialize(
        self,
        students: List[Student],
        results: List[Tuple[Student, FinalGrade]],
        criteria: List[Criterion],
    ) -> str:
        result_map = {str(r.student_id): r for _, r in results}

        export_data = {
            "система": "ПОС — Преподавательская Оценка Студентов",
            "рубрикатор": [
                {
                    "id": c.id.value,
                    "название": c.name,
                    "максимум": c.max_score,
                    "вес": c.weight.value,
                    "описание": c.description,
                }
                for c in criteria
            ],
            "ведомость": [],
        }

        for student in students:
            entry: dict = {
                "id": student.id.value,
                "фио": student.full_name,
                "группа": student.group,
            }

            result = result_map.get(student.id.value)
            if result:
                entry["результат"] = {
                    "итоговый_балл": result.total_score,
                    "максимум": result.max_possible,
                    "процент": result.percentage,
                    "оценка_10": result.hse_10_grade(),
                    "оценка_буквенная": result.letter_grade(),
                    "расшифровка_по_критериям": result.breakdown,
                }
            else:
                entry["результат"] = None

            export_data["ведомость"].append(entry)

        return json.dumps(export_data, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Алиасы для обратной совместимости
# ---------------------------------------------------------------------------

BaseExporter = BaseReportExporter
CsvExporter = CsvReportExporter
JsonExporter = JsonReportExporter
