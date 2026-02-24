import logging

from dotenv import load_dotenv

load_dotenv()

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel

from complaint_workflow import ComplaintState, compile_graph
from database import (
    create_complaint,
    get_complaint,
    init_db,
    list_complaints,
    mark_error,
    mark_processing,
    save_workflow_result,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("server")

app = FastAPI(title="Complaint Workflow")


@app.on_event("startup")
def startup():
    init_db()


# --- Models ---

class ComplaintRequest(BaseModel):
    complaint: str


# --- Background processing ---

def process_complaint(complaint_id: str, text: str):
    try:
        mark_processing(complaint_id)
        checkpointer = MemorySaver()
        graph = compile_graph(checkpointer=checkpointer)
        initial_state: ComplaintState = {
            "complaint": text,
            "context": [],
            "categories": [],
            "resolution": "",
            "workflow_path": [],
            "status": "new",
            "validation_results": {},
            "investigation_findings": {},
            "effectiveness_rating": "",
            "requires_escalation": False,
            "closure_log": "",
            "satisfaction_verified": False,
            "follow_up_required": False,
            "closed_at": "",
        }
        result = graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": complaint_id}},
        )
        save_workflow_result(complaint_id, result)
        logger.info("Complaint %s processed successfully", complaint_id)
    except Exception:
        logger.exception("Error processing complaint %s", complaint_id)
        import traceback
        mark_error(complaint_id, traceback.format_exc())


# --- API endpoints ---

@app.post("/api/complaints")
def submit_complaint(req: ComplaintRequest, background_tasks: BackgroundTasks):
    if not req.complaint.strip():
        raise HTTPException(status_code=400, detail="Complaint text is required")
    record = create_complaint(req.complaint.strip())
    background_tasks.add_task(process_complaint, record["id"], req.complaint.strip())
    return record


@app.get("/api/complaints")
def list_all():
    return list_complaints()


@app.get("/api/complaints/{complaint_id}")
def get_one(complaint_id: str):
    record = get_complaint(complaint_id)
    if not record:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return record


# --- HTML frontend ---

