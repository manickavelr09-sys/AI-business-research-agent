const form = document.querySelector("#research-form");
const pdfButton = document.querySelector("#download-pdf");
const pdfButtonSecondary = document.querySelector("#download-pdf-secondary");
const results = document.querySelector("#results");
const events = document.querySelector("#events");
const runButton = form.querySelector('button[type="submit"]');
let lastReport = null;
let activeController = null;
const renderedCards = new Map();
const readinessStatus = document.querySelector("#readiness-status");
const readinessGrid = document.querySelector("#readiness-grid");
const readinessWarnings = document.querySelector("#readiness-warnings");
const summary = {
  businesses: document.querySelector("#businesses"),
  verified: document.querySelector("#verified"),
  duplicates: document.querySelector("#duplicates"),
  duration: document.querySelector("#duration"),
};
const quality = {
  phone: document.querySelector("#quality-phone"),
  address: document.querySelector("#quality-address"),
  website: document.querySelector("#quality-website"),
  rating: document.querySelector("#quality-rating"),
  hours: document.querySelector("#quality-hours"),
  services: document.querySelector("#quality-services"),
};
let currentRunId = null;
function logEvent(event) {
  const line = document.createElement("div");
  line.textContent = `${new Date().toLocaleTimeString()} ${event.event}`;
  events.prepend(line);
  while (events.children.length > 120) {
    events.lastElementChild?.remove();
  }
}

async function loadReadiness() {
  if (!readinessGrid || !readinessStatus) return;
  try {
    const response = await fetch("/readiness");
    if (!response.ok) throw new Error("readiness failed");
    const payload = await response.json();
    renderReadiness(payload);
  } catch (error) {
    readinessStatus.textContent = "Unavailable";
    readinessStatus.className = "status-bad";
    readinessGrid.innerHTML = "";
    readinessWarnings.textContent = "Readiness check could not be loaded.";
  }
}

function renderReadiness(payload) {
  readinessStatus.textContent = payload.status || "unknown";
  readinessStatus.className = payload.status === "ready" ? "status-ok" : "status-warn";
  const providers = payload.providers || {};
  const rows = [
    ["Maps", providers.maps],
    ["Search", providers.search],
    ["Intelligence", providers.intelligence],
    ["Storage", providers.storage],
  ];
  readinessGrid.innerHTML = rows
    .map(([label, values]) => readinessGroup(label, values || {}))
    .join("");
  const warnings = payload.warnings || [];
  readinessWarnings.innerHTML = warnings.length
    ? warnings.map((warning) => `<div>${escapeHtml(warning)}</div>`).join("")
    : "<div>All core providers are configured.</div>";
}

function readinessGroup(label, values) {
  const items = Object.entries(values)
    .map(([name, enabled]) => `<span class="${enabled ? "pill-on" : "pill-off"}">${escapeHtml(name.replaceAll("_", " "))}</span>`)
    .join("");
  return `<div><strong>${escapeHtml(label)}</strong><div class="provider-pills">${items}</div></div>`;
}

function field(label, verified, fallback = "") {
  const value = verified?.value || fallback || "";
  if (!value || (Array.isArray(value) && value.length === 0)) return "";
  const display = Array.isArray(value) ? value.join(", ") : value;
  const level = verified?.verified_level ? `<span class="badge">${verified.verified_level}</span>` : "";
  return `<div class="field"><div class="label">${label}${level}</div><div class="value">${escapeHtml(display)}</div></div>`;
}

