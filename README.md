
# SmartShift

### Intelligent Workforce Scheduling & Staffing Management

**SmartShift** is an interactive workforce scheduling application built with Python. It helps managers plan weekly shifts, generate optimized staffing schedules, track employee availability, and address staffing shortages—all while giving employees a dedicated portal to manage their availability and respond to staffing requests.

**[🚀 Try the Live Demo](https://smartshift-lian-demo.streamlit.app/)** · **[View Source Code](https://github.com/lianchemo/smartshift)**

> **Portfolio demo:** Select **Manager Demo** or **Employee Demo** on the landing page. No account or password is required. All sample employee data is fictional.

## Explore the Application

| Manager Dashboard | Employee Portal |
| --- | --- |
| Review weekly staffing metrics and schedules | Review assigned shifts and weekly availability |
| Create shifts with custom staffing requirements | Submit availability before the weekly deadline |
| Generate optimized schedules and approve assignments | Accept or decline staffing requests |
| Publish schedules and track staffing gaps | See published schedules and request statuses |
| Identify suitable employees for understaffed shifts | Switch between both demo roles to explore a complete workflow |

### Suggested Demo Walkthrough

1. Open the [live application](https://smartshift-lian-demo.streamlit.app/) and choose **Manager Demo**.
2. Explore the weekly schedule, staffing metrics, and availability tracking.
3. Select a week with available scheduling actions to generate a schedule preview and review proposed assignments.
4. Explore staffing recommendations and send a request to an eligible employee, when a staffing gap exists.
5. Switch to **Employee Portal** in the same demo session to review availability, assigned shifts, and staffing requests.

The demo is interactive; available actions depend on the selected week's schedule status, availability deadlines, and staffing data.

## Key Features

- **Constraint-based scheduling:** Uses **Google OR-Tools** to generate weekly shift assignment proposals based on employee availability and scheduling constraints.
- **Manager approval workflow:** Review proposed assignments before saving and publishing a weekly schedule.
- **Employee availability:** Submit per-shift availability and track weekly completion and deadlines.
- **Staffing gap detection:** Identify understaffed shifts and recommend eligible employees for additional coverage.
- **Staffing request workflow:** Send, accept, or decline requests, with assignment updates handled by the application.
- **Two interactive role-based demo views:** Explore manager and employee experiences in the same browser session.
- **Isolated demo sessions:** Each visitor receives a separate temporary SQLite database initialized from fictional sample data.
- **Responsive interface:** Streamlit dashboard with summary metrics, schedule cards, and employee-facing views.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Application & UI | Python, Streamlit |
| Scheduling optimization | Google OR-Tools |
| Database | SQLite |
| Persistence | SQLAlchemy |
| Data handling | Pandas |
| Authentication (restricted mode) | Google OAuth via Streamlit authentication |
| Testing | pytest |
| Deployment | Streamlit Community Cloud |

## Architecture & Data Isolation

SmartShift separates the **public portfolio demo** from its **restricted sign-in flow**:

- **Public demo:** Selecting a demo role creates a visitor-specific, writable SQLite copy of `smartshift_demo_template.db`. Both demo views use that same visitor database, while separate visitor sessions receive separate copies.
- **Restricted sign-in:** Google authentication is paired with an authorized-manager email allowlist. Authentication alone does not grant access.
- **Cloud limitation:** The restricted manager database is **not configured on the public deployment**. Authorized Google users see an informational message instead of a live protected workspace. The public demos remain available independently.

The public repository contains a **fictional demo database template**, not a production employee database. Temporary local SQLite storage is intended for demonstration, not persistent production data.

## Run Locally

**Requirements:** Python 3.13 and a compatible environment for the dependencies in `requirements.txt`.

```bash
git clone https://github.com/lianchemo/smartshift.git
cd smartshift
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

The demo database template is included in the repository, so the public demo views can initialize sample data locally. Restricted Google sign-in requires separate local Streamlit secrets and OAuth configuration; credentials are **not** included in this repository.

### Run Tests

```bash
python -m pytest -q
```

The project has an automated pytest suite covering core scheduling and database workflows. The latest local run reported **54 passing tests**.

## Project Status

**Live public portfolio demo** — Manager Demo and Employee Demo are deployed and interactive. Future improvements may include persistent storage and full role-specific access for authenticated employees.

---

Built as a software engineering portfolio project to demonstrate optimization, relational data modeling, backend workflows, testing, and interactive application development.
