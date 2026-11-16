"""
Тесты прецедентов использования (Use Cases) и интеграционные тесты.
Проверяют сценарии взаимодействия с системой end-to-end
с использованием репозиториев в памяти и через DI-контейнер.
"""
import json
import os
import tempfile
import pytest

from src.application.facade import PosApplicationFacade
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
from src.container import Container
from src.domain.factory import RubricBuilder
from src.domain.services import GradeCalculationService, WeightedGradeStrategy
from src.domain.value_objects import DomainError
from src.infrastructure.export import CsvReportExporter, JsonReportExporter
from src.infrastructure.repositories import (
    InMemoryCriterionRepository,
    InMemoryEvaluationRepository,
    InMemoryStudentRepository,
)


# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------

@pytest.fixture
def repos():
    """Набор репозиториев в памяти для изолированных тестов."""
    return {
        "students": InMemoryStudentRepository(),
        "criteria": InMemoryCriterionRepository(),
        "evaluations": InMemoryEvaluationRepository(),
    }


@pytest.fixture
def grading_service():
    return GradeCalculationService(WeightedGradeStrategy())


@pytest.fixture
def container_memory():
    """DI-контейнер с хранением в памяти."""
    return Container(storage_mode="memory")


# ---------------------------------------------------------------------------
# Тесты AddStudentUseCase
# ---------------------------------------------------------------------------

class TestAddStudentUseCase:
    def test_add_student_success(self, repos):
        use_case = AddStudentUseCase(repos["students"])
        student = use_case.execute("Иванов Иван Иванович", "БПИ-21-1")

        assert student.full_name == "Иванов Иван Иванович"
        assert student.group == "БПИ-21-1"
        assert student.id is not None

        saved = repos["students"].find_by_id(student.id)
        assert saved is not None
        assert saved.full_name == "Иванов Иван Иванович"

    def test_add_student_generates_unique_ids(self, repos):
        use_case = AddStudentUseCase(repos["students"])
        s1 = use_case.execute("Иванов И.И.", "Гр-1")
        s2 = use_case.execute("Петров П.П.", "Гр-1")
        assert s1.id != s2.id

    def test_add_student_empty_name_raises_error(self, repos):
        use_case = AddStudentUseCase(repos["students"])
        with pytest.raises(DomainError):
            use_case.execute("", "БПИ-21-1")

    def test_add_student_empty_group_raises_error(self, repos):
        use_case = AddStudentUseCase(repos["students"])
        with pytest.raises(DomainError):
            use_case.execute("Иванов И.И.", "")


# ---------------------------------------------------------------------------
# Тесты UpdateStudentUseCase
# ---------------------------------------------------------------------------

class TestUpdateStudentUseCase:
    def test_update_student_name(self, repos):
        add = AddStudentUseCase(repos["students"])
        student = add.execute("Старое Имя", "Гр-1")

        update = UpdateStudentUseCase(repos["students"])
        updated = update.execute(student.id.value, full_name="Новое Имя")
        assert updated.full_name == "Новое Имя"

    def test_update_nonexistent_student_raises_error(self, repos):
        update = UpdateStudentUseCase(repos["students"])
        with pytest.raises(DomainError, match="не найден"):
            update.execute("nonexistent-id")


# ---------------------------------------------------------------------------
# Тесты DeleteStudentUseCase
# ---------------------------------------------------------------------------

class TestDeleteStudentUseCase:
    def test_delete_student_removes_evaluations(self, repos):
        add_student = AddStudentUseCase(repos["students"])
        add_crit = AddCriterionUseCase(repos["criteria"])
        grade = GradeStudentUseCase(repos["evaluations"], repos["students"], repos["criteria"])
        delete = DeleteStudentUseCase(repos["students"], repos["evaluations"])

        student = add_student.execute("Удаляемый Студент", "Гр-1")
        crit = add_crit.execute("Тест", 10.0, 1.0)
        grade.execute(student.id.value, crit.id.value, 7.0)

        list_evals = ListEvaluationsUseCase(repos["evaluations"])
        assert len(list_evals.execute()) == 1

        delete.execute(student.id.value)

        assert repos["students"].find_by_id(student.id) is None
        assert len(list_evals.execute()) == 0