HTML_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Complaint Workflow</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #f5f5f5; color: #333; padding: 2rem; max-width: 960px; margin: 0 auto; }
  h1 { margin-bottom: 1.5rem; color: #1a1a2e; }
  .card { background: #fff; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem;
          box-shadow: 0 1px 3px rgba(0,0,0,.1); }
  textarea { width: 100%; min-height: 80px; padding: .75rem; border: 1px solid #ddd;
             border-radius: 6px; font-size: .95rem; resize: vertical; font-family: inherit; }
  button { background: #1a1a2e; color: #fff; border: none; padding: .65rem 1.5rem;
           border-radius: 6px; cursor: pointer; font-size: .95rem; margin-top: .75rem; }
  button:disabled { opacity: .5; cursor: not-allowed; }
  button:hover:not(:disabled) { background: #16213e; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: .6rem .75rem; border-bottom: 1px solid #eee; font-size: .9rem; }
  th { background: #f9f9f9; font-weight: 600; }
  .badge { display: inline-block; padding: .2rem .6rem; border-radius: 12px; font-size: .78rem;
           font-weight: 600; text-transform: uppercase; }
  .badge-submitted { background: #e3f2fd; color: #1565c0; }
  .badge-processing { background: #fff3e0; color: #e65100; }
  .badge-closed { background: #e8f5e9; color: #2e7d32; }
  .badge-error { background: #ffebee; color: #c62828; }
  .id-link { color: #1565c0; cursor: pointer; text-decoration: underline; font-family: monospace; font-size: .82rem; }
  .modal-bg { position: fixed; inset: 0; background: rgba(0,0,0,.45); display: none;
              align-items: center; justify-content: center; z-index: 100; }
  .modal-bg.open { display: flex; }
  .modal { background: #fff; border-radius: 10px; padding: 2rem; max-width: 700px; width: 90%;
           max-height: 85vh; overflow-y: auto; position: relative; }
  .modal h2 { margin-bottom: 1rem; font-size: 1.1rem; }
  .modal pre { background: #f5f5f5; padding: 1rem; border-radius: 6px; white-space: pre-wrap;
               word-break: break-word; font-size: .85rem; margin: .5rem 0 1rem; max-height: 200px; overflow-y: auto; }
  .modal .close { position: absolute; top: 1rem; right: 1rem; background: none; border: none;
                  font-size: 1.3rem; cursor: pointer; color: #666; padding: 0; margin: 0; }
  .section-label { font-weight: 600; margin-top: .75rem; color: #555; font-size: .85rem; }
  .empty { color: #999; text-align: center; padding: 2rem; }
</style>
</head>
<body>
<h1>Complaint Workflow</h1>

<div class="card">
  <form id="form">
    <textarea id="text" placeholder="Describe your complaint..."></textarea>
    <button type="submit" id="btn">Submit Complaint</button>
  </form>
</div>

<div class="card">
  <h2 style="margin-bottom:.75rem">Complaints</h2>
  <div id="table-wrap"></div>
</div>

<div class="modal-bg" id="modal-bg">
  <div class="modal" id="modal"></div>
</div>

<script>
const API = '/api/complaints';

document.getElementById('form').addEventListener('submit', async e => {
  e.preventDefault();
  const text = document.getElementById('text').value.trim();
  if (!text) return;
  const btn = document.getElementById('btn');
  btn.disabled = true;
  try {
    await fetch(API, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({complaint: text})
    });
    document.getElementById('text').value = '';
    loadComplaints();
  } finally { btn.disabled = false; }
});

function badge(status) {
  return `<span class="badge badge-${status}">${status}</span>`;
}

function truncate(s, n) {
  return s.length > n ? s.slice(0, n) + '...' : s;
}

async function loadComplaints() {
  const res = await fetch(API);
  const data = await res.json();
  const wrap = document.getElementById('table-wrap');
  if (!data.length) { wrap.innerHTML = '<p class="empty">No complaints yet.</p>'; return; }
  let html = '<table><tr><th>ID</th><th>Complaint</th><th>Status</th><th>Created</th></tr>';
  for (const c of data) {
    const created = new Date(c.created_at).toLocaleString();
    html += `<tr>
      <td><span class="id-link" onclick="showDetail('${c.id}')">${c.id.slice(0,8)}</span></td>
      <td>${esc(truncate(c.complaint, 80))}</td>
      <td>${badge(c.status)}</td>
      <td>${created}</td>
    </tr>`;
  }
  html += '</table>';
  wrap.innerHTML = html;
}

async function showDetail(id) {
  const res = await fetch(API + '/' + id);
  const c = await res.json();
  const modal = document.getElementById('modal');
  let html = `<button class="close" onclick="closeModal()">&times;</button>`;
  html += `<h2>Complaint ${c.id.slice(0,8)} ${badge(c.status)}</h2>`;
  html += `<p class="section-label">Complaint</p><pre>${esc(c.complaint)}</pre>`;
  if (c.categories.length) {
    html += `<p class="section-label">Categories</p><pre>${esc(c.categories.join(', '))}</pre>`;
  }
  if (Object.keys(c.findings).length) {
    html += `<p class="section-label">Investigation Findings</p><pre>${esc(JSON.stringify(c.findings, null, 2))}</pre>`;
  }
  if (c.resolution) {
    html += `<p class="section-label">Resolution</p><pre>${esc(c.resolution)}</pre>`;
  }
  if (c.closure_log) {
    html += `<p class="section-label">Closure Log</p><pre>${esc(c.closure_log)}</pre>`;
  }
  if (c.error) {
    html += `<p class="section-label">Error</p><pre style="color:#c62828">${esc(c.error)}</pre>`;
  }
  html += `<p class="section-label">Created</p><pre>${new Date(c.created_at).toLocaleString()}</pre>`;
  html += `<p class="section-label">Updated</p><pre>${new Date(c.updated_at).toLocaleString()}</pre>`;
  modal.innerHTML = html;
  document.getElementById('modal-bg').classList.add('open');
}

function closeModal() { document.getElementById('modal-bg').classList.remove('open'); }
document.getElementById('modal-bg').addEventListener('click', e => {
  if (e.target === e.currentTarget) closeModal();
});

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

loadComplaints();
setInterval(loadComplaints, 3000);
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE
