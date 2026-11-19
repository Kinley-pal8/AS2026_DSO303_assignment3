/* UniExam single-page app: Cognito (PKCE) sign-in, role-based views, timed exams with 30 s autosave,
   direct-to-S3 assignment uploads. No build step, no framework. */
"use strict";

const C = window.APP_CONFIG;
const $ = (sel, el = document) => el.querySelector(sel);
const view = $("#view");
const MAX_UPLOAD = 50 * 1024 * 1024;
const AUTOSAVE_MS = 30_000;
let cleanup = () => {};

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const fmt = (iso) => (iso ? new Date(iso).toLocaleString() : "—");
const store = {
  get: (k) => { try { return sessionStorage.getItem(k); } catch { return null; } },
  set: (k, v) => { try { sessionStorage.setItem(k, v); } catch {} },
  del: (k) => { try { sessionStorage.removeItem(k); } catch {} },
};
function toast(msg, ms = 3500) {
  const t = $("#toast"); t.textContent = msg; t.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), ms);
}

/* ------------------------------------------------------------------ auth (OAuth2 code + PKCE) */
const redirectUri = location.origin + "/";
const b64url = (bytes) => btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

async function login() {
  const verifier = b64url(crypto.getRandomValues(new Uint8Array(32)));
  const challenge = b64url(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier))));
  const state = b64url(crypto.getRandomValues(new Uint8Array(16)));
  store.set("pkce_verifier", verifier); store.set("oauth_state", state); store.set("return_hash", location.hash);
  location.assign(`${C.cognitoDomain}/oauth2/authorize?` + new URLSearchParams({
    response_type: "code", client_id: C.clientId, redirect_uri: redirectUri, scope: "openid email profile",
    code_challenge_method: "S256", code_challenge: challenge, state,
  }));
}

function logout() {
  ["id_token", "refresh_token"].forEach(store.del);
  location.assign(`${C.cognitoDomain}/logout?` + new URLSearchParams({ client_id: C.clientId, logout_uri: redirectUri }));
}

async function tokenRequest(params) {
  const r = await fetch(`${C.cognitoDomain}/oauth2/token`, {
    method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ client_id: C.clientId, ...params }),
  });
  if (!r.ok) throw new Error("token request failed");
  const t = await r.json();
  store.set("id_token", t.id_token);
  if (t.refresh_token) store.set("refresh_token", t.refresh_token);
}

async function handleCallback() {
  const p = new URLSearchParams(location.search);
  if (!p.has("code")) return;
  const ok = p.get("state") === store.get("oauth_state");
  const hash = store.get("return_hash") || "";
  history.replaceState(null, "", location.pathname + hash);
  if (!ok) throw new Error("sign-in state mismatch, please try again");
  await tokenRequest({ grant_type: "authorization_code", code: p.get("code"), code_verifier: store.get("pkce_verifier"), redirect_uri: redirectUri });
  store.del("pkce_verifier"); store.del("oauth_state");
}

function claims() {
  const t = store.get("id_token");
  if (!t) return null;
  try {
    const part = t.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(part), (c) => c.charCodeAt(0))));
  } catch { return null; }
}

async function idToken() {
  let c = claims();
  if (!c) return null;
  if (c.exp * 1000 - Date.now() < 5 * 60_000 && store.get("refresh_token")) {
    try { await tokenRequest({ grant_type: "refresh_token", refresh_token: store.get("refresh_token") }); } catch {}
    c = claims();
  }
  return c && c.exp * 1000 > Date.now() ? store.get("id_token") : null;
}