# ---------------------------------------------------------------------------
# Тесты AddCriterionUseCase
# ---------------------------------------------------------------------------

class TestAddCriterionUseCase:
    def test_add_criterion_success(self, repos):
        use_case = AddCriterionUseCase(repos["criteria"])
        crit = use_case.execute("Оформление кода", 10.0, 0.4, "Описание")

        assert crit.name == "Оформление кода"
        assert crit.max_score == 10.0
        assert crit.weight.value == 0.4
        assert crit.description == "Описание"

    def test_add_criterion_invalid_weight_raises_error(self, repos):
        use_case = AddCriterionUseCase(repos["criteria"])
        with pytest.raises(DomainError):
            use_case.execute("Тест", 10.0, 1.5)

    def test_add_criterion_zero_max_score_raises_error(self, repos):
        use_case = AddCriterionUseCase(repos["criteria"])
        with pytest.raises(DomainError):
            use_case.execute("Тест", 0.0, 0.5)

    def test_add_criterion_duplicate_name_raises_error(self, repos):
        use_case = AddCriterionUseCase(repos["criteria"])
        use_case.execute("Тест", 10.0, 0.5)
        with pytest.raises(DomainError, match="уже существует"):
            use_case.execute("ТЕСТ", 10.0, 0.5)


# ---------------------------------------------------------------------------
# Тесты GradeStudentUseCase
# ---------------------------------------------------------------------------

class TestGradeStudentUseCase:
    @pytest.fixture(autouse=True)
    def setup(self, repos):
        add_student = AddStudentUseCase(repos["students"])
        add_crit = AddCriterionUseCase(repos["criteria"])
        self.student = add_student.execute("Тестовый Студент", "Тест-1")
        self.criterion = add_crit.execute("Тест критерий", 10.0, 1.0)
        self.repos = repos

    def test_grade_student_success(self):
        use_case = GradeStudentUseCase(
            self.repos["evaluations"],
            self.repos["students"],
            self.repos["criteria"],
        )
        ev = use_case.execute(self.student.id.value, self.criterion.id.value, 8.5)
        assert ev.score.value == 8.5

    def test_grade_exceeds_max_raises_error(self):
        use_case = GradeStudentUseCase(
            self.repos["evaluations"],
            self.repos["students"],
            self.repos["criteria"],
        )
        with pytest.raises(DomainError, match="превышает максимум"):
            use_case.execute(self.student.id.value, self.criterion.id.value, 15.0)

    def test_grade_negative_score_raises_error(self):
        use_case = GradeStudentUseCase(
            self.repos["evaluations"],
            self.repos["students"],
            self.repos["criteria"],
        )
        with pytest.raises(DomainError, match="отрицательной"):
            use_case.execute(self.student.id.value, self.criterion.id.value, -1.0)

    def test_duplicate_grade_raises_error(self):
        use_case = GradeStudentUseCase(
            self.repos["evaluations"],
            self.repos["students"],
            self.repos["criteria"],
        )
        use_case.execute(self.student.id.value, self.criterion.id.value, 7.0)
        with pytest.raises(DomainError, match="уже имеет оценку"):
            use_case.execute(self.student.id.value, self.criterion.id.value, 8.0)

    def test_grade_nonexistent_student_raises_error(self):
        use_case = GradeStudentUseCase(
            self.repos["evaluations"],
            self.repos["students"],
            self.repos["criteria"],
        )
        with pytest.raises(DomainError, match="не найден"):
            use_case.execute("nonexistent", self.criterion.id.value, 7.0)


