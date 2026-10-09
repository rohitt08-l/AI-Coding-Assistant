# AI Coding Agent

A Streamlit-based coding assistant that can inspect a repository, identify the most relevant files for a task, propose an implementation plan, and generate a git-style unified diff. It follows a modular architecture with a repository scanner, planning agent, diff generator, and validation layer.

## Features

- Natural-language coding task input
- Repository selection and recursive repository scanning
- Ranking of the most relevant files in the target codebase
- Implementation plan generation and rationale summary
- Unified diff preview for proposed changes
- Pytest test coverage for the core repository and LLM provider behavior
- Ruff lint verification for clean, maintainable code
- Deployment-ready Streamlit app configuration

## Repository layout

- `app/` — application logic, repository scanner, agent, and UI helpers
- `app/llm/` — LLM provider abstraction for Groq/OpenAI-compatible endpoints
- `streamlit_app.py` — entry point for the Streamlit dashboard
- `tests/` — pytest coverage for the repository scanner and provider logic
- `sample_repo/` — placeholder repository for local experimentation

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Optionally set a Groq API key in a local `.env` file:

   ```env
   GROQ_API_KEY=your_key_here
   DEFAULT_PROVIDER=groq
   ```

4. Launch the app:

   ```bash
   streamlit run streamlit_app.py
   ```

5. Enter a coding task and repository path in the UI, then click Run analysis.

## Validation

Run the test suite:

```bash
pytest -q
```

Run Ruff:

```bash
ruff check .
```

## Streamlit Cloud deployment

This project is compatible with Streamlit Cloud:

1. Push the repository to GitHub.
2. Create a new Streamlit Cloud app pointing at this repository.
3. Set the app entry file to `streamlit_app.py`.
4. Ensure the environment installs dependencies from `requirements.txt`.
5. The app will read the selected local repository path from the UI at runtime.

## Notes

The current implementation intentionally keeps the agent logic deterministic and local-first so it works without an LLM key. If an OpenAI-compatible provider is configured, the project can also be extended to use the provider abstraction in `app/llm/provider.py` for model-backed completions.