const form = document.querySelector('#match-form');
const resumeInput = document.querySelector('#resume-text');
const status = document.querySelector('.engine-status');
const resultSection = document.querySelector('.match-results');
const cards = document.querySelector('#result-cards');
const empty = document.querySelector('#results-empty');
const summary = document.querySelector('#results-summary');
let worker;
let activeRequest;
let sequence = 0;
let revision = 0;
let customCSV = '';
let lastRows = [];

function showStatus(message, error = false) {
  status.textContent = message;
  status.classList.toggle('is-error', error);
}
function resetWorker() {
  worker?.terminate();
  worker = null;
  if (activeRequest) {
    clearTimeout(activeRequest.timer);
    const error = new Error('Cancelled');
    error.name = 'AbortError';
    activeRequest.reject(error);
    activeRequest = null;
  }
}
function runModel(payload) {
  if (!worker) {
    worker = new Worker(new URL('projects/job-recommender/worker.mjs', import.meta.url), { type: 'module' });
    worker.addEventListener('message', ({ data }) => {
      if (data.type === 'progress') { showStatus(data.message); return; }
      if (!activeRequest || data.id !== activeRequest.id) return;
      const request = activeRequest;
      activeRequest = null;
      clearTimeout(request.timer);
      if (data.type === 'result') request.resolve(data.result);
      else {
        request.reject(new Error(data.message));
        worker.terminate();
        worker = null;
      }
    });
    worker.addEventListener('error', () => {
      if (activeRequest) {
        clearTimeout(activeRequest.timer);
        activeRequest.reject(new Error('The matching engine could not load. Check your connection and try again.'));
        activeRequest = null;
      }
      worker?.terminate();
      worker = null;
    });
  }
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    activeRequest = { id, resolve, reject, timer: setTimeout(() => {
      if (!activeRequest || activeRequest.id !== id) return;
      activeRequest = null;
      worker?.terminate(); worker = null;
      reject(new Error('The engine took too long to load. Your résumé is still here; please try again.'));
    }, 180000) };
    worker.postMessage({ id, payload });
  });
}
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function displayResults(result) {
  lastRows = result.results.filter(row => Number(row.cosine_similarity) > 0);
  cards.replaceChildren();
  empty.hidden = lastRows.length > 0;
  summary.hidden = lastRows.length === 0;
  if (!lastRows.length) {
    empty.querySelector('h3').textContent = 'No shared terms found.';
    empty.querySelector('p').textContent = 'Try a more detailed résumé, broader filters, or job descriptions closer to your background.';
    showStatus('No meaningful text overlap was found for the selected roles.');
    return;
  }
  document.querySelector('.results-count').textContent = `${lastRows.length} ${lastRows.length === 1 ? 'match' : 'matches'} · ${result.eligible} roles compared`;
  for (const row of lastRows) {
    const card = el('article', 'result-card');
    const titleRow = el('div', 'result-title-row');
    titleRow.append(el('h3', '', row.job_title), el('span', 'result-rank', `#${row.rank}`));
    const context = [row.job_company, row.job_location, row.job_source].filter(Boolean).join(' · ');
    const label = el('div', 'similarity-label');
    const score = Math.max(0, Math.min(1, Number(row.cosine_similarity) || 0));
    label.append(el('span', '', 'Text similarity'), el('strong', '', score.toFixed(3)));
    const bar = el('div', 'similarity-bar');
    const fill = el('span'); fill.style.width = `${score * 100}%`; bar.append(fill);
    const skills = el('p', 'result-skills', `Shared skills: ${row.matched_skills || 'No named skills detected; see shared terms below.'}`);
    const detail = el('details');
    detail.append(el('summary', '', 'Why this match?'));
    detail.append(el('p', '', `Shared terms: ${row.matched_terms || 'None detected.'}`));
    detail.append(el('p', '', `Job skills not found in the résumé: ${row.missing_skills || 'None detected.'}`));
    detail.append(el('p', '', row.job_description_raw));
    card.append(titleRow, el('p', 'result-context', context), label, bar, skills, detail);
    cards.append(card);
  }
  showStatus('Matches ready. Your résumé was processed locally in this browser.');
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!form.reportValidity() || activeRequest) return;
  const button = form.querySelector('[type="submit"]');
  const runRevision = ++revision;
  const payload = { resume: resumeInput.value, csv: customCSV, jobs: [], location: document.querySelector('#location-filter').value.trim(), title: document.querySelector('#title-filter').value.trim(), top_n: Number(document.querySelector('#top-n').value) };
  button.disabled = true;
  button.querySelector('span').textContent = 'Finding connections…';
  resultSection.setAttribute('aria-busy', 'true');
  summary.hidden = true;
  cards.replaceChildren();
  showStatus('Preparing your matches…');
  try {
    let jobs = [];
    if (!payload.csv) {
      const response = await fetch('projects/job-recommender/example-jobs.json');
      if (!response.ok) throw new Error('The example roles could not be loaded. Please try again.');
      jobs = await response.json();
    }
    if (revision !== runRevision) return;
    const result = await runModel({ ...payload, jobs });
    if (revision === runRevision) displayResults(result);
  } catch (error) {
    if (revision === runRevision && error.name !== 'AbortError') showStatus(error.message, true);
  } finally {
    button.disabled = false;
    button.querySelector('span').textContent = 'Find my matches';
    resultSection.setAttribute('aria-busy', 'false');
  }
});