# ---------------------------------------------------------------------------
# Тесты GetFinalResultUseCase
# ---------------------------------------------------------------------------

class TestGetFinalResultUseCase:
    def test_get_final_result_success(self, repos, grading_service):
        add_student = AddStudentUseCase(repos["students"])
        add_crit = AddCriterionUseCase(repos["criteria"])
        grade = GradeStudentUseCase(repos["evaluations"], repos["students"], repos["criteria"])
        get_result = GetFinalResultUseCase(
            repos["students"], repos["evaluations"], repos["criteria"], grading_service
        )

        student = add_student.execute("Иванов И.И.", "Гр-1")
        c1 = add_crit.execute("Критерий А", 10.0, 0.6)
        c2 = add_crit.execute("Критерий Б", 10.0, 0.4)

        grade.execute(student.id.value, c1.id.value, 8.0)
        grade.execute(student.id.value, c2.id.value, 6.0)

        result = get_result.execute(student.id.value)

        # (8*0.6 + 6*0.4) / 1.0 = 7.2
        assert result.total_score == pytest.approx(7.2, abs=0.01)
        assert result.percentage == pytest.approx(72.0, abs=0.1)
        assert result.student_id.value == student.id.value

    def test_get_result_no_evaluations_raises_error(self, repos, grading_service):
        add_student = AddStudentUseCase(repos["students"])
        get_result = GetFinalResultUseCase(
            repos["students"], repos["evaluations"], repos["criteria"], grading_service
        )
        student = add_student.execute("Петров П.П.", "Гр-1")
        with pytest.raises(DomainError, match="нет ни одной оценки"):
            get_result.execute(student.id.value)

    def test_get_result_nonexistent_student_raises_error(self, repos, grading_service):
        get_result = GetFinalResultUseCase(
            repos["students"], repos["evaluations"], repos["criteria"], grading_service
        )
        with pytest.raises(DomainError, match="не найден"):
            get_result.execute("nonexistent-id")


# ---------------------------------------------------------------------------
# Тесты GoF Template Method: CsvReportExporter и JsonReportExporter
# ---------------------------------------------------------------------------

class TestExporters:
    """Тесты экспортёров ведомости."""

    def test_csv_exporter_generates_file(self, container_memory):
        facade = container_memory.facade
        st = facade.add_student("Тест Студент", "Гр-1")
        cr = facade.add_criterion("ДЗ", 10.0, 1.0)
        facade.grade_student(st.id.value, cr.id.value, 9.0)

        students = facade.list_students()
        results = facade.get_all_results()
        criteria = facade.list_criteria()

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
            path = tf.name

        try:
            exporter = CsvReportExporter()
            out = exporter.export(students, results, criteria, path)
            assert os.path.exists(out)
            with open(out, "r", encoding="utf-8") as f:
                content = f.read()
                assert "Тест Студент" in content
                assert "9.00" in content
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_json_exporter_generates_valid_json(self, container_memory):
        facade = container_memory.facade
        st = facade.add_student("Тест Студент", "Гр-1")
        cr = facade.add_criterion("ДЗ", 10.0, 1.0)
        facade.grade_student(st.id.value, cr.id.value, 9.0)

        students = facade.list_students()
        results = facade.get_all_results()
        criteria = facade.list_criteria()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            path = tf.name

        try:
            exporter = JsonReportExporter()
            out = exporter.export(students, results, criteria, path)
            assert os.path.exists(out)
            with open(out, "r", encoding="utf-8") as f:
                data = json.load(f)
                assert "рубрикатор" in data
                assert "ведомость" in data
                assert data["ведомость"][0]["фио"] == "Тест Студент"
        finally:
            if os.path.exists(path):
                os.remove(path)


# ---------------------------------------------------------------------------
# Тесты через DI-контейнер и PosApplicationFacade (интеграционные)
# ---------------------------------------------------------------------------

