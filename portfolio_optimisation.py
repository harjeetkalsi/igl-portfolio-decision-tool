import random


def diversity_score(portfolio, dimension):
    """Return budget-weighted diversity for a portfolio using 1 - HHI.

    A score near 0 means the budget is concentrated in one group.
    A score closer to 1 means the budget is spread more evenly.
    """
    total_budget = sum(project["budget_eur"] for project in portfolio)

    if total_budget == 0:
        return 0

    grouped_budgets = {}

    for project in portfolio:
        key = project[dimension]
        grouped_budgets[key] = grouped_budgets.get(key, 0) + project["budget_eur"]

    # HHI is the sum of squared budget shares. Higher HHI means more concentration.
    hhi = sum(
        (budget / total_budget) ** 2
        for budget in grouped_budgets.values()
    )

    return round(1 - hhi, 2)


def project_score(project, current_portfolio):
    """Score the marginal value of adding one project to the current portfolio."""
    trial = current_portfolio + [project]

    subtopic_gain = (
        diversity_score(trial, "subtopic")
        - diversity_score(current_portfolio, "subtopic")
    )
    institution_gain = (
        diversity_score(trial, "host_institution")
        - diversity_score(current_portfolio, "host_institution")
    )

    # Risk is normalised from a 0-10 scale to 0-1 so it can be combined with diversity.
    risk = project["risk_score"] / 10

    return (0.4 * subtopic_gain) + (0.4 * institution_gain) + (0.2 * risk)


def portfolio_fitness(portfolio):
    """Score an entire portfolio against the three weighted objectives."""
    if not portfolio:
        return 0

    subtopic_diversity = diversity_score(portfolio, "subtopic")
    institution_diversity = diversity_score(portfolio, "host_institution")
    average_risk = (
        sum(project["risk_score"] for project in portfolio)
        / len(portfolio)
        / 10
    )

    return round(
        (0.4 * subtopic_diversity)
        + (0.4 * institution_diversity)
        + (0.2 * average_risk),
        2,
    )


def recommend_greedy(projects, max_budget):
    """Build a portfolio by repeatedly adding the highest-scoring affordable project.

    This is fast and explainable, but it can get stuck with locally good choices.
    """
    portfolio = []
    remaining_budget = max_budget
    available = [
        project
        for project in projects
        if project["budget_eur"] <= max_budget
    ]

    while available:
        scored = []

        for project in available:
            if project["budget_eur"] <= remaining_budget:
                score = project_score(project, portfolio)
                scored.append((score, project))

        if not scored:
            break

        scored.sort(key=lambda item: item[0], reverse=True)
        best_project = scored[0][1]

        portfolio.append(best_project)
        remaining_budget -= best_project["budget_eur"]
        available.remove(best_project)

    return portfolio


def recommend_genetic(projects, max_budget, generations=500, population_size=100):
    """Evolve a population of random portfolios towards higher portfolio fitness.

    This explores more combinations than greedy selection, but takes longer and is
    not guaranteed to return the same result every time.
    """
    def random_portfolio():
        """Create one random valid portfolio within the budget limit."""
        shuffled = random.sample(projects, len(projects))
        portfolio = []
        budget = 0

        for project in shuffled:
            if budget + project["budget_eur"] <= max_budget:
                portfolio.append(project)
                budget += project["budget_eur"]

        return portfolio

    def crossover(parent_a, parent_b):
        """Combine projects from two parent portfolios into one valid child."""
        combined = list({
            project["id"]: project
            for project in parent_a + parent_b
        }.values())
        random.shuffle(combined)

        child = []
        budget = 0

        for project in combined:
            if budget + project["budget_eur"] <= max_budget:
                child.append(project)
                budget += project["budget_eur"]

        return child

    def mutate(portfolio):
        """Occasionally add a random project, then trim back to the budget limit."""
        if random.random() >= 0.1:
            return portfolio

        available = [
            project
            for project in projects
            if project not in portfolio
        ]

        if not available:
            return portfolio

        mutated = portfolio.copy()
        mutated.append(random.choice(available))

        while sum(project["budget_eur"] for project in mutated) > max_budget:
            mutated.pop(random.randint(0, len(mutated) - 1))

        return mutated

    population = [
        random_portfolio()
        for _ in range(population_size)
    ]

    for _ in range(generations):
        # Keep the best half, then refill the population with children of strong parents.
        population.sort(key=portfolio_fitness, reverse=True)
        population = population[:population_size // 2]

        while len(population) < population_size:
            parent_a, parent_b = random.sample(population[:10], 2)
            child = crossover(parent_a, parent_b)
            population.append(mutate(child))

    return max(population, key=portfolio_fitness)