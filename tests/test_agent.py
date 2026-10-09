from pathlib import Path

from app.agent import CodingAgent, CoordinatorAgent
from app.repository import RepositoryScanner


def test_repository_scanner_ranks_relevant_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "feature.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (repo / "README.md").write_text("This project adds a new feature and handles errors.\n", encoding="utf-8")

    context = RepositoryScanner.scan(str(repo), "add feature and error handling")

    assert len(context.relevant_files) >= 1
    assert any("feature.py" in file.path for file in context.relevant_files)
    assert any("README.md" in file.path for file in context.relevant_files)


def test_agent_generates_plan_and_diff():
    repo = Path("sample_repo")
    scanner = RepositoryScanner.scan(str(repo), "create a small utility module")
    agent = CodingAgent()

    result = agent.analyze_repository(scanner)

    assert result.plan
    assert "Implement" in " ".join(result.plan)
    assert result.diff
    assert "---" in result.diff
    assert "+++" in result.diff


def test_agent_response_changes_with_task():
    scanner_for_logging = RepositoryScanner.scan("sample_repo", "add validation and logging to main app flow")
    scanner_for_hello = RepositoryScanner.scan("sample_repo", "print hello world")
    agent = CodingAgent()

    result_logging = agent.analyze_repository(scanner_for_logging)
    result_hello = agent.analyze_repository(scanner_for_hello)

    assert result_logging.plan != result_hello.plan
    assert any("validation" in step.lower() for step in result_logging.plan)
    assert any("hello" in step.lower() for step in result_hello.plan)


def test_coordinator_assigns_agents_by_complexity():
    scanner = RepositoryScanner.scan("sample_repo", "add validation and logging across the main app flow with tests and docs")
    coordinator = CoordinatorAgent()

    result = coordinator.analyze_repository(scanner)

    assert result.task_complexity in {"simple", "moderate", "complex"}
    assert len(result.assigned_agents) >= 2
    assert "coordinator" in result.assigned_agents