function renderBusiness(business) {
  const key = businessKey(business);
  const card = document.createElement("article");
  card.className = "result-card";
  card.dataset.businessKey = key;
  const verification = business.verification || {};
  const conflicts = Object.keys(business.conflicts || {});
  card.innerHTML = `
    <h2>${escapeHtml(business.business_name || "Unnamed business")}</h2>
    <div class="fields">
      ${field("Address", verification.address, business.address)}
      ${field("Phone", verification.phone, business.phone)}
      ${field("Email", verification.email, business.email)}
      ${field("Website", verification.website, business.website)}
      ${field("Hours", verification.working_hours, business.working_hours)}
      ${field("Rating", verification.rating, business.rating)}
      ${field("Reviews", verification.review_count, business.review_count)}
      ${field("License", verification.license_information, business.license_information)}
      ${field("Services", verification.services, business.services)}
      ${field("Certifications", verification.certifications, business.certifications)}
      <div class="field"><div class="label">Reliability</div><div class="value">${business.reliability_score}</div></div>
      <div class="field"><div class="label">Conflicts</div><div class="value conflict">${conflicts.join(", ") || "None"}</div></div>
    </div>
  `;
  const existing = renderedCards.get(key);
  if (existing) {
    existing.replaceWith(card);
  } else {
    results.prepend(card);
  }
  renderedCards.set(key, card);
}

function renderFinalBusinesses(businesses) {
  results.innerHTML = "";
  renderedCards.clear();
  const reportSummary = lastReport?.research_summary;
  if (reportSummary) {
    results.append(renderResearchSummary(reportSummary));
  }
  if (!businesses.length) {
    if (!reportSummary) showMessage("No businesses found for this search.");
    return;
  }
  businesses.forEach((business) => renderBusiness(business));
}

