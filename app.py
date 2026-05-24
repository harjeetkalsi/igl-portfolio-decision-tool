import json 
from pathlib import Path
from flask import Flask, render_template, abort, request, jsonify

from portfolio_optimisation import (
    diversity_score,
    portfolio_fitness,
    recommend_genetic,
    recommend_greedy,
)

from openai import OpenAI

from ai_summary import (
    build_ai_portfolio_context,
    build_ai_summary_prompt,
    clean_ai_summary,
)

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
PROJECTS_FILE = BASE_DIR / 'projects.json'

def load_projects():
    with PROJECTS_FILE.open("r", encoding="utf-8") as file: 
        data = json.load(file)
    
    return data['projects']

    
projects = load_projects()
projects_by_id = {project["id"] : project for project in projects}

def parse_project_ids(value): 
    if not value: 
        return []
    
    return [project_id.strip() for project_id in value.split(",") if project_id.strip()]

def get_projects_by_ids(project_ids):
    
    return [
        projects_by_id[project_id]
        for project_id in project_ids 
        if project_id  in projects_by_id
    ]


def budget_breakdown(selected_projects, dimension):
    total_budget = sum(project["budget_eur"] for project in selected_projects)

    if total_budget == 0:
        return []

    grouped_budgets = {}

    for project in selected_projects:
        key = project[dimension]
        grouped_budgets[key] = grouped_budgets.get(key, 0) + project["budget_eur"]

    return [
        {
            "label": label,
            "value": budget,
            "percentage": round((budget / total_budget) * 100, 1),
        }
        for label, budget in sorted(
            grouped_budgets.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]


def portfolio_chart_data(selected_projects):
    return {
        "subtopic": budget_breakdown(selected_projects, "subtopic"),
        "institution": budget_breakdown(selected_projects, "host_institution"),
    }

def summarise_portfolio(selected_projects): 
    total_budget = sum(project["budget_eur"] for project in selected_projects)

    if selected_projects: 
        average_risk = sum(project["risk_score"] for project in selected_projects) / len(selected_projects)
    else: 
        average_risk = 0 

    unique_subtopics = {
        project["subtopic"]
        for project in selected_projects
    }

    unique_institutions = {
        project["host_institution"]
        for project in selected_projects
    }

    return {
        "total_budget": total_budget, 
        "average_risk": average_risk, 
        "subtopic_count": len(unique_subtopics), 
        "institution_count": len(unique_institutions),
        "project_count" : len(selected_projects),
        "subtopic_diversity_score": diversity_score(selected_projects, "subtopic"),
        "institution_diversity_score": diversity_score(selected_projects, "host_institution"),
    }


@app.route("/")
def index():
    return render_template("index.html", projects=projects)

@app.route("/portfolio/<portfolio_id>")
def portfolio(portfolio_id):

    if portfolio_id not in {"a", "b"}:
        abort(404)

    portfolio_a_ids = parse_project_ids(request.args.get("a"))
    portfolio_b_ids = parse_project_ids(request.args.get("b"))

    if portfolio_id == "a":
        selected_projects = get_projects_by_ids(portfolio_a_ids)
    else: 
        selected_projects = get_projects_by_ids(portfolio_b_ids) 

    summary = summarise_portfolio(selected_projects)

    return render_template(
        "portfolio.html",
        portfolio_id = portfolio_id, 
        portfolio_label = portfolio_id.upper(),
        selected_projects = selected_projects, 
        summary = summary, 
        chart_data=portfolio_chart_data(selected_projects),
        portfolio_a_ids = ",".join(portfolio_a_ids),
        portfolio_b_ids = ",".join(portfolio_b_ids),
    )

@app.route("/compare")
def compare():
    portfolio_a_ids = parse_project_ids(request.args.get("a"))
    portfolio_b_ids = parse_project_ids(request.args.get("b"))

    portfolio_a_projects = get_projects_by_ids(portfolio_a_ids)
    portfolio_b_projects = get_projects_by_ids(portfolio_b_ids)

    portfolio_a_summar = summarise_portfolio(portfolio_a_projects)
    portfolio_b_summary = summarise_portfolio(portfolio_b_projects)

    return render_template(
        "compare.html",
        portfolio_a_projects = portfolio_a_projects,
        portfolio_b_projects = portfolio_b_projects,
        portfolio_a_summary = portfolio_a_summar,
        portfolio_b_summary = portfolio_b_summary,
        portfolio_a_chart_data=portfolio_chart_data(portfolio_a_projects),
        portfolio_b_chart_data=portfolio_chart_data(portfolio_b_projects),
        portfolio_a_ids = ",".join(portfolio_a_ids),
        portfolio_b_ids = ",".join(portfolio_b_ids)
    )

@app.route("/recommend/greedy", methods=["POST"])
def recommend_greedy_route():
    data = request.json or {}
    max_budget = data.get("max_budget", 40000)
    target = data.get("target", "a")

    result = recommend_greedy(projects, max_budget)

    return jsonify({

        "portfolio" : target, 
        "projects" : [project["id"] for project in result], 
        "fitness" : portfolio_fitness(result)
    })

@app.route("/recommend/genetic", methods=["POST"])
def recommend_genetic_route():
    data = request.json or {}
    max_budget = data.get("max_budget", 40000)
    target = data.get("target", "a")

    result = recommend_genetic(projects, max_budget)

    return jsonify({
        "portfolio" : target, 
        "projects" : [project["id"] for project in result], 
        "fitness" : portfolio_fitness(result)
    })

@app.route("/readme")
def readme():
    return render_template("readme.html")


@app.route("/ai-summary", methods=["POST"])
def ai_summary():
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        return jsonify({"error": "No API key provided"}), 401

    data = request.json or {}
    portfolio_a_ids = parse_project_ids(data.get("a"))
    portfolio_b_ids = parse_project_ids(data.get("b"))
    max_budget = data.get("max_budget", 4000000)

    portfolio_a_projects = get_projects_by_ids(portfolio_a_ids)
    portfolio_b_projects = get_projects_by_ids(portfolio_b_ids)

    portfolio_a_context = build_ai_portfolio_context(
        portfolio_a_projects,
        summarise_portfolio(portfolio_a_projects),
        max_budget,
    )
    portfolio_b_context = build_ai_portfolio_context(
        portfolio_b_projects,
        summarise_portfolio(portfolio_b_projects),
        max_budget,
    )

    prompt = build_ai_summary_prompt(portfolio_a_context, portfolio_b_context)

    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            max_output_tokens=700,
        )

        return jsonify({
            "summary": clean_ai_summary(response.output_text)
        })
    except Exception:
        return jsonify({
            "error": "Summary could not be generated. Please check your API key and try again."
        }), 500

if __name__ == "__main__":
    app.run(debug=True, port=5001)