class TestContainerIntegration:
    """Интеграционные тесты через DI-контейнер и PosApplicationFacade."""

    def test_full_workflow_via_facade(self, container_memory):
        facade = container_memory.facade

        student = facade.add_student("Сидоров С.С.", "МАТ-22-1")
        assert student.full_name == "Сидоров С.С."

        c1 = facade.add_criterion("Теория", 20.0, 0.5)
        c2 = facade.add_criterion("Практика", 20.0, 0.5)

        facade.grade_student(student.id.value, c1.id.value, 16.0)
        facade.grade_student(student.id.value, c2.id.value, 18.0)

        result = facade.get_final_result(student.id.value)
        assert result.total_score == pytest.approx(17.0, abs=0.01)
        assert result.percentage == pytest.approx(85.0, abs=0.1)

    def test_list_students_via_facade(self, container_memory):
        facade = container_memory.facade
        facade.add_student("Студент 1", "Гр-1")
        facade.add_student("Студент 2", "Гр-2")
        students = facade.list_students()
        assert len(students) == 2

    def test_delete_criterion_removes_evaluations(self, container_memory):
        facade = container_memory.facade
        student = facade.add_student("Тест", "Гр-1")
        crit = facade.add_criterion("Тест критерий", 10.0, 1.0)
        facade.grade_student(student.id.value, crit.id.value, 7.0)

        assert len(facade.list_evaluations()) == 1
        facade.delete_criterion(crit.id.value)
        assert len(facade.list_evaluations()) == 0

    def test_update_evaluation_via_facade(self, container_memory):
        facade = container_memory.facade
        student = facade.add_student("Тест", "Гр-1")
        crit = facade.add_criterion("Тест", 10.0, 1.0)
        ev = facade.grade_student(student.id.value, crit.id.value, 5.0)

        updated = facade.update_evaluation(ev.id.value, new_score=8.0, new_comment="Улучшено")
        assert updated.score.value == 8.0
        assert updated.comment == "Улучшено"

    def test_get_all_results(self, container_memory):
        facade = container_memory.facade
        s1 = facade.add_student("Первый", "Гр-1")
        s2 = facade.add_student("Второй", "Гр-1")
        crit = facade.add_criterion("Тест", 10.0, 1.0)

        facade.grade_student(s1.id.value, crit.id.value, 9.0)
        facade.grade_student(s2.id.value, crit.id.value, 7.0)

        results = facade.get_all_results()
        assert len(results) == 2
        scores = {str(st.id): res.total_score for st, res in results}
        assert scores[s1.id.value] == pytest.approx(9.0)
        assert scores[s2.id.value] == pytest.approx(7.0)

    def test_facade_save_rubric_and_get_rubric(self, container_memory):
        facade = container_memory.facade
        rubric = (
            RubricBuilder()
            .add("Критерий 1", 10.0, 0.5)
            .add("Критерий 2", 10.0, 0.5)
            .build()
        )
        facade.save_rubric(rubric)
        loaded = facade.get_rubric()
        assert len(loaded.criteria) == 2

        # Повторный save_rubric не падает с ошибкой, а обновляет критерии
        facade.save_rubric(rubric)
        assert len(facade.get_rubric().criteria) == 2

    def test_json_file_repository_bare_path_and_persistence(self, tmp_path, monkeypatch):
        from src.infrastructure.repositories import (
            JsonFileCriterionRepository,
            JsonFileEvaluationRepository,
            JsonFileStudentRepository,
        )
        from src.domain.entities import Student
        from src.domain.value_objects import StudentId

        monkeypatch.chdir(tmp_path)
        # Путь без директории (bare filename)
        repo = JsonFileStudentRepository("students_bare.json")
        student = Student(id=StudentId("st-1"), full_name="Иван", group="БПИ-1")
        repo.save(student)

        loaded = repo.find_by_id(StudentId("st-1"))
        assert loaded is not None
        assert loaded.full_name == "Иван"
