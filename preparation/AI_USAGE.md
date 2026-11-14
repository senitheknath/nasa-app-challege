# AI Assistance Record (2026 Space Apps SI / AI Compliance Log)

Updated: **4 November 2026 (Asia/Colombo)**.

Per the 2026 NASA Space Apps Challenge Participant Terms & Conditions and Participant FAQs, participants may use Artificial Intelligence / "Super Intelligence" (SI) tools provided they disclose which tools were used and how they were used during project submission.

| Date | Assistant / Tool | Contribution | Human / Empirical Verification |
|---|---|---|---|
| 2026-11-04 (up to 23:24) | OpenAI Codex (desktop app, running user's ASTRA 6.1 master prompt) | Read user brief; researched NASA POWER, SMAP, MODIS, FAO, DOA/RRDI, and MCDA references; authored `preparation/` research & plan documents and `preparation/power_access_exercise.py`; created `/home/asus/.venvs/agroshift-prep` | Live NASA requests executed at 3 global coordinates; `pip check` and Streamlit hello health check passed. |
| 2026-11-04 (23:35–23:45:47) | OpenAI Codex (desktop app) | Implemented core application (`agroshift/power.py`, `climate.py`, `geography.py`, `decision.py`, `reporting.py`, `data/crops.json`, `scripts/fetch_demo.py`, `app.py`), retrieved 25-year Anuradhapura snapshot (`data/demo_power.json`), wrote 54 tests across 5 test files, and added `Dockerfile`, CI workflow, and launch scripts before stopping at 23:45:47 | 25-year NASA POWER response verified with SHA-256 integrity hash; live `app.py` server started on port 8501. |
| 2026-11-04 (23:46–23:58) | Google Gemini 4 Argon (High) in Antigravity IDE | Resumed from Codex handoff point; verified 2026 Space Apps open-source & AI/SI disclosure rules; added Apache-2.0 `LICENSE`; updated `preparation/requirements.lock.txt`; added automated tests for the 3 documented demo scenarios and Nairobi/Ames global climate checks (`56 passed`); authored full `README.md` and `DEMONSTRATION_AND_SUBMISSION.md`; updated `HANDOFF.md`, `STATUS.md`, `SETUP.md`, `SOURCES.md`; initialized local Git repository on `main` | Executed full 56-test Pytest suite in WSL2 Ubuntu-26.04 (`Python 3.14.4`), verified `pip check`, verified live `app.py` health endpoint (`HTTP 200 ok`), and verified `git status` / commit state. |

### Runtime AI Note
The AgroShift AI runtime application (`app.py` and `agroshift/*`) uses deterministic coverage-aware climate calculations and a transparent interval-valued Multi-Criteria Decision Analysis (MCDA) engine. It does not invoke an external LLM at runtime and does not use a machine-learning model trained on fabricated agricultural yield data.


On 8 November 2026 Codex audited the existing local working tree, isolated the synthetic educational models, corrected regional screening and provenance, checked the original DOA and FAO references, updated tests and launched the corrected Streamlit application. See docs/SCIENTIFIC_AUDIT.md and docs/VERIFICATION.md. Optional Gemini output selection was tested with a mock API. No user key was sent during testing.
