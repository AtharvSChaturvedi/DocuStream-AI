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
      <li class="paper-card" data-paper-id="${p.paper_id}">
        <div class="p-row">
          <div>
            <div class="p-title">${escapeHtml(p.title)}</div>
            <div class="p-meta">#${p.paper_id}</div>
          </div>
          <button class="p-remove" data-paper-id="${p.paper_id}" title="Remove this paper">&times;</button>
        </div>
        <button class="p-readiness-btn" data-paper-id="${p.paper_id}" data-title="${escapeHtml(p.title)}">
          Check readiness
        </button>
        <div class="readiness-panel" data-panel-for="${p.paper_id}" hidden></div>
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
  scopeSelect.value = papers.some((p) => p.paper_id === current) ? current : "";
}

paperList.addEventListener("click", async (e) => {
  const removeBtn = e.target.closest(".p-remove");
  if (removeBtn) {
    const paperId = removeBtn.dataset.paperId;
    const paper = papers.find((p) => p.paper_id === paperId);
    const label = paper ? paper.title : "this paper";
    if (!confirm(`Remove "${label}"? This can't be undone.`)) return;

    removeBtn.disabled = true;
    try {
      const res = await fetch(`/api/papers/${paperId}`, { method: "DELETE" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Delete failed");
      await refreshPapers();
    } catch (err) {
      uploadStatus.textContent = err.message;
      uploadStatus.className = "status-line error";
      removeBtn.disabled = false;
    }
    return;
  }

  const readinessBtn = e.target.closest(".p-readiness-btn");
  if (readinessBtn) {
    await runReadinessCheck(readinessBtn);
  }
});

async function runReadinessCheck(btn) {
  const paperId = btn.dataset.paperId;
  const title = btn.dataset.title;
  const panel = paperList.querySelector(`.readiness-panel[data-panel-for="${paperId}"]`);

  btn.disabled = true;
  btn.textContent = "Reviewing\u2026";
  panel.hidden = false;
  panel.innerHTML = `<div class="loading-dot">Reading like an reviewer\u2026</div>`;

  try {
    const res = await fetch(`/api/papers/${paperId}/readiness`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Readiness check failed");

    panel.innerHTML = renderReadiness(data);
  } catch (err) {
    panel.innerHTML = `<div class="a-text" style="color:var(--accent)">${escapeHtml(err.message)}</div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Re-check readiness";
  }
}

function renderReadiness(data) {
  const barsHtml = data.criteria
    .map(
      (c) => `
    <div class="crit-row">
      <div class="crit-label">${escapeHtml(c.label)}</div>
      <div class="crit-bar-track">
        <div class="crit-bar-fill" style="width:${c.score * 10}%"></div>
      </div>
      <div class="crit-score">${c.score}/10</div>
    </div>
    <div class="crit-feedback">${escapeHtml(c.feedback)}</div>`
    )
    .join("");

  const strengthsHtml = data.top_strengths.length
    ? `<div class="rlist">
         <div class="rlist-head">Strengths</div>
         <ul>${data.top_strengths.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ul>
       </div>`
    : "";

  const improvementsHtml = data.top_improvements.length
    ? `<div class="rlist">
         <div class="rlist-head">Improve before submitting</div>
         <ul>${data.top_improvements.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ul>
       </div>`
    : "";

  return `
    <div class="readiness-score-row">
      <div class="readiness-score-num">${data.readiness_score}%</div>
      <div class="readiness-score-label">
        Readiness Score
        <span class="readiness-disclaimer">Heuristic estimate against common review criteria &mdash; not a guarantee of acceptance.</span>
      </div>
    </div>
    <div class="crit-list">${barsHtml}</div>
    <div class="rlist-grid">${strengthsHtml}${improvementsHtml}</div>
  `;
}

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
      <div class="a-text typing"></div>
    `;
    const answerEl = block.querySelector(".a-text");

    await typeHtml(answerEl, answerHtml);
    answerEl.classList.remove("typing");

    if (sourcesHtml) {
      const sourcesEl = document.createElement("div");
      sourcesEl.innerHTML = sourcesHtml;
      sourcesEl.style.opacity = "0";
      block.appendChild(sourcesEl.firstElementChild);
      requestAnimationFrame(() => {
        block.querySelector(".sources").style.opacity = "1";
      });
    }
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

function typeHtml(el, html, charsPerTick = 2, delayMs = 12) {
  return new Promise((resolve) => {
    el.innerHTML = "";
    let i = 0;

    function step() {
      if (i >= html.length) {
        resolve();
        return;
      }

      if (html[i] === "<") {
        const close = html.indexOf(">", i);
        if (close === -1) {
          el.innerHTML += html.slice(i);
          i = html.length;
        } else {
          el.innerHTML += html.slice(i, close + 1);
          i = close + 1;
        }
      } else {
        const nextTag = html.indexOf("<", i);
        const end = nextTag === -1 ? html.length : nextTag;
        const chunkEnd = Math.min(i + charsPerTick, end);
        el.innerHTML += html.slice(i, chunkEnd);
        i = chunkEnd;
      }

      thread.scrollTop = thread.scrollHeight;
      setTimeout(step, delayMs);
    }

    step();
  });
}

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
