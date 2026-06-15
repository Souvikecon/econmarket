const state = {
  candidates: [],
  country: "all",
  institution: "all",
  topic: "all",
  placementType: "all",
  query: "",
};

const elements = {
  grid: document.querySelector("#paper-grid"),
  count: document.querySelector("#result-count"),
  updated: document.querySelector("#updated-label"),
  search: document.querySelector("#search-input"),
  institution: document.querySelector("#institution-filter"),
  topic: document.querySelector("#topic-filter"),
  placementType: document.querySelector("#placement-type-filter"),
  empty: document.querySelector("#empty-state"),
  clear: document.querySelector("#clear-filters"),
};

function escapeHtml(value = "") {
  const node = document.createElement("span");
  node.textContent = value;
  return node.innerHTML;
}

function candidateCard(candidate) {
  const fields = candidate.research_topics
    .map((field) => `<span class="field-tag">${escapeHtml(field)}</span>`)
    .join("");
  const rankLabel = candidate.country === "US" ? "US rank" : "UK rank";
  const placement = candidate.placement_status === "confirmed"
    ? escapeHtml(candidate.placement_destination)
    : "Not yet announced";
  return `
    <article class="paper-card">
      <div class="card-top">
        <span class="institution">${escapeHtml(candidate.institution)}</span>
        <span class="rank">${rankLabel} #${candidate.rank}</span>
      </div>
      <h3>${escapeHtml(candidate.paper_title)}</h3>
      <p class="candidate-name">${escapeHtml(candidate.name)}</p>
      <div class="field-list">${fields}</div>
      <details class="paper-details">
        <summary>Abstract summary <span aria-hidden="true"></span></summary>
        <div class="abstract-content">
          <p>${escapeHtml(candidate.abstract_summary)}</p>
          <p class="abstract-placement"><strong>Placement:</strong> <span>${placement}</span></p>
          <a href="${escapeHtml(candidate.abstract_source_url)}" target="_blank" rel="noopener">Open full paper <span>&nearr;</span></a>
        </div>
      </details>
      <div class="card-links">
        <a class="paper-link" href="${escapeHtml(candidate.paper_url)}" target="_blank" rel="noopener">Read paper <span>&nearr;</span></a>
        <a class="profile-link" href="${escapeHtml(candidate.profile_url)}" target="_blank" rel="noopener">Candidate profile</a>
      </div>
    </article>`;
}

function render() {
  const query = state.query.trim().toLowerCase();
  const visible = state.candidates.filter((candidate) => {
    const matchesCountry = state.country === "all" || candidate.country === state.country;
    const matchesInstitution = state.institution === "all" || candidate.institution === state.institution;
    const matchesTopic = state.topic === "all" || candidate.research_topics.includes(state.topic);
    const matchesPlacement = state.placementType === "all" || candidate.placement_types.includes(state.placementType);
    const haystack = [
      candidate.name,
      candidate.paper_title,
      candidate.institution,
      candidate.abstract_summary,
      candidate.placement_destination,
      ...candidate.fields,
      ...candidate.research_topics,
      ...candidate.placement_types,
    ]
      .join(" ")
      .toLowerCase();
    return matchesCountry && matchesInstitution && matchesTopic && matchesPlacement && (!query || haystack.includes(query));
  });

  elements.grid.innerHTML = visible.map(candidateCard).join("");
  elements.count.textContent = String(visible.length);
  elements.empty.hidden = visible.length > 0;
}

function resetFilters() {
  state.country = "all";
  state.institution = "all";
  state.topic = "all";
  state.placementType = "all";
  state.query = "";
  elements.search.value = "";
  elements.institution.value = "all";
  elements.topic.value = "all";
  elements.placementType.value = "all";
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

elements.topic.addEventListener("change", (event) => {
  state.topic = event.target.value;
  render();
});

elements.placementType.addEventListener("change", (event) => {
  state.placementType = event.target.value;
  render();
});

elements.clear.addEventListener("click", resetFilters);

fetch("data/candidate_details.json", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) throw new Error(`Data request failed: ${response.status}`);
    return response.json();
  })
  .then((data) => {
    state.candidates = data.candidates.sort((a, b) => a.rank - b.rank || a.institution.localeCompare(b.institution) || a.name.localeCompare(b.name));
    const institutions = [...new Set(state.candidates.map((candidate) => candidate.institution))].sort();
    const topics = [...new Set(state.candidates.flatMap((candidate) => candidate.research_topics))].sort();
    const placementTypes = [...new Set(state.candidates.flatMap((candidate) => candidate.placement_types))].sort();
    elements.institution.insertAdjacentHTML(
      "beforeend",
      institutions.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("")
    );
    elements.topic.insertAdjacentHTML(
      "beforeend",
      topics.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("")
    );
    elements.placementType.insertAdjacentHTML(
      "beforeend",
      placementTypes.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("")
    );
    const updated = new Date(data.generated_at);
    const updatedLabel = updated.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
    elements.updated.textContent = `Updated ${updatedLabel} | ${data.total_candidates} candidates | ${data.summaries_available} abstract summaries`;
    render();
  })
  .catch((error) => {
    console.error(error);
    elements.updated.textContent = "Latest data could not be loaded";
    elements.empty.hidden = false;
  });
