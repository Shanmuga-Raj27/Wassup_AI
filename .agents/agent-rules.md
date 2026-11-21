# Project Rules & Agent Operating Guidelines

> Strict operational rulebook for AI agents working in this repository. All rules are mandatory and non-negotiable.

---

## 1. Context First (Lookup Before Scanning)
- **Always read `.agents/agent-memory.md` and `.agents/agent-rules.md`** at the beginning of any session or task before searching, listing, or reading source files.
- **Use the Responsibility → File Path Lookup Map** in `agent-memory.md` to navigate directly to the target file.
- **Do not run broad codebase scans**, recursive directory searches, or exploratory grep runs when the lookup map already specifies the responsible files.

---

## 2. Tech Stack & Dependency Discipline
- **Product Name:** **Web Agent**
- **Strictly adhere to the existing tech stack:**
  - Backend: Python 3.12, FastAPI, Uvicorn, Google GenAI SDK (`google-genai`), DDGS (`ddgs` for metasearch), Trafilatura (`trafilatura` for web scraping), Streamlit.
  - Frontend: 
  - Databases: 
- **Never install new packages, libraries, or dependencies** on your own (no `pip install`, `uv add`, `npm install`, `yarn add`, etc.).
- **Always request explicit user approval** before proposing or adding any dependency, and only recommend new tools if genuinely essential to the project.

---

## 3. Explicit Permission for Critical Operations
Always ask clarifying questions and request explicit user confirmation before:
1. **Deleting files, directories, or substantial code blocks.**
2. **Modifying database schemas**, creating or running new Alembic migrations, or altering ORM models in `backend/app/database/db_models.py`.
3. **Changing core architecture**, request flows, security/auth patterns, or data pipelines.
4. **Performing multi-file refactors** across backend services or frontend pages.

---

## 4. Shell, Git & MCP Restrictions
- **Authorized shell execution:** The agent may use essential shell/bash commands only if the task requires it (e.g., inspecting files, exact line counts, directory checks, or running targeted test scripts explicitly requested by the user). Never run heavy build commands, docker commands, or background daemons without explicit user direction or permission granted in conversation.
- **Git read commands permitted:** The agent may use `git diff` and other read-only inspection commands (`git status`, `git log`) to verify code changes and track modifications. Strictly never run git write commands (`git commit`, `git push`, `git reset`, `git checkout`, `git rebase`, `git clean`) automatically.
- **No automatic test suites:** Never launch full automated test suites (e.g., `pytest`, `npm test`, `vitest`) automatically unless explicitly requested by the user.
- **No unapproved MCP tools:** Never call external MCP servers or tools unless specifically asked by the user.

---

## 5. Fast Execution for Small Frontend Tasks
- Execute small frontend UI tasks (tweaking copy, updating icons, adjusting component props, modifying layout alignment) **quickly and directly**.
- Do not run unnecessary deep exploratory codebase scans, test runs, or heavy architectural over-engineering for simple UI adjustments.

---

## 6. Frontend Architecture & Styling (React MUI Only)

---

## 7. Strict Secrets & Privacy Protection
- **NEVER read, open, cat, parse, log, or output:**
  - `.env`, `.env.*`, or any environment file anywhere in the workspace.
  - Credential files, CSV export files (e.g., `aws-secret/*.csv`), PEM private keys (`*.pem`), or bearer tokens.
- If environment variable configuration is needed, reference variable names exclusively from `root/.env.example` or `backend/app/core/config.py`.
- **Device & Personal Privacy Rule:** Never include personal usernames (e.g., device username), user home directory paths, machine-specific paths, or system credentials in documentation, memory files, or file lookup maps. Always use repository-relative paths starting strictly from the project's root folder names (e.g., `backend/...`, `frontend/...`, `documentations/...`).
- **Public Documentation Rule:** Public documentation must never contain secrets, credentials, personal usernames, or machine-specific file paths. Use safe placeholders instead.

---

## 8. Code Comments & Explanation Syntax
- **Always use `#` for comments and explanations:** Every line of code explanation, commentary, or operational note inside Python and script files must strictly use single-line `#` comments.
- **Never use multi-line docstring comments (`"""` or `'''`):** Do not use triple-quoted strings as comments or explanation blocks, as they can be easily confused with actual multiline string literals in code.