function renderResearchSummary(summary) {
  const card = document.createElement("article");
  card.className = "result-card summary-card";
  const steps = (summary.agent_steps || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  const limitations = (summary.limitations || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  const strategy = Array.isArray(summary.source_strategy) ? summary.source_strategy.join(", ") : "";
  card.innerHTML = `
    <h2>Research Summary</h2>
    <p>${escapeHtml(summary.summary || "")}</p>
    <div class="fields">
      <div class="field"><div class="label">RAG Evidence Chunks</div><div class="value">${summary.retrieved_evidence_chunks || 0}</div></div>
      <div class="field"><div class="label">LLM Used</div><div class="value">${summary.llm_used ? "Yes" : "No"}</div></div>
      <div class="field"><div class="label">Source Strategy</div><div class="value">${escapeHtml(strategy || "Public web evidence")}</div></div>
      <div class="field"><div class="label">Agent Steps</div><div class="value"><ul>${steps}</ul></div></div>
      <div class="field"><div class="label">Limitations</div><div class="value"><ul>${limitations || "<li>None flagged</li>"}</ul></div></div>
    </div>
  `;
  return card;
}

function showMessage(message) {
  results.innerHTML = `<article class="result-card"><h2>${escapeHtml(message)}</h2></article>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function businessKey(business) {
  const verification = business.verification || {};
  const name = normalizeKey(business.business_name);
  const phone = normalizeKey(business.phone || verification.phone?.value);
  const address = normalizeKey(business.address || verification.address?.value);
  if (phone) return `phone-${phone}`;
  if (name && address) return `name-address-${name}-${address}`;
  return `name-${name || crypto.randomUUID()}`;
}

function normalizeKey(value = "") {
  return String(value).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (activeController) activeController.abort();
  activeController = new AbortController();
  const controller = activeController;
  lastReport = null;
  renderedCards.clear();
  pdfButton.disabled = true;
  pdfButtonSecondary.disabled = true;
  runButton.disabled = true;
  runButton.textContent = "Running";
  showMessage("Searching public sources...");
  events.innerHTML = "";
  summary.businesses.textContent = "0";
  summary.verified.textContent = "0";
  summary.duplicates.textContent = "0";
  summary.duration.textContent = "-";
  Object.values(quality).forEach((node) => {
    node.textContent = "0%";
  });

  const params = new URLSearchParams(new FormData(form));
  let response;
  try {
    response = await fetch(`/research/stream?${params.toString()}`, { signal: controller.signal });
  } catch (error) {
    if (error.name === "AbortError") return;
    showMessage("Search failed. Check that the local server is running.");
    resetRunButton();
    return;
  }
  if (!response.ok || !response.body) {
    showMessage(`Search failed with status ${response.status}.`);
    resetRunButton();
    return;
  }
  try {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.trim()) continue;
        let payload;
        try {
          payload = JSON.parse(line);
        } catch (error) {
          logEvent({ event: "stream_parse_error" });
          continue;
        }
        logEvent(payload);
        if (payload.event === "discovery_complete" && payload.candidate_urls === 0) {
          showMessage("No candidate businesses found. Try a more specific location, such as Birmingham AL.");
        }
        if (payload.event === "extraction_started") {
          runButton.textContent = "Finalizing";
        }
        if (payload.event === "extraction_timeout") {
          logEvent({ event: "finalizing_partial_report" });
        }
        if (payload.event === "business_discovered" || payload.event === "business_enriched") {
          if (results.textContent.includes("Searching public sources")) results.innerHTML = "";
          renderBusiness(payload.business);
        }
        if (payload.event === "completed") {
          currentRunId = payload.run_id;

          console.log("RUN ID:", currentRunId);
          lastReport = payload.report;
          pdfButton.disabled = false;
          pdfButtonSecondary.disabled = false;
          const searchSummary = payload.report.search_summary;
          const dataQuality = payload.report.data_quality_summary || {};
          summary.businesses.textContent = searchSummary.businesses_found;
          summary.verified.textContent = searchSummary.businesses_verified;
          summary.duplicates.textContent = searchSummary.duplicate_records_removed;
          summary.duration.textContent = searchSummary.research_duration;
          quality.phone.textContent = dataQuality.records_with_phone_number || "0%";
          quality.address.textContent = dataQuality.records_with_address || "0%";
          quality.website.textContent = dataQuality.records_with_website || "0%";
          quality.rating.textContent = dataQuality.records_with_rating || "0%";
          quality.hours.textContent = dataQuality.records_with_working_hours || "0%";
          quality.services.textContent = dataQuality.records_with_services || "0%";
          renderFinalBusinesses(payload.report.business_results || []);
        }
      }
    }
  } catch (error) {
    if (error.name !== "AbortError") {
      showMessage("Search stopped because the stream could not be read.");
      logEvent({ event: "stream_error" });
    }
  } finally {
    if (!lastReport && results.textContent && !results.textContent.includes("Search stopped")) {
      logEvent({ event: "completed_event_missing" });
      showMessage("Partial results were shown, but the final report did not complete. Try a smaller limit or rerun.");
    }
    if (activeController === controller) resetRunButton();
  }
});

function resetRunButton() {
  runButton.disabled = false;
  runButton.textContent = "Run";
  activeController = null;
}

async function downloadReport() {
  if (!lastReport) return;
  pdfButton.disabled = true;
  pdfButtonSecondary.disabled = true;
  const response = await fetch("/research/pdf", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(lastReport),
  });
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match ? match[1] : "business-research-report.pdf";
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
  pdfButton.disabled = false;
  pdfButtonSecondary.disabled = false;
}

pdfButton.addEventListener("click", downloadReport);
pdfButtonSecondary.addEventListener("click", downloadReport);
loadReadiness();
document
  .getElementById("ask-ai-btn")
  ?.addEventListener("click", askAI);
//---------------------------
//Rag setup
//---------------------------

async function askAI() {

    const question =
        document.getElementById(
            "rag-question"
        ).value;

    if (!question) {
        alert("Enter a question");
        return;
    }

    const answerDiv =
        document.getElementById(
            "rag-answer"
        );

    answerDiv.innerHTML =
        "Thinking...";

    try {

        const response =
            await fetch(
                "/rag/ask",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        run_id: String(currentRunId),
                        question: question
                    })
                }
            );

        const data =
            await response.json();

        answerDiv.innerHTML =
            data.answer;

    } catch (err) {

        answerDiv.innerHTML =
            "Error: " + err;
    }
}