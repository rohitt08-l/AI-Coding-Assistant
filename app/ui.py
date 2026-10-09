from __future__ import annotations

import logging

from app.agent import CodingAgent
from app.config import get_settings
from app.llm.provider import validate_groq_connection
from app.repository import RepositoryScanner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

try:
    import streamlit as st
except ImportError:  # pragma: no cover - only used in local Streamlit app execution.
    st = None


def _render_streamlit_ui() -> None:
    if st is None:
        logger.error("Streamlit is required to run the coding agent UI.")
        raise RuntimeError("Streamlit is not installed. Install the project dependencies and run the app again.")

    st.set_page_config(page_title="Coding Agent", page_icon="🤖", layout="wide")
    st.title("Coding Agent")
    st.caption("Natural-language coding assistance for any repository on disk.")

    settings = get_settings()
    groq_status_ok, groq_status_message = validate_groq_connection()
    if groq_status_ok:
        st.success(groq_status_message)
    else:
        st.warning(groq_status_message)

    st.caption(f"Groq API key configured: {'Yes' if settings.groq_api_key else 'No'}")

    default_repo = "."
    task = st.text_area("Coding task", placeholder="Describe the change you want, for example: add logging and validation around the API request flow.")
    repo_path = st.text_input("Repository path", value=default_repo)

    if st.button("Run analysis"):
        if not task.strip():
            st.warning("Please describe a coding task before running the agent.")
            return

        logger.info("Starting repository analysis for task: %s", task)
        with st.spinner("Scanning repository and ranking relevant files..."):
            try:
                context = RepositoryScanner.scan(repo_path, task)
                agent = CodingAgent()
                result = agent.analyze_repository(context, task)
                logger.info("Repository analysis finished for %s", repo_path)
            except (FileNotFoundError, OSError, ValueError) as exc:
                logger.exception("Repository analysis failed")
                st.error(f"Analysis failed: {exc}")
                return

        st.subheader("Coordinator decision")
        st.info(f"Task complexity: {result.task_complexity}")
        st.write("Assigned agents: " + ", ".join(result.assigned_agents))

        st.subheader("Agent progress")
        for item in result.progress:
            st.write(f"- {item}")

        st.subheader("Relevant files")
        if result.relevant_files:
            for relative_path in result.relevant_files:
                st.write(f"- {relative_path}")
        else:
            st.write("No high-confidence matches were found. The agent will still provide a safe, minimal patch suggestion.")

        st.subheader("Implementation plan")
        for index, step in enumerate(result.plan, start=1):
            st.write(f"{index}. {step}")

        st.subheader("Why this change")
        for item in result.reasoning:
            st.write(f"- {item}")

        st.subheader("Unified diff")
        st.code(result.diff, language="diff")

        st.subheader("Summary")
        st.write(result.summary)


def render_app() -> None:
    _render_streamlit_ui()