async function api(method, path, body) {
  const token = await idToken();
  if (!token) { login(); throw new Error("Session expired, signing in again…"); }
  const r = await fetch(C.apiBase + path, {
    method, headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) { const e = new Error(data.error || data.message || `HTTP ${r.status}`); e.status = r.status; throw e; }
  return data;
}

const roles = () => (claims()?.["cognito:groups"]) || [];
const has = (...r) => roles().some((x) => r.includes(x));

/* ------------------------------------------------------------------ router */
async function router() {
  cleanup(); cleanup = () => {};
  const c = claims();
  if (!c) {
    $("#who").innerHTML = "";
    view.innerHTML = `<div class="card"><h1>Online exams & assignments</h1>
      <p class="muted">Sign in with your university account.</p><button id="login">Sign in</button></div>`;
    $("#login").onclick = login;
    return;
  }
  $("#who").innerHTML = `<span>${esc(c.email)} · ${esc(roles().join(", ") || "no role")}</span>
    <button class="secondary" id="logout">Sign out</button>`;
  $("#logout").onclick = logout;

  const [page, id] = (location.hash.replace(/^#\/?/, "") || "").split("/");
  view.innerHTML = `<p class="muted">Loading…</p>`;
  try {
    if (page === "exam" && id) return await examPage(id);
    if (page === "results" && id) return await resultsPage(id);
    if (page === "submissions" && id) return await submissionsPage(id);
    return await home();
  } catch (e) {
    view.innerHTML = `<div class="card"><h2>Something went wrong</h2><p>${esc(e.message)}</p><a class="btn" href="#/">Back</a></div>`;
  }
}

async function home() {
  if (!roles().length) {
    view.innerHTML = `<div class="card"><h1>No role assigned</h1><p class="muted">Ask an administrator to add you to students, tutors or admins.</p></div>`;
    return;
  }
  const parts = [];
  if (has("students")) parts.push(await studentHome());
  if (has("tutors", "admins")) parts.push(await staffHome());
  if (has("admins")) parts.push(await adminHome());
  view.innerHTML = parts.map((p) => p.html).join("");
  parts.forEach((p) => p.bind && p.bind());
}

/* ------------------------------------------------------------------ student */
async function studentHome() {
  const [{ exams }, { results }, { assignments }] = await Promise.all([api("GET", "/exams"), api("GET", "/results"), api("GET", "/assignments")]);
  const now = Date.now();
  const examRows = exams.map((e) => {
    const open = new Date(e.opens_at) <= now && now <= new Date(e.closes_at);
    const st = e.attempt_status;
    const action = st === "SUBMITTED" ? `<span class="pill ok">Submitted</span>`
      : open ? `<a class="btn" href="#/exam/${e.id}">${st ? "Resume" : "Start"}</a>`
      : `<span class="pill">${new Date(e.opens_at) > now ? "Not open yet" : "Closed"}</span>`;
    return `<tr><td>${esc(e.title)}<div class="muted">${esc(e.course)} · ${e.duration_minutes} min</div></td>
      <td>${fmt(e.opens_at)}<br>${fmt(e.closes_at)}</td><td>${action}</td></tr>`;
  }).join("") || `<tr><td colspan="3" class="muted">No exams scheduled.</td></tr>`;
  const resultRows = results.map((r) => `<tr><td>${esc(r.title)}</td>
      <td>${Number(r.mcq_score) + Number(r.sa_score || 0)} / ${Number(r.mcq_max) + Number(r.sa_max)}</td><td>${fmt(r.released_at)}</td></tr>`).join("")
    || `<tr><td colspan="3" class="muted">No results released yet.</td></tr>`;
  const asgRows = assignments.map((a) => `<tr><td>${esc(a.title)}<div class="muted">${esc(a.course)}</div></td>
      <td>${fmt(a.due_at)}</td>
      <td>${a.my_last_submission ? `<span class="pill ok">Submitted ${fmt(a.my_last_submission)}</span>` : `<span class="pill warn">Not submitted</span>`}</td>
      <td><input type="file" accept=".pdf,.zip" data-upload="${a.id}"><progress data-progress="${a.id}" value="0" max="100" hidden></progress></td></tr>`).join("")
    || `<tr><td colspan="4" class="muted">No assignments.</td></tr>`;
  return {
    html: `<div class="card"><h1>My exams</h1><div class="table-wrap"><table><tr><th>Exam</th><th>Window</th><th></th></tr>${examRows}</table></div></div>
      <div class="card"><h2>My results</h2><div class="table-wrap"><table><tr><th>Exam</th><th>Score</th><th>Released</th></tr>${resultRows}</table></div></div>
      <div class="card"><h2>Assignments</h2><p class="muted">PDF or ZIP, up to 50 MB. Files upload straight to secure storage.</p>
      <div class="table-wrap"><table><tr><th>Assignment</th><th>Due</th><th>Status</th><th>Upload</th></tr>${asgRows}</table></div></div>`,
    bind() {
      view.querySelectorAll("[data-upload]").forEach((input) => {
        input.onchange = () => input.files[0] && uploadFile(input.dataset.upload, input.files[0], input);
      });
    },
  };
}

async function uploadFile(assignmentId, file, input) {
  if (file.size > MAX_UPLOAD) return toast("File is larger than 50 MB.");
  if (!/\.(pdf|zip)$/i.test(file.name)) return toast("Only .pdf and .zip files are accepted.");
  const bar = view.querySelector(`[data-progress="${assignmentId}"]`);
  input.disabled = true; bar.hidden = false; bar.value = 0;
  try {
    const p = await api("POST", `/assignments/${assignmentId}/upload-url`, { filename: file.name, size: file.size });
    const form = new FormData();
    Object.entries(p.fields).forEach(([k, v]) => form.append(k, v));
    form.append("file", file); // must be the last field
    await new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", p.url);
      xhr.upload.onprogress = (e) => e.lengthComputable && (bar.value = (e.loaded / e.total) * 100);
      xhr.onload = () => (xhr.status < 300 ? resolve() : reject(new Error(`Upload rejected (${xhr.status})`)));
      xhr.onerror = () => reject(new Error("Network error during upload"));
      xhr.send(form);
    });
    toast("Uploaded. Your tutor will be notified and you'll get a receipt by e-mail.");
    setTimeout(router, 2500);
  } catch (e) {
    toast(e.message); input.disabled = false; bar.hidden = true;
  }
}

/* ------------------------------------------------------------------ exam taking (timer + autosave) */
async function examPage(examId) {
  const data = await api("POST", `/exams/${examId}/start`);
  const { attempt, paper } = data;
  if (attempt.attempt_status === "SUBMITTED") {
    view.innerHTML = `<div class="card"><h1>${esc(paper.title)}</h1><p>This exam has been submitted.</p><a class="btn" href="#/">Back</a></div>`;
    return;
  }
  const localKey = `exam-backup-${examId}`;
  let answers = attempt.answers || {};
  try { // local copy survives a browser crash / network drop; use it if newer than the server copy
    const local = JSON.parse(localStorage.getItem(localKey) || "null");
    if (local && local.ts / 1000 > (attempt.saved_at || 0)) answers = { ...answers, ...local.answers };
  } catch {}
  const skew = data.server_time * 1000 - Date.now();
  const deadline = attempt.deadline_epoch * 1000;
  let dirty = Object.keys(answers).length > 0, saving = false, finished = false;

  view.innerHTML = `
    <div class="card exam-bar"><div><h1 style="margin:0">${esc(paper.title)}</h1><span class="muted">${esc(paper.course)}</span></div>
      <div class="row"><span id="save-status" class="pill">Not saved yet</span><span id="timer" class="timer">--:--</span>
      <button id="submit">Submit exam</button></div></div>
    <form class="card" id="paper">${paper.questions.map((q, i) => `
      <div class="question"><p>${i + 1}. ${esc(q.text)} <span class="muted">(${q.marks} mark${q.marks > 1 ? "s" : ""})</span></p>
      ${q.type === "mcq"
        ? q.options.map((o, oi) => `<label class="option"><input type="radio" name="${esc(q.id)}" value="${oi}" ${answers[q.id] === oi ? "checked" : ""}> ${esc(o)}</label>`).join("")
        : `<textarea name="${esc(q.id)}" maxlength="5000">${esc(answers[q.id] || "")}</textarea>`}
      </div>`).join("")}</form>`;

  const status = (text, cls = "") => { const s = $("#save-status"); s.textContent = text; s.className = `pill ${cls}`; };
  $("#paper").addEventListener("input", (e) => {
    const t = e.target;
    answers[t.name] = t.type === "radio" ? Number(t.value) : t.value;
    dirty = true; status("Unsaved changes", "warn");
    try { localStorage.setItem(localKey, JSON.stringify({ ts: Date.now(), answers })); } catch {}
  });

  async function save() {
    if (!dirty || saving || finished) return;
    saving = true; dirty = false;
    try {
      const r = await api("PUT", `/exams/${examId}/answers`, { answers });
      status(`Saved ${new Date(r.saved_at * 1000).toLocaleTimeString()}`, "ok");
    } catch (e) {
      dirty = true;
      status(e.status === 409 ? "Exam closed" : "Offline – retrying", "bad");
    } finally { saving = false; }
  }

  async function submit(auto) {
    if (finished) return;
    if (!auto && !confirm("Submit your exam now? You cannot change answers afterwards.")) return;
    finished = true; $("#submit").disabled = true;
    try {
      await api("POST", `/exams/${examId}/submit`, { answers });
      try { localStorage.removeItem(localKey); } catch {}
      view.innerHTML = `<div class="card"><h1>Submitted</h1><p>${auto ? "Time is up – your answers were submitted automatically." : "Your answers were submitted."}
        Multiple-choice questions are marked automatically; you'll be e-mailed when results are released.</p><a class="btn" href="#/">Back to dashboard</a></div>`;
      cleanup();
    } catch (e) {
      finished = false; $("#submit").disabled = false; toast(`Submit failed: ${e.message}. Your answers are saved – try again.`);
    }
  }

  function tick() {
    const left = Math.max(0, deadline - (Date.now() + skew));
    const m = Math.floor(left / 60000), s = Math.floor((left % 60000) / 1000);
    const t = $("#timer");
    if (t) { t.textContent = `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`; t.classList.toggle("low", left < 5 * 60000); }
    if (left <= 0) submit(true);
  }

  $("#submit").onclick = () => submit(false);
  const onHide = () => document.visibilityState === "hidden" && save();
  document.addEventListener("visibilitychange", onHide);
  const timers = [setInterval(tick, 1000), setInterval(save, AUTOSAVE_MS)];
  tick();
  cleanup = () => { timers.forEach(clearInterval); document.removeEventListener("visibilitychange", onHide); };
}

/* ------------------------------------------------------------------ tutor / staff */
const SAMPLE_QUESTIONS = JSON.stringify([
  { id: "q1", type: "mcq", text: "Which AWS feature keeps a synchronous standby database in a second AZ?", options: ["Read replica", "Multi-AZ", "Snapshots"], answer: 1, marks: 2 },
  { id: "q2", type: "mcq", text: "Which service sends the result e-mails?", options: ["SNS", "SES", "SQS"], answer: 1, marks: 1 },
  { id: "q3", type: "short", text: "Explain how SQS protects the database during the exam peak.", marks: 5 },
], null, 2);

const localInput = (d) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);

