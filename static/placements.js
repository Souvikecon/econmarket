const placementState = {
  placements: [],
  status: "all",
  institution: "all",
  query: "",
};

const placementElements = {
  grid: document.querySelector("#placement-grid"),
  count: document.querySelector("#placement-count"),
  summary: document.querySelector("#placement-summary"),
  search: document.querySelector("#placement-search"),
  institution: document.querySelector("#placement-institution-filter"),
  empty: document.querySelector("#placement-empty-state"),
  clear: document.querySelector("#clear-placement-filters"),
};

function escapePlacementHtml(value = "") {
  const node = document.createElement("span");
  node.textContent = value;
  return node.innerHTML;
}

function placementCard(item) {
  const confirmed = item.status === "confirmed";
  const statusLabel = confirmed ? "Confirmed" : "Not yet announced";
  const destination = confirmed ? item.destination : "Placement not yet public";
  const position = item.position
    ? `<p class="placement-position">${escapePlacementHtml(item.position)}</p>`
    : "";
  const timing = item.timing
    ? `<p class="placement-timing">${escapePlacementHtml(item.timing)}</p>`
    : "";
  const source = confirmed
    ? `<a class="source-link" href="${escapePlacementHtml(item.source_url)}" target="_blank" rel="noopener">${escapePlacementHtml(item.source_label)} <span>&nearr;</span></a>`
    : "";

  return `
    <article class="placement-card${confirmed ? "" : " pending-card"}">
      <div class="card-top">
        <span class="institution">${escapePlacementHtml(item.institution)}</span>
        <span class="placement-status ${item.status}">${statusLabel}</span>
      </div>
      <h3>${escapePlacementHtml(item.name)}</h3>
      <div class="placement-detail">
        <span class="placement-label">Placement</span>
        <strong class="placement-destination">${escapePlacementHtml(destination)}</strong>
        ${position}
        ${timing}
      </div>
      <div class="placement-links">
        ${source}
        <a class="profile-link" href="${escapePlacementHtml(item.profile_url)}" target="_blank" rel="noopener">Candidate profile</a>
        <a class="profile-link" href="${escapePlacementHtml(item.paper_url)}" target="_blank" rel="noopener">Paper</a>
      </div>
    </article>`;
}

function renderPlacements() {
  const query = placementState.query.trim().toLowerCase();
  const visible = placementState.placements.filter((item) => {
    const matchesStatus = placementState.status === "all" || item.status === placementState.status;
    const matchesInstitution = placementState.institution === "all" || item.institution === placementState.institution;
    const haystack = [item.name, item.institution, item.destination, item.position, item.timing, ...item.fields]
      .join(" ")
      .toLowerCase();
    return matchesStatus && matchesInstitution && (!query || haystack.includes(query));
  });

  placementElements.grid.innerHTML = visible.map(placementCard).join("");
  placementElements.count.textContent = String(visible.length);
  placementElements.empty.hidden = visible.length > 0;
}

function resetPlacementFilters() {
  placementState.status = "all";
  placementState.institution = "all";
  placementState.query = "";
  placementElements.search.value = "";
  placementElements.institution.value = "all";
  document.querySelectorAll("[data-status]").forEach((button) => {
    button.classList.toggle("active", button.dataset.status === "all");
  });
  renderPlacements();
}

document.querySelectorAll("[data-status]").forEach((button) => {
  button.addEventListener("click", () => {
    placementState.status = button.dataset.status;
    document.querySelectorAll("[data-status]").forEach((item) => item.classList.toggle("active", item === button));
    renderPlacements();
  });
});

placementElements.search.addEventListener("input", (event) => {
  placementState.query = event.target.value;
  renderPlacements();
});

placementElements.institution.addEventListener("change", (event) => {
  placementState.institution = event.target.value;
  renderPlacements();
});

placementElements.clear.addEventListener("click", resetPlacementFilters);

fetch("data/placements.json", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) throw new Error(`Placement data request failed: ${response.status}`);
    return response.json();
  })
  .then((data) => {
    placementState.placements = data.placements.sort((a, b) => {
      if (a.status !== b.status) return a.status === "confirmed" ? -1 : 1;
      return a.rank - b.rank || a.institution.localeCompare(b.institution) || a.name.localeCompare(b.name);
    });
    const institutions = [...new Set(placementState.placements.map((item) => item.institution))].sort();
    placementElements.institution.insertAdjacentHTML(
      "beforeend",
      institutions.map((name) => `<option value="${escapePlacementHtml(name)}">${escapePlacementHtml(name)}</option>`).join("")
    );
    const reviewed = new Date(`${data.reviewed_at}T00:00:00`);
    const reviewedLabel = reviewed.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
    placementElements.summary.textContent = `${data.confirmed_count} confirmed | ${data.pending_count} not yet announced | Reviewed ${reviewedLabel}`;
    renderPlacements();
  })
  .catch((error) => {
    console.error(error);
    placementElements.summary.textContent = "Placement data could not be loaded";
    placementElements.empty.hidden = false;
  });
