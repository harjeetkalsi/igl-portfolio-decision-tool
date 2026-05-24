// -----------------------------------------------------------------------------
// Constants
// -----------------------------------------------------------------------------

const defaultMaxBudget = 4000000;

let maxBudget = Number(localStorage.getItem("maxBudget")) || defaultMaxBudget;

let openaiApiKey = "";

const chartColours = [
  "#2563eb",
  "#16a34a",
  "#f59e0b",
  "#dc2626",
  "#7c3aed",
  "#0891b2",
  "#db2777",
  "#65a30d",
  "#ea580c",
  "#475569",
];

// -----------------------------------------------------------------------------
// Formatting helpers
// -----------------------------------------------------------------------------

const formatCurrency = (amount) => {
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(amount);
};

// -----------------------------------------------------------------------------
// URL state helpers
// -----------------------------------------------------------------------------

const getUrlPortfolioIds = () => {
  const params = new URLSearchParams(window.location.search);

  return {
    a: params.get("a") ? params.get("a").split(",").filter(Boolean) : [],
    b: params.get("b") ? params.get("b").split(",").filter(Boolean) : [],
  };
};

const buildStateQuery = (portfolioAIds, portfolioBIds) => {
  const params = new URLSearchParams();

  if (portfolioAIds.length > 0) {
    params.set("a", portfolioAIds.join(","));
  }

  if (portfolioBIds.length > 0) {
    params.set("b", portfolioBIds.join(","));
  }

  const queryString = params.toString();
  return queryString ? `?${queryString}` : "";
};

const updateBrowserUrl = (portfolioAIds, portfolioBIds) => {
  if (!document.querySelector(".portfolio-checkbox")) {
    return;
  }

  const stateQuery = buildStateQuery(portfolioAIds, portfolioBIds);
  const newUrl = `${window.location.pathname}${stateQuery}`;

  window.history.replaceState({}, "", newUrl);
};

// -----------------------------------------------------------------------------
// Portfolio checkbox state
// -----------------------------------------------------------------------------

const syncCheckboxesFromUrl = () => {
  const selectedIds = getUrlPortfolioIds();

  document.querySelectorAll(".portfolio-checkbox").forEach((checkbox) => {
    const portfolio = checkbox.dataset.portfolio;
    const projectId = checkbox.dataset.projectId;

    checkbox.checked = selectedIds[portfolio].includes(projectId);
  });
};

const getSelectedProjects = (portfolio) => {
  const checkedBoxes = document.querySelectorAll(
    `.portfolio-checkbox[data-portfolio="${portfolio}"]:checked`
  );

  return Array.from(checkedBoxes).map((checkbox) => ({
    id: checkbox.dataset.projectId,
    budget: Number(checkbox.dataset.budget),
  }));
};

const setPortfolioSelection = (portfolio, projectIds) => {
  const selectedIds = new Set(projectIds);

  document
    .querySelectorAll(`.portfolio-checkbox[data-portfolio="${portfolio}"]`)
    .forEach((checkbox) => {
      checkbox.checked = selectedIds.has(checkbox.dataset.projectId);
    });
};

const updatePortfolioSummary = (portfolio) => {
  const selectedProjects = getSelectedProjects(portfolio);
  const totalBudget = selectedProjects.reduce(
    (sum, project) => sum + project.budget,
    0
  );

  const totalElement = document.querySelector(`#portfolio-${portfolio}-total`);
  const countElement = document.querySelector(`#portfolio-${portfolio}-count`);
  const cardElement = document.querySelector(
    `[data-budget-card="${portfolio}"]`
  );

  if (!totalElement || !countElement || !cardElement) {
    return selectedProjects.map((project) => project.id);
  }

  totalElement.textContent = formatCurrency(totalBudget);
  countElement.textContent = selectedProjects.length;
  cardElement.classList.toggle("is-over-budget", totalBudget > maxBudget);

  return selectedProjects.map((project) => project.id);
};

const updateDashboard = () => {
  const hasCheckboxes = document.querySelector(".portfolio-checkbox");

  if (hasCheckboxes) {
    const portfolioAIds = updatePortfolioSummary("a");
    const portfolioBIds = updatePortfolioSummary("b");

    updateLinks(portfolioAIds, portfolioBIds);
    updateBrowserUrl(portfolioAIds, portfolioBIds);
    return;
  }

  const selectedIds = getUrlPortfolioIds();

  updateLinks(selectedIds.a, selectedIds.b);
};

// -----------------------------------------------------------------------------
// Navigation and action links
// -----------------------------------------------------------------------------