async function staffHome() {
  const [{ exams }, { assignments }] = await Promise.all([api("GET", "/exams"), api("GET", "/assignments")]);
  const now = new Date();
  return {
    html: `
    <div class="card"><h1>Exams</h1><div class="table-wrap"><table><tr><th>Exam</th><th>Window</th><th></th></tr>
      ${exams.map((e) => `<tr><td>${esc(e.title)}<div class="muted">${esc(e.course)} · ${e.duration_minutes} min</div></td>
        <td>${fmt(e.opens_at)}<br>${fmt(e.closes_at)}</td><td><a class="btn" href="#/results/${e.id}">Results</a></td></tr>`).join("")
        || `<tr><td colspan="3" class="muted">No exams yet.</td></tr>`}</table></div></div>
    <div class="card"><h2>Create exam</h2><form id="new-exam">
      <div class="grid"><div><label>Title</label><input name="title" required></div>
        <div><label>Course</label><input name="course" required placeholder="DSO303"></div>
        <div><label>Duration (minutes)</label><input name="duration" type="number" min="1" max="600" value="60" required></div>
        <div><label>Opens</label><input name="opens" type="datetime-local" value="${localInput(now)}" required></div>
        <div><label>Closes</label><input name="closes" type="datetime-local" value="${localInput(new Date(now.getTime() + 3 * 3600_000))}" required></div></div>
      <label>Questions (JSON: mcq needs options + answer index; short is marked by tutor)</label>
      <textarea name="questions" rows="12" style="font-family:ui-monospace,monospace">${esc(SAMPLE_QUESTIONS)}</textarea>
      <p><button>Create exam</button></p></form></div>
    <div class="card"><h2>Assignments</h2><div class="table-wrap"><table><tr><th>Assignment</th><th>Due</th><th>Submissions</th><th></th></tr>
      ${assignments.map((a) => `<tr><td>${esc(a.title)}<div class="muted">${esc(a.course)} · notifies ${esc(a.tutor_email)}</div></td>
        <td>${fmt(a.due_at)}</td><td>${a.submission_count}</td><td><a class="btn" href="#/submissions/${a.id}">View</a></td></tr>`).join("")
        || `<tr><td colspan="4" class="muted">No assignments yet.</td></tr>`}</table></div>
      <form id="new-asg"><h2 style="margin-top:14px">Create assignment</h2>
      <div class="grid"><div><label>Title</label><input name="title" required></div>
        <div><label>Course</label><input name="course" required></div>
        <div><label>Due</label><input name="due" type="datetime-local" value="${localInput(new Date(now.getTime() + 7 * 86400_000))}" required></div>
        <div><label>Notify tutor e-mail</label><input name="tutor_email" type="email" value="${esc(claims().email)}" required></div></div>
      <p><button>Create assignment</button></p></form></div>`,
    bind() {
      $("#new-exam").onsubmit = async (ev) => {
        ev.preventDefault();
        const f = new FormData(ev.target);
        try {
          await api("POST", "/exams", {
            title: f.get("title"), course: f.get("course"), duration_minutes: Number(f.get("duration")),
            opens_at: new Date(f.get("opens")).toISOString(), closes_at: new Date(f.get("closes")).toISOString(),
            questions: JSON.parse(f.get("questions")),
          });
          toast("Exam created"); router();
        } catch (e) { toast(e.message); }
      };
      $("#new-asg").onsubmit = async (ev) => {
        ev.preventDefault();
        const f = new FormData(ev.target);
        try {
          await api("POST", "/assignments", { title: f.get("title"), course: f.get("course"), due_at: new Date(f.get("due")).toISOString(), tutor_email: f.get("tutor_email") });
          toast("Assignment created"); router();
        } catch (e) { toast(e.message); }
      };
    },
  };
}

