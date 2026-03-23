const form = document.getElementById("analyzeForm");
const fileInput = document.getElementById("fileInput");
const requiredItems = document.getElementById("requiredItems");
const generateAiSummary = document.getElementById("generateAiSummary");
const submitButton = document.getElementById("submitButton");
const filePreview = document.getElementById("filePreview");
const loadingState = document.getElementById("loadingState");
const emptyState = document.getElementById("emptyState");
const resultsContent = document.getElementById("resultsContent");
const summaryGrid = document.getElementById("summaryGrid");
const annotatedImage = document.getElementById("annotatedImage");
const reportTitle = document.getElementById("reportTitle");
const reportSummary = document.getElementById("reportSummary");
const reportActions = document.getElementById("reportActions");
const workerList = document.getElementById("workerList");
const timelineSection = document.getElementById("timelineSection");
const timelineGrid = document.getElementById("timelineGrid");
const dropzone = document.getElementById("dropzone");
const demoPolicyButton = document.getElementById("demoPolicyButton");
const downloadJsonButton = document.getElementById("downloadJsonButton");

let latestResponse = null;

function setLoading(message, busy = false) {
  loadingState.textContent = message;
  submitButton.disabled = busy;
  submitButton.style.opacity = busy ? "0.7" : "1";
}

function updateFilePreview() {
  const file = fileInput.files?.[0];
  filePreview.textContent = file
    ? `${file.name} - ${(file.size / (1024 * 1024)).toFixed(2)} MB`
    : "No file selected yet.";
}

function createSummaryCard(label, value, tone = "") {
  const card = document.createElement("article");
  card.className = `summary-card ${tone}`.trim();
  card.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
  return card;
}

function renderWorkers(workers) {
  workerList.innerHTML = "";
  workers.forEach((worker) => {
    const card = document.createElement("article");
    card.className = "worker-card";
    const statusClass = worker.status === "compliant" ? "ok" : "bad";
    card.innerHTML = `
      <div class="worker-header">
        <h5>${worker.worker_id}</h5>
        <span class="worker-pill ${statusClass}">${worker.status}</span>
      </div>
      <div class="worker-meta"><strong>Score:</strong> ${worker.score}%</div>
      <div class="worker-meta"><strong>Present:</strong> ${worker.present_items.join(", ") || "None"}</div>
      <div class="worker-meta"><strong>Missing:</strong> ${worker.missing_items.join(", ") || "None"}</div>
    `;
    workerList.appendChild(card);
  });
}

function renderActions(actions) {
  reportActions.innerHTML = "";
  actions.forEach((action) => {
    const item = document.createElement("div");
    item.className = "action-item";
    item.textContent = action;
    reportActions.appendChild(item);
  });
}

function renderTimeline(frames) {
  timelineGrid.innerHTML = "";
  if (!frames.length) {
    timelineSection.classList.add("hidden");
    return;
  }
  timelineSection.classList.remove("hidden");
  frames.forEach((frame) => {
    const card = document.createElement("article");
    card.className = "timeline-card";
    card.innerHTML = `
      <div class="timeline-header">
        <h5>${frame.timestamp_seconds}s</h5>
        <span class="risk-pill ${frame.risk_level}">${frame.risk_level} risk</span>
      </div>
      <img src="${frame.thumbnail_url}" alt="Frame at ${frame.timestamp_seconds} seconds" />
      <div class="timeline-meta">${frame.compliant_workers}/${frame.total_workers} workers compliant</div>
    `;
    timelineGrid.appendChild(card);
  });
}

function renderResults(payload) {
  latestResponse = payload;
  emptyState.classList.add("hidden");
  resultsContent.classList.remove("hidden");

  summaryGrid.innerHTML = "";
  summaryGrid.appendChild(createSummaryCard("Workers", payload.site_summary.total_workers));
  summaryGrid.appendChild(createSummaryCard("Compliance Rate", `${payload.site_summary.compliance_rate}%`));
  summaryGrid.appendChild(createSummaryCard("Non-Compliant", payload.site_summary.non_compliant_workers));
  summaryGrid.appendChild(createSummaryCard("Policy", payload.required_items.join(", ")));

  annotatedImage.src = payload.annotated_asset.url;
  reportTitle.textContent = payload.report.title;
  reportSummary.textContent = payload.report.summary;
  renderActions(payload.report.actions);
  renderWorkers(payload.workers);
  renderTimeline(payload.frames || []);
}

async function handleSubmit(event) {
  event.preventDefault();
  const file = fileInput.files?.[0];
  if (!file) {
    setLoading("Choose an image or video first");
    return;
  }

  const body = new FormData();
  body.append("file", file);
  body.append("required_items", requiredItems.value);
  body.append("generate_ai_summary", generateAiSummary.checked ? "true" : "false");

  setLoading("Analyzing PPE compliance...", true);

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      body,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Analysis failed");
    }
    renderResults(data);
    setLoading("Analysis complete");
  } catch (error) {
    setLoading(error.message || "Analysis failed");
  } finally {
    submitButton.disabled = false;
    submitButton.style.opacity = "1";
  }
}

function enableDragAndDrop() {
  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.add("dragging");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.remove("dragging");
    });
  });

  dropzone.addEventListener("drop", (event) => {
    const file = event.dataTransfer?.files?.[0];
    if (!file) {
      return;
    }
    fileInput.files = event.dataTransfer.files;
    updateFilePreview();
  });
}

demoPolicyButton.addEventListener("click", () => {
  requiredItems.value = "helmet,vest";
});

downloadJsonButton.addEventListener("click", () => {
  if (!latestResponse) {
    return;
  }
  const blob = new Blob([JSON.stringify(latestResponse, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "ppe-analysis.json";
  anchor.click();
  URL.revokeObjectURL(url);
});

fileInput.addEventListener("change", updateFilePreview);
form.addEventListener("submit", handleSubmit);
enableDragAndDrop();
