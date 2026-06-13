const state = {
  candidates: [],
  country: "all",
  institution: "all",
  query: "",
};

const elements = {
  grid: document.querySelector("#paper-grid"),
  count: document.querySelector("#result-count"),
  updated: document.querySelector("#updated-label"),
  search: document.querySelector("#search-input"),
  institution: document.querySelector("#institution-filter"),
  empty: document.querySelector("#empty-state"),
  clear: document.querySelector("#clear-filters"),
};

function escapeHtml(value = "") {
  const node = document.createElement("span");
  node.textContent = value;
  return node.innerHTML;
}

function candidateCard(candidate) {
  const fields = candidate.fields
    .map((field) => `<span class="field-tag">${escapeHtml(field)}</span>`)
    .join("");
  const rankLabel = candidate.country === "US" ? "US rank" : "UK rank";
  return `
    <article class="paper-card">
      <div class="card-top">
        <span class="institution">${escapeHtml(candidate.institution)}</span>
        <span class="rank">${rankLabel} #${candidate.rank}</span>
      </div>
      <h3>${escapeHtml(candidate.paper_title)}</h3>
      <p class="candidate-name">${escapeHtml(candidate.name)}</p>
      <div class="field-list">${fields}</div>
      <div class="card-links">
        <a class="paper-link" href="${escapeHtml(candidate.paper_url)}" target="_blank" rel="noopener">Read paper <span>↗</span></a>
        <a class="profile-link" href="${escapeHtml(candidate.profile_url)}" target="_blank" rel="noopener">Candidate profile</a>
      </div>
    </article>`;
}

function render() {
  const query = state.query.trim().toLowerCase();
  const visible = state.candidates.filter((candidate) => {
    const matchesCountry = state.country === "all" || candidate.country === state.country;
    const matchesInstitution = state.institution === "all" || candidate.institution === state.institution;
    const haystack = [candidate.name, candidate.paper_title, candidate.institution, ...candidate.fields]
      .join(" ")
      .toLowerCase();
    return matchesCountry && matchesInstitution && (!query || haystack.includes(query));
  });

  elements.grid.innerHTML = visible.map(candidateCard).join("");
  elements.count.textContent = String(visible.length);
  elements.empty.hidden = visible.length > 0;
}

function resetFilters() {
  state.country = "all";
  state.institution = "all";
  state.query = "";
  elements.search.value = "";
  elements.institution.value = "all";
  document.querySelectorAll("[data-country]").forEach((button) => {
    button.classList.toggle("active", button.dataset.country === "all");
  });
  render();
}

document.querySelectorAll("[data-country]").forEach((button) => {
  button.addEventListener("click", () => {
    state.country = button.dataset.country;
    document.querySelectorAll("[data-country]").forEach((item) => item.classList.toggle("active", item === button));
    render();
  });
});

elements.search.addEventListener("input", (event) => {
  state.query = event.target.value;
  render();
});

elements.institution.addEventListener("change", (event) => {
  state.institution = event.target.value;
  render();
});

elements.clear.addEventListener("click", resetFilters);

fetch("data/candidates.json", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) throw new Error(`Data request failed: ${response.status}`);
    return response.json();
  })
  .then((data) => {
    state.candidates = data.candidates.sort((a, b) => a.rank - b.rank || a.institution.localeCompare(b.institution) || a.name.localeCompare(b.name));
    const institutions = [...new Set(state.candidates.map((candidate) => candidate.institution))].sort();
    elements.institution.insertAdjacentHTML(
      "beforeend",
      institutions.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("")
    );
    const updated = new Date(data.generated_at);
    const rankingPeriod = data.ranking_period ? ` · RePEc ${data.ranking_period}` : "";
    elements.updated.textContent = `Updated ${updated.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })} · ${data.departments_monitored} departments monitored${rankingPeriod}`;
    render();
  })
  .catch((error) => {
    console.error(error);
    elements.updated.textContent = "Latest data could not be loaded";
    elements.empty.hidden = false;
  });