async function resultsPage(examId) {
  const [exam, { results }] = await Promise.all([api("GET", `/exams/${examId}`), api("GET", `/exams/${examId}/results`)]);
  const shortQs = exam.questions.filter((q) => q.type === "short");
  view.innerHTML = `<div class="card"><a href="#/">← Back</a><h1>${esc(exam.title)} – results</h1>
    <p class="muted">MCQs are auto-marked when a student submits. Enter short-answer marks, then release.</p>
    <p><button id="release">Release marked results & e-mail students</button></p>
    <div class="table-wrap"><table><tr><th>Student</th><th>MCQ</th><th>Short answers</th><th>Short mark</th><th>Status</th></tr>
    ${results.map((r) => `<tr><td>${esc(r.student_email)}</td><td>${r.mcq_score}/${r.mcq_max}</td>
      <td>${shortQs.map((q) => `<div><b>${esc(q.id)}</b>: ${esc(r.answers[q.id] || "—")}</div>`).join("") || "—"}</td>
      <td>${Number(r.sa_max) > 0 ? `<div class="row"><input style="width:70px" type="number" min="0" max="${r.sa_max}" step="0.5" value="${r.sa_score ?? ""}"
          data-student="${esc(r.student_id)}" ${r.released ? "disabled" : ""}> / ${r.sa_max}</div>` : "n/a"}</td>
      <td>${r.released ? `<span class="pill ok">Released</span>` : `<span class="pill warn">Not released</span>`}</td></tr>`).join("")
      || `<tr><td colspan="5" class="muted">No submissions marked yet.</td></tr>`}</table></div></div>`;
  view.querySelectorAll("[data-student]").forEach((input) => {
    input.onchange = async () => {
      try { await api("POST", `/exams/${examId}/marks`, { student_id: input.dataset.student, sa_score: Number(input.value) }); toast("Mark saved"); }
      catch (e) { toast(e.message); }
    };
  });
  $("#release").onclick = async () => {
    try {
      const r = await api("POST", `/exams/${examId}/release`);
      toast(`Released ${r.released} result(s); ${r.still_pending} still need short-answer marks.`);
      resultsPage(examId);
    } catch (e) { toast(e.message); }
  };
}

