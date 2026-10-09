from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.diff import generate_unified_diff
from app.repository import RepositoryContext

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AgentResult:
    task: str
    summary: str
    plan: list[str]
    reasoning: list[str]
    relevant_files: list[str]
    diff: str
    progress: list[str] = field(default_factory=list)
    task_complexity: str = "simple"
    assigned_agents: list[str] = field(default_factory=list)


class CoordinatorAgent:
    """Assigns work based on task complexity and delegates to specialist agents."""

    def __init__(self) -> None:
        self.progress: list[str] = []

    def decide_complexity(self, task: str, context: RepositoryContext | None = None) -> str:
        lowered = task.lower()
        score = 0

        if any(keyword in lowered for keyword in ("validation", "logging", "error", "refactor", "test", "document", "debug")):
            score += 2
        if any(keyword in lowered for keyword in ("across", "multiple", "repository", "architecture", "workflow", "integration")):
            score += 2
        if any(keyword in lowered for keyword in ("hello", "print", "odd", "even", "number")):
            score -= 1

        if context is not None:
            if context.total_files > 30:
                score += 2
            if len(context.relevant_files) >= 4:
                score += 2

        if score >= 5:
            return "complex"
        if score >= 2:
            return "moderate"
        return "simple"

    def _agent_pool(self, complexity: str) -> list[str]:
        if complexity == "complex":
            return ["coordinator", "researcher", "planner", "validator", "documenter"]
        if complexity == "moderate":
            return ["coordinator", "researcher", "planner", "validator"]
        return ["coordinator", "researcher", "validator"]

    def _build_reasoning(self, context: RepositoryContext, task: str, complexity: str, agents: list[str]) -> list[str]:
        reasons = [
            f"The coordinator rated this task as '{complexity}' based on the request scope and repository signal.",
            f"Assigned specialists: {', '.join(agents)}.",
        ]

        if not context.relevant_files:
            reasons.append("No strong file matches were found, so the coordinator will keep the execution narrowly scoped and favor a safe minimal patch.")
            return reasons

        for file in context.relevant_files[:3]:
            reasons.append(f"{file.path} was selected by the researcher because it contains high-signal keywords for this task.")
        return reasons

    def _build_plan(self, task: str, complexity: str) -> list[str]:
        lowered = task.lower()
        if "hello" in lowered or "print" in lowered:
            return [
                "Researcher: identify the smallest entry point that should print the requested output.",
                "Implement a minimal hello-world example in the most relevant entry point.",
                "Validator: run the example and confirm the output matches the expected hello message.",
            ]
        if complexity == "complex":
            return [
                "Researcher: scan the repository and rank the files with the strongest task alignment.",
                "Planner: break the task into sub-goals and define the likely implementation sequence.",
                "Validator: identify the safest validation points and the minimal test coverage needed.",
                "Documenter: update any user-facing guidance required by the change.",
                "Coordinator: integrate the specialist outputs into one final implementation summary and diff.",
            ]
        if complexity == "moderate":
            return [
                "Researcher: identify the most relevant files and likely entry points.",
                "Planner: convert the request into a focused implementation strategy.",
                "Validator: check the change with targeted validation or regression tests.",
                "Coordinator: consolidate the final plan and patch preview.",
            ]
        return [
            "Researcher: inspect the repository for the most relevant files.",
            "Implement the minimum fix that satisfies the requested behavior.",
            "Validator: keep the change minimal and confirm the output or behavior matches the request.",
            "Coordinator: summarize the recommendation in a compact plan and diff.",
        ]

    def _build_diff(self, context: RepositoryContext, task: str) -> str:
        if "hello" in task.lower() or "print" in task.lower():
            original = "print('Hello from the app')\n"
            updated = "print('Hello, world!')\n"
            return generate_unified_diff(original, updated, "main.py")

        if any(word in task.lower() for word in ("validation", "logging", "error", "guard")):
            original = "def handle_request(user_input):\n    return user_input.strip()\n"
            updated = (
                "def handle_request(user_input):\n"
                "    if not user_input or not user_input.strip():\n"
                "        raise ValueError('user_input cannot be empty')\n"
                "    logger.info('Processing request: %s', user_input)\n"
                "    return user_input.strip()\n"
            )
            return generate_unified_diff(original, updated, "request_handler.py")

        if context.relevant_files:
            target = context.relevant_files[0]
            original = target.excerpt or "def placeholder():\n    return None\n"
            updated = (
                original
                + "\n\n# Coordinated multi-agent patch: apply the task-specific fix, validate the behavior, "
                + "and document the implementation summary.\n"
            )
            return generate_unified_diff(original, updated, target.path)

        return generate_unified_diff(
            "",
            "# Multi-agent coordination\n- identify the relevant implementation points\n- keep the patch focused\n- validate and summarize the result\n",
            "README.md",
        )

    def analyze_repository(self, context: RepositoryContext, task: str | None = None) -> AgentResult:
        task_text = task or context.request or "review this repository and propose the next coding step"
        self.progress = [
            "Coordinator evaluating task complexity",
            "Researcher ranking relevant files",
            "Specialists producing the execution plan",
            "Coordinator integrating the final diff",
        ]
        complexity = self.decide_complexity(task_text, context)
        assigned_agents = self._agent_pool(complexity)
        reasoning = self._build_reasoning(context, task_text, complexity, assigned_agents)
        plan = self._build_plan(task_text, complexity)
        summary = (
            f"Coordinator selected '{complexity}' complexity and assigned {len(assigned_agents)} agents. "
            f"Found {context.total_files} files in the repository and {len(context.relevant_files)} high-signal candidates."
        )

        return AgentResult(
            task=task_text,
            summary=summary,
            plan=plan,
            reasoning=reasoning,
            relevant_files=[item.path for item in context.relevant_files],
            diff=self._build_diff(context, task_text),
            progress=self.progress,
            task_complexity=complexity,
            assigned_agents=assigned_agents,
        )


class CodingAgent(CoordinatorAgent):
    """Backward-compatible coding assistant that delegates to the coordinator workflow."""
