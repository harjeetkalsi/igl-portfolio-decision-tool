# IGL Portfolio Decision Support Tool

A Flask prototype that helps research funders build, compare, and optimise funding portfolios from a shortlist of battery research proposals.

The tool was built as a technical task prototype for the Innovation Growth Lab at Nesta. It focuses on helping a funder compare two alternative funding scenarios using budget, risk, diversity, recommendation algorithms, and an optional AI-generated summary.

## Features

- Browse 50 battery research proposals from `projects.json`
- Build Portfolio A and Portfolio B side by side using checkbox selection
- Track budget totals live against a configurable maximum budget
- Compare portfolios using:
  - total budget
  - average risk score
  - number of subtopics covered
  - number of institutions covered
  - budget-weighted subtopic diversity score
  - budget-weighted institution diversity score
- Visualise budget distribution with Chart.js pie charts
- Generate recommended portfolios using:
  - greedy recommendation algorithm
  - genetic optimisation algorithm
- Compare algorithm results using a shared portfolio fitness score
- Share comparisons via URL query parameters
- Generate an optional OpenAI-powered portfolio summary
- Configure settings from a sidebar panel
- View in-app documentation from the README page

## Tech Stack

- Flask
- Jinja2
- Vanilla JavaScript
- Chart.js
- OpenAI Python SDK
- Gunicorn for deployment
- uv for Python dependency management

There is no database. The project data is loaded from `projects.json`, and portfolio state is encoded in the URL using query parameters.

## Project Structure

```text
.
├── app.py
├── ai_summary.py
├── portfolio_optimisation.py
├── projects.json
├── pyproject.toml
├── uv.lock
├── Procfile
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── portfolio.html
│   ├── compare.html
│   └── readme.html
└── static/
    ├── css/
    │   └── styles.css
    └── js/
        └── app.js
```

## Running Locally

Install dependencies:

```bash
uv sync
```

Run the Flask app:

```bash
uv run flask --app app run --debug --port 5001
```

Open:

```text
http://127.0.0.1:5001
```

## Data

The app loads `projects.json` at startup.

The expected project fields are:

```text
id
title
subtopic
risk_score
peer_review_score
budget_eur
duration_months
host_institution
description
```

The current implementation assumes the JSON file contains a top-level `projects` list.

## Portfolio State

Portfolio selections are stored in the URL rather than in a database or server session.

Example:

```text
/compare?a=P001,P004,P012&b=P003,P007,P019
```

This makes comparisons shareable and easy to restore. Opening a shared URL reconstructs both portfolios automatically.

## Diversity Scoring

The tool uses a budget-weighted diversity score based on the Herfindahl-Hirschman Index.

For each portfolio, the app calculates:

- subtopic diversity
- institution diversity

The calculation groups budget by a dimension, calculates each group's share of the total portfolio budget, computes HHI as the sum of squared shares, and returns:

```text
1 - HHI
```

A score closer to `0` means funding is concentrated. A score closer to `1` means funding is more evenly distributed.

## Recommendation Algorithms

The recommendation logic lives in `portfolio_optimisation.py`.

Both algorithms optimise for:

- 40% subtopic diversity
- 40% institution diversity
- 20% average risk score

### Greedy Recommendation

The greedy algorithm builds a portfolio one project at a time. At each step, it chooses the affordable project that adds the most marginal value to the current portfolio.

It is fast, explainable, and useful for generating a strong first recommendation.

### Genetic Optimisation

The genetic algorithm creates a population of random valid portfolios and evolves them over multiple generations. It keeps stronger portfolios, combines them, and occasionally mutates them to explore more of the search space.

It is slower than the greedy algorithm, but can find stronger combinations because it evaluates many more possible portfolios.

## AI Summary

The compare page includes an optional AI Summary feature powered by OpenAI.

The user enters an OpenAI API key in the settings panel. The key is held in browser memory for the current session and sent to the Flask backend only when the user requests a summary.

The backend constructs the prompt server-side using:

- total number of projects
- total and remaining budget
- average risk score
- diversity scores
- budget breakdown by subtopic
- budget breakdown by institution
- selected project titles, risks, and budgets

The OpenAI response is returned as plain text and displayed on the compare page.

## Key Routes

```text
GET  /
GET  /portfolio/<a|b>
GET  /compare
GET  /readme
POST /recommend/greedy
POST /recommend/genetic
POST /ai-summary
```

## Deployment

The project is configured for Render using `Procfile`:

```text
web: gunicorn app:app
```

Recommended Render settings:

```text
Runtime: Python 3
Build command: uv sync --frozen && uv cache prune --ci
Start command: gunicorn app:app
```

If not using uv on the deployment platform, a simple build command can also be:

```bash
pip install .
```

## Design Decisions

### No Database

The prototype does not use a database because the main state is small and naturally represented as project IDs in the URL. This keeps the app simple to run, easy to review, and shareable without accounts or saved sessions.

A database would be a sensible next step for saved named portfolios, uploaded datasets, collaboration, audit history, or multi-user workflows.

### Vanilla JavaScript

The frontend uses vanilla JavaScript rather than React or another frontend framework. This keeps the prototype lightweight while still supporting live budget tracking, URL state syncing, recommendation actions, settings, charts, and AI summary interactions.

### Separate Domain Modules

The optimisation and AI prompt logic are kept out of `app.py`:

- `portfolio_optimisation.py` owns scoring and recommendation algorithms
- `ai_summary.py` owns AI prompt/context formatting
- `app.py` remains focused on Flask routes and rendering

## Future Improvements

- Upload a custom CSV or JSON dataset
- Configure algorithm weights with sliders
- Add a third portfolio slot
- Export comparison view to PDF
- Save and name portfolios
- Move API key handling fully server-side for production use
- Add automated tests for scoring and optimisation logic