async function submissionsPage(assignmentId) {
  const { submissions } = await api("GET", `/assignments/${assignmentId}/submissions`);
  view.innerHTML = `<div class="card"><a href="#/">← Back</a><h1>Submissions</h1>
    <div class="table-wrap"><table><tr><th>Student</th><th>File</th><th>Size</th><th>Submitted</th><th></th></tr>
    ${submissions.map((s) => `<tr><td>${esc(s.student_email)}</td><td>${esc(s.filename)}</td><td>${(s.size_bytes / 1048576).toFixed(1)} MB</td>
      <td>${fmt(s.submitted_at)} ${s.late ? `<span class="pill bad">Late</span>` : ""}</td>
      <td><a class="btn" href="${esc(s.download_url)}">Download</a></td></tr>`).join("")
      || `<tr><td colspan="5" class="muted">No submissions yet.</td></tr>`}</table></div></div>`;
}

/* ------------------------------------------------------------------ admin */
async function adminHome() {
  const { users } = await api("GET", "/admin/users");
  return {
    html: `<div class="card"><h1>Users</h1>
      <form id="new-user" class="grid"><div><label>E-mail</label><input name="email" type="email" required></div>
        <div><label>Name</label><input name="name"></div>
        <div><label>Role</label><select name="role"><option>students</option><option>tutors</option><option>admins</option></select></div>
        <div><label>&nbsp;</label><button>Invite user</button></div></form>
      <div class="table-wrap" style="margin-top:12px"><table><tr><th>E-mail</th><th>Name</th><th>Role</th><th>Status</th></tr>
      ${users.map((u) => `<tr><td>${esc(u.email)}</td><td>${esc(u.name)}</td><td>${esc(u.role)}</td><td>${esc(u.status)}</td></tr>`).join("")}
      </table></div></div>`,
    bind() {
      $("#new-user").onsubmit = async (ev) => {
        ev.preventDefault();
        const f = new FormData(ev.target);
        try { await api("POST", "/admin/users", Object.fromEntries(f)); toast("Invitation e-mailed"); router(); }
        catch (e) { toast(e.message); }
      };
    },
  };
}

/* ------------------------------------------------------------------ boot */
window.addEventListener("hashchange", router);
handleCallback().catch((e) => toast(e.message)).finally(router);