document.querySelector('#example-resume').addEventListener('click', () => {
  resumeInput.value = 'Data science graduate with practical experience in Python, pandas, NumPy and scikit-learn. Built a content-based job recommendation system using natural language processing, text preprocessing, TF-IDF and cosine similarity. Interested in data analysis, machine learning, model evaluation and data visualization. Comfortable working with SQL and communicating clear findings.';
  showStatus('Example summary added. Select “Find my matches” to try the model.');
});
document.querySelector('#resume-file').addEventListener('change', async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  if (!/\.txt$/i.test(file.name) || file.size > 200000) { showStatus('Please choose a TXT résumé smaller than 200 KB.', true); event.target.value = ''; return; }
  try {
    const text = await file.text();
    if (text.length > 30000) throw new Error('Please shorten the résumé to 30,000 characters or fewer.');
    resumeInput.value = text;
    showStatus('Résumé text added locally. It has not been uploaded.');
  } catch (error) { showStatus(error.message, true); }
});
document.querySelector('#jobs-file').addEventListener('change', async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  if (!/\.csv$/i.test(file.name) || file.size > 2000000) { showStatus('Please choose a job CSV smaller than 2 MB.', true); event.target.value = ''; return; }
  try {
    customCSV = await file.text();
    document.querySelector('#dataset-title').textContent = file.name;
    document.querySelector('#dataset-note').textContent = 'Using your job dataset. Its contents remain in this browser.';
    document.querySelector('#reset-dataset').hidden = false;
    showStatus('Your CSV is ready. It will be checked when you run the model.');
  } catch { showStatus('The CSV could not be read. Please try another file.', true); }
});
document.querySelector('#reset-dataset').addEventListener('click', () => {
  customCSV = '';
  document.querySelector('#jobs-file').value = '';
  document.querySelector('#dataset-title').textContent = '10 example roles';
  document.querySelector('#dataset-note').textContent = 'Illustrative job descriptions for trying the model. These are not live vacancies.';
  document.querySelector('#reset-dataset').hidden = true;
  showStatus('Example roles selected.');
});
document.querySelector('#clear-data').addEventListener('click', () => {
  ++revision;
  ++sequence;
  resetWorker();
  resumeInput.value = '';
  document.querySelector('#resume-file').value = '';
  lastRows = [];
  cards.replaceChildren();
  summary.hidden = true;
  empty.hidden = false;
  empty.querySelector('h3').textContent = 'Good matches start with context.';
  empty.querySelector('p').textContent = 'Add your résumé or try the example. The model will rank roles and explain each match.';
  showStatus('Résumé and matching results cleared.');
});

function csvCell(value) {
  let text = String(value ?? '');
  if (/^[\s]*[=+\-@]/.test(text)) text = "'" + text;
  return '"' + text.replaceAll('"', '""') + '"';
}
document.querySelector('#download-results').addEventListener('click', () => {
  const columns = ['rank', 'job_title', 'job_company', 'job_location', 'cosine_similarity', 'matched_terms', 'matched_skills', 'missing_skills'];
  const csv = [columns.map(csvCell).join(','), ...lastRows.map(row => columns.map(key => csvCell(row[key])).join(','))].join('\r\n');
  const url = URL.createObjectURL(new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a'); link.href = url; link.download = 'job-recommendations.csv'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
