def format_breakdown(selected_projects, dimension):
    total_budget = sum(project["budget_eur"] for project in selected_projects)

    if total_budget == 0:
        return "  - No projects selected"

    grouped_budgets = {}

    for project in selected_projects:
        key = project[dimension]
        grouped_budgets[key] = grouped_budgets.get(key, 0) + project["budget_eur"]

    lines = []

    for key, budget in sorted(grouped_budgets.items(), key=lambda item: item[1], reverse=True):
        percentage = round((budget / total_budget) * 100, 1)
        lines.append(f"  - {key}: €{budget:,} ({percentage}%)")

    return "\n".join(lines)


def format_projects(selected_projects):
    if not selected_projects:
        return "  - No projects selected"

    lines = []

    for project in selected_projects:
        lines.append(
            f"  - {project['title']} | Risk: {project['risk_score']}/10 | Budget: €{project['budget_eur']:,}"
        )

    return "\n".join(lines)


def build_ai_portfolio_context(selected_projects, summary, max_budget):
    total_budget = summary["total_budget"]

    return {
        "count": summary["project_count"],
        "total_budget": total_budget,
        "remaining_budget": max_budget - total_budget,
        "average_risk": round(summary["average_risk"], 1),
        "subtopic_diversity": summary["subtopic_diversity_score"],
        "institution_diversity": summary["institution_diversity_score"],
        "subtopic_breakdown": format_breakdown(selected_projects, "subtopic"),
        "institution_breakdown": format_breakdown(selected_projects, "host_institution"),
        "project_list": format_projects(selected_projects),
    }


def build_ai_summary_prompt(portfolio_a, portfolio_b):
    return f"""
You are an analyst advising a research funder. Their strategic goals are to fund projects that are more diverse and higher risk than their current portfolio. They do not have specific numerical targets — this is a direction, not a formula.

You are comparing two alternative funding portfolios. Use only the data provided below — do not infer, assume or hallucinate any figures not present in this data.

PORTFOLIO A
- Projects selected: {portfolio_a["count"]}
- Total budget allocated: €{portfolio_a["total_budget"]:,}
- Remaining budget: €{portfolio_a["remaining_budget"]:,}
- Average risk score: {portfolio_a["average_risk"]}/10
- Subtopic diversity score: {portfolio_a["subtopic_diversity"]} out of 1.0
- Institution diversity score: {portfolio_a["institution_diversity"]} out of 1.0

Budget by subtopic:
{portfolio_a["subtopic_breakdown"]}

Budget by institution:
{portfolio_a["institution_breakdown"]}

Projects:
{portfolio_a["project_list"]}

PORTFOLIO B
- Projects selected: {portfolio_b["count"]}
- Total budget allocated: €{portfolio_b["total_budget"]:,}
- Remaining budget: €{portfolio_b["remaining_budget"]:,}
- Average risk score: {portfolio_b["average_risk"]}/10
- Subtopic diversity score: {portfolio_b["subtopic_diversity"]} out of 1.0
- Institution diversity score: {portfolio_b["institution_diversity"]} out of 1.0

Budget by subtopic:
{portfolio_b["subtopic_breakdown"]}

Budget by institution:
{portfolio_b["institution_breakdown"]}

Projects:
{portfolio_b["project_list"]}

Using only the data above, write a 4-5 sentence summary that:
1. States which portfolio better aligns with the funder's goals of greater diversity and higher risk, and by how much
2. Calls out the most significant difference between the two portfolios with specific figures
3. Notes any meaningful tradeoffs
4. Ends with a single concrete recommendation

Be specific and use the actual numbers and names from the data. Do not use vague language like "somewhat more diverse" — quantify it.
""".strip()


def clean_ai_summary(text):
    return (
        text
        .replace("**", "")
        .replace("##", "")
        .replace("#", "")
        .strip()
    )