const updateLinks = (portfolioAIds, portfolioBIds) => {
  const stateQuery = buildStateQuery(portfolioAIds, portfolioBIds);

  const portfolioALink = document.querySelector("#portfolio-a-link");
  const portfolioBLink = document.querySelector("#portfolio-b-link");
  const compareLink = document.querySelector("#compare-link");
  const readmeNavLink = document.querySelector('[data-nav-link="readme"]');


  if (portfolioALink) {
    portfolioALink.href = `/portfolio/a${stateQuery}`;
  }

  if (portfolioBLink) {
    portfolioBLink.href = `/portfolio/b${stateQuery}`;
  }

  if (compareLink) {
    compareLink.href = `/compare${stateQuery}`;
  }

  if (readmeNavLink) {
  readmeNavLink.href = `/readme${stateQuery}`;
}

  const projectsNavLink = document.querySelector('[data-nav-link="projects"]');
  const portfolioANavLink = document.querySelector('[data-nav-link="portfolio-a"]');
  const portfolioBNavLink = document.querySelector('[data-nav-link="portfolio-b"]');
  const compareNavLink = document.querySelector('[data-nav-link="compare"]');

  if (projectsNavLink) {
    projectsNavLink.href = `/${stateQuery}`;
  }

  if (portfolioANavLink) {
    portfolioANavLink.href = `/portfolio/a${stateQuery}`;
  }

  if (portfolioBNavLink) {
    portfolioBNavLink.href = `/portfolio/b${stateQuery}`;
  }

  if (compareNavLink) {
    compareNavLink.href = `/compare${stateQuery}`;
  }
};

// -----------------------------------------------------------------------------
// Recommendation algorithm UI
// -----------------------------------------------------------------------------

const setFitnessScore = (portfolio, fitness) => {
  const scoreElement = document.querySelector(`#portfolio-${portfolio}-fitness`);

  if (!scoreElement) {
    return;
  }

  scoreElement.textContent = `Portfolio fitness: ${fitness.toFixed(2)}`;
};

const setRecommendLoading = (button, isLoading) => {
  const algorithm = button.dataset.recommendAlgorithm;

  if (isLoading) {
    button.disabled = true;
    button.dataset.originalText = button.textContent;
    button.textContent = algorithm === "genetic" ? "Optimising..." : "Recommending...";
    return;
  }

  button.disabled = false;
  button.textContent = button.dataset.originalText;
};

const runRecommendation = async (button) => {
  const algorithm = button.dataset.recommendAlgorithm;
  const target = button.dataset.recommendTarget;

  setRecommendLoading(button, true);

  try {
    const response = await fetch(`/recommend/${algorithm}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        target,
        max_budget: maxBudget,
      }),
    });

    if (!response.ok) {
      throw new Error("Recommendation request failed");
    }

    const result = await response.json();

    setPortfolioSelection(result.portfolio, result.projects);
    setFitnessScore(result.portfolio, result.fitness);
    updateDashboard();
  } catch (error) {
    const scoreElement = document.querySelector(`#portfolio-${target}-fitness`);

    if (scoreElement) {
      scoreElement.textContent = "Recommendation failed. Please try again.";
    }
  } finally {
    setRecommendLoading(button, false);
  }
};

// -----------------------------------------------------------------------------
// Diversity charts
// -----------------------------------------------------------------------------

const initialiseDiversityCharts = () => {
  if (!window.Chart) {
    return;
  }

  document.querySelectorAll(".diversity-chart").forEach((canvas) => {
    const items = JSON.parse(canvas.dataset.chartItems || "[]");

    if (items.length === 0) {
      return;
    }

    new Chart(canvas, {
      type: "pie",
      data: {
        labels: items.map((item) => item.label),
        datasets: [
          {
            data: items.map((item) => item.value),
            backgroundColor: items.map(
              (_, index) => chartColours[index % chartColours.length]
            ),
            borderColor: "#ffffff",
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              boxWidth: 12,
              font: {
                size: 11,
              },
            },
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                const item = items[context.dataIndex];
                return `${item.label}: ${formatCurrency(item.value)} (${item.percentage}%)`;
              },
            },
          },
        },
      },
    });
  });
};

// -----------------------------------------------------------------------------
// Share link button
// -----------------------------------------------------------------------------

const initialiseShareLinkButton = () => {
  const copyShareLinkButton = document.querySelector("#copy-share-link");

  if (!copyShareLinkButton) {
    return;
  }

  copyShareLinkButton.addEventListener("click", async () => {
    const shareUrl = window.location.href;

    try {
      await navigator.clipboard.writeText(shareUrl);
      copyShareLinkButton.textContent = "Copied";
    } catch (error) {
      copyShareLinkButton.textContent = "Copy failed";
    }

    window.setTimeout(() => {
      copyShareLinkButton.textContent = "Copy shareable link";
    }, 2000);
  });
};

// -----------------------------------------------------------------------------
// Page initialisation
// -----------------------------------------------------------------------------

if (document.querySelector(".portfolio-checkbox")) {
  syncCheckboxesFromUrl();
}

updateDashboard();

