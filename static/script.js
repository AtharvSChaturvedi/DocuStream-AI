const fileInput = document.getElementById("file-input");
const uploadText = document.getElementById("upload-text");
const uploadStatus = document.getElementById("upload-status");
const paperList = document.getElementById("paper-list");
const paperCount = document.getElementById("paper-count");
const scopeSelect = document.getElementById("scope-select");
const askForm = document.getElementById("ask-form");
const questionInput = document.getElementById("question-input");
const askButton = document.getElementById("ask-button");
const thread = document.getElementById("thread");

let papers = [];

async function refreshPapers() {
  try {
    const res = await fetch("/api/papers");
    papers = await res.json();
    renderPapers();
  } catch (e) {
    // Non-fatal on first load.
  }
}

function renderPapers() {
  paperCount.textContent = papers.length;

  if (papers.length === 0) {
    paperList.innerHTML = '<li class="empty-note">No papers indexed yet.</li>';
  } else {
    paperList.innerHTML = papers
      .map(
        (p) => `
      <li class="paper-card">
        <div class="p-row">
          <div>
            <div class="p-title">${escapeHtml(p.title)}</div>
            <div class="p-meta">#${p.paper_id}</div>
          </div>
          <button class="p-remove" data-paper-id="${p.paper_id}" title="Remove this paper">&times;</button>
        </div>
      </li>`
      )
      .join("");
  }

  const current = scopeSelect.value;
  scopeSelect.innerHTML =
    '<option value="">All indexed papers</option>' +
    papers
      .map((p) => `<option value="${p.paper_id}">${escapeHtml(p.title)}</option>`)
      .join("");
  // Keep the previous selection only if that paper still exists.
  scopeSelect.value = papers.some((p) => p.paper_id === current) ? current : "";
}

paperList.addEventListener("click", async (e) => {
  const btn = e.target.closest(".p-remove");
  if (!btn) return;

  const paperId = btn.dataset.paperId;
  const paper = papers.find((p) => p.paper_id === paperId);
  const label = paper ? paper.title : "this paper";

  if (!confirm(`Remove "${label}"? This can't be undone.`)) return;

  btn.disabled = true;
  try {
    const res = await fetch(`/api/papers/${paperId}`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Delete failed");
    await refreshPapers();
  } catch (err) {
    uploadStatus.textContent = err.message;
    uploadStatus.className = "status-line error";
    btn.disabled = false;
  }
});

fileInput.addEventListener("change", async () => {
  const file = fileInput.files[0];
  if (!file) return;

  uploadText.textContent = "Uploading\u2026";
  uploadStatus.textContent = "";
  uploadStatus.className = "status-line";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Upload failed");

    uploadStatus.textContent = `Indexed ${data.chunks} chunks from "${data.title}"`;
    uploadStatus.className = "status-line ok";
    await refreshPapers();
  } catch (e) {
    uploadStatus.textContent = e.message;
    uploadStatus.className = "status-line error";
  } finally {
    uploadText.textContent = "Add a paper (PDF)";
    fileInput.value = "";
  }
});

askForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;

  questionInput.value = "";
  askButton.disabled = true;

  const block = document.createElement("div");
  block.className = "qa-block";
  block.innerHTML = `
    <div class="q-line">${escapeHtml(question)}</div>
    <div class="loading-dot">Reading the papers\u2026</div>
  `;
  thread.appendChild(block);
  thread.scrollTop = thread.scrollHeight;

  try {
    const res = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, paper_id: scopeSelect.value || null }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Query failed");

    const answerHtml = formatAnswer(data.answer);
    const sourcesHtml =
      data.sources && data.sources.length
        ? `<div class="sources">
             <div class="src-head">Works cited</div>
             ${data.sources
               .map(
                 (s, i) =>
                   `<div class="src-item">[${i + 1}] <b>${escapeHtml(
                     s.title
                   )}</b> &middot; page ${s.page}</div>`
               )
               .join("")}
           </div>`
        : "";

    block.innerHTML = `
      <div class="q-line">${escapeHtml(question)}</div>
      <div class="a-text">${answerHtml}</div>
      ${sourcesHtml}
    `;
  } catch (e) {
    block.innerHTML = `
      <div class="q-line">${escapeHtml(question)}</div>
      <div class="a-text" style="color:var(--accent)">${escapeHtml(e.message)}</div>
    `;
  } finally {
    askButton.disabled = false;
    thread.scrollTop = thread.scrollHeight;
  }
});

function formatAnswer(text) {
  const escaped = escapeHtml(text);
  return escaped.replace(/\[(\d+)\]/g, '<sup class="cite">$1</sup>');
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

refreshPapers();