document.querySelectorAll(".portfolio-checkbox").forEach((checkbox) => {
  checkbox.addEventListener("change", updateDashboard);
});

document.querySelectorAll("[data-recommend-algorithm]").forEach((button) => {
  button.addEventListener("click", () => runRecommendation(button));
});

// -----------------------------------------------------------------------------
// Settings panel
// -----------------------------------------------------------------------------

const updateBudgetSettingDisplay = () => {
  const budgetInput = document.querySelector("#max-budget-input");
  const budgetDisplay = document.querySelector("#max-budget-display");

  if (budgetInput) {
    budgetInput.value = maxBudget;
  }

  if (budgetDisplay) {
    budgetDisplay.textContent = formatCurrency(maxBudget);
  }
};

const openSettingsPanel = () => {
  const panel = document.querySelector("#settings-panel");
  const overlay = document.querySelector("#settings-overlay");

  if (!panel || !overlay) {
    return;
  }

  overlay.hidden = false;
  panel.classList.add("is-open");
  overlay.classList.add("is-open");
  panel.setAttribute("aria-hidden", "false");
};

const closeSettingsPanel = () => {
  const panel = document.querySelector("#settings-panel");
  const overlay = document.querySelector("#settings-overlay");

  if (!panel || !overlay) {
    return;
  }

  panel.classList.remove("is-open");
  overlay.classList.remove("is-open");
  panel.setAttribute("aria-hidden", "true");

  window.setTimeout(() => {
    overlay.hidden = true;
  }, 180);
};

const initialiseSettingsPanel = () => {
  const openButton = document.querySelector("#open-settings-panel");
  const closeButton = document.querySelector("#close-settings-panel");
  const overlay = document.querySelector("#settings-overlay");
  const budgetInput = document.querySelector("#max-budget-input");
  const apiKeyInput = document.querySelector("#openai-api-key-input");

  updateBudgetSettingDisplay();

  if (openButton) {
    openButton.addEventListener("click", openSettingsPanel);
  }

  if (closeButton) {
    closeButton.addEventListener("click", closeSettingsPanel);
  }

  if (overlay) {
    overlay.addEventListener("click", closeSettingsPanel);
  }

  if (apiKeyInput) {
  apiKeyInput.addEventListener("input", () => {
    openaiApiKey = apiKeyInput.value.trim();
  });
}

  if (budgetInput) {
    budgetInput.addEventListener("input", () => {
      const nextBudget = Number(budgetInput.value);

      if (!Number.isFinite(nextBudget) || nextBudget < 0) {
        return;
      }

      maxBudget = nextBudget;
      localStorage.setItem("maxBudget", String(maxBudget));

      updateBudgetSettingDisplay();
      updateDashboard();
    });
  }
};

// -----------------------------------------------------------------------------
// AI summary
// -----------------------------------------------------------------------------

const showAiSummaryPanel = (message) => {
  const panel = document.querySelector("#ai-summary-panel");
  const text = document.querySelector("#ai-summary-text");

  if (!panel || !text) {
    return;
  }

  panel.hidden = false;
  text.textContent = message;
};

const setAiSummaryLoading = (isLoading) => {
  const generateButton = document.querySelector("#generate-ai-summary");
  const regenerateButton = document.querySelector("#regenerate-ai-summary");

  [generateButton, regenerateButton].forEach((button) => {
    if (!button) {
      return;
    }

    button.disabled = isLoading;
  });

  if (generateButton) {
    generateButton.textContent = isLoading
      ? "Analysing portfolios..."
      : "✨ Generate AI Summary";
  }
};

const generateAiSummary = async () => {
  if (!openaiApiKey) {
    showAiSummaryPanel("Please add your OpenAI API key in Settings to use this feature.");
    openSettingsPanel();
    return;
  }

  const selectedIds = getUrlPortfolioIds();

  setAiSummaryLoading(true);
  showAiSummaryPanel("Analysing portfolios...");

  try {
    const response = await fetch("/ai-summary", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": openaiApiKey,
      },
      body: JSON.stringify({
        a: selectedIds.a.join(","),
        b: selectedIds.b.join(","),
        max_budget: maxBudget,
      }),
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "Summary request failed");
    }

    showAiSummaryPanel(result.summary);
  } catch (error) {
    showAiSummaryPanel("Summary could not be generated. Please check your API key and try again.");
  } finally {
    setAiSummaryLoading(false);
  }
};

const initialiseAiSummary = () => {
  const generateButton = document.querySelector("#generate-ai-summary");
  const regenerateButton = document.querySelector("#regenerate-ai-summary");

  if (generateButton) {
    generateButton.addEventListener("click", generateAiSummary);
  }

  if (regenerateButton) {
    regenerateButton.addEventListener("click", generateAiSummary);
  }
};

initialiseDiversityCharts();
initialiseShareLinkButton();
initialiseSettingsPanel();
initialiseAiSummary();
