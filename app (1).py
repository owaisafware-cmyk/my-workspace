import os
import uuid
from flask import Flask, request, render_template_string, session, redirect, url_for, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "workspace_front_door_key_77"

MASTER_PIN = "1234"

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'png','jpg','jpeg','gif','webp','pdf','txt','doc','docx','xls','xlsx','csv','zip','mp3','mp4','mov'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///local_fallback.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ── MODELS ────────────────────────────────────────────────────────────────────

class Folder(db.Model):
    id    = db.Column(db.String(50), primary_key=True)
    name  = db.Column(db.String(150), nullable=False)
    color = db.Column(db.String(30), nullable=True, default='default')
    notes = db.relationship('WorkspaceNote', backref='folder', lazy=True)

class WorkspaceNote(db.Model):
    id        = db.Column(db.String(50),  primary_key=True)
    title     = db.Column(db.String(150), nullable=False)
    content   = db.Column(db.Text,        nullable=True)
    link      = db.Column(db.String(500), nullable=True)
    color     = db.Column(db.String(20),  nullable=True, default='default')
    tags      = db.Column(db.String(300), nullable=True, default='')   # comma-separated
    folder_id = db.Column(db.String(50),  db.ForeignKey('folder.id'), nullable=True)
    pinned    = db.Column(db.Boolean,     default=False)
    files     = db.relationship('NoteFile', backref='note', lazy=True, cascade='all, delete-orphan')

class NoteFile(db.Model):
    id       = db.Column(db.String(50),  primary_key=True)
    note_id  = db.Column(db.String(50),  db.ForeignKey('workspace_note.id'), nullable=False)
    filename = db.Column(db.String(300), nullable=False)
    original = db.Column(db.String(300), nullable=False)
    mimetype = db.Column(db.String(100), nullable=True)

with app.app_context():
    db.create_all()
    if not WorkspaceNote.query.first():
        welcome = WorkspaceNote(
            id=str(uuid.uuid4()),
            title="🌕 Welcome to Moon Workspace!",
            content="Your personal workspace is ready.\nUse folders to organise, tags to label, and search to find anything instantly.",
            link="",
            color="indigo",
            tags="welcome,guide"
        )
        db.session.add(welcome)
        db.session.commit()

# ── HELPERS ───────────────────────────────────────────────────────────────────

def allowed_file(f):
    return '.' in f and f.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

def save_files(files, note_id):
    for f in files:
        if f and f.filename and allowed_file(f.filename):
            ext = f.filename.rsplit('.',1)[1].lower()
            stored = f"{uuid.uuid4()}.{ext}"
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], stored))
            db.session.add(NoteFile(
                id=str(uuid.uuid4()), note_id=note_id,
                filename=stored, original=secure_filename(f.filename),
                mimetype=f.mimetype or ''
            ))

# ── LOGIN TEMPLATE ────────────────────────────────────────────────────────────

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moon Workspace — Login</title>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:linear-gradient(160deg,#07090f 0%,#0f1729 50%,#1a1040 100%);min-height:100vh;display:flex;justify-content:center;align-items:center;font-family:'Sora',sans-serif;padding:20px;position:relative;overflow:hidden}
.stars{position:fixed;inset:0;pointer-events:none}
.star{position:absolute;background:#fff;border-radius:50%;animation:twinkle 3s infinite alternate}
@keyframes twinkle{0%{opacity:.2}100%{opacity:.9}}
.card{background:rgba(15,23,42,.85);backdrop-filter:blur(20px);width:100%;max-width:400px;padding:48px 36px;border-radius:28px;box-shadow:0 0 60px rgba(139,92,246,.15),0 24px 60px rgba(0,0,0,.6);border:1px solid rgba(139,92,246,.2);text-align:center;position:relative;z-index:1}
.moon-logo{font-size:64px;margin-bottom:12px;filter:drop-shadow(0 0 20px rgba(250,220,100,.5));animation:moonpulse 4s ease-in-out infinite}
@keyframes moonpulse{0%,100%{filter:drop-shadow(0 0 16px rgba(250,220,100,.4))}50%{filter:drop-shadow(0 0 32px rgba(250,220,100,.8))}}
h2{color:#f1f5f9;font-size:22px;font-weight:700;margin-bottom:6px}
p{color:#94a3b8;font-size:14px;margin-bottom:28px;line-height:1.6}
input[type=password]{width:100%;background:rgba(255,255,255,.06);border:1.5px solid rgba(139,92,246,.3);border-radius:14px;padding:16px;font-size:22px;color:#f1f5f9;outline:none;text-align:center;letter-spacing:10px;transition:.2s;margin-bottom:16px;font-family:'Sora',sans-serif}
input[type=password]:focus{border-color:#8b5cf6;box-shadow:0 0 0 3px rgba(139,92,246,.2)}
.btn{width:100%;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;border:none;border-radius:14px;padding:16px;font-size:15px;font-weight:700;cursor:pointer;font-family:'Sora',sans-serif;transition:.2s}
.btn:hover{opacity:.9;transform:translateY(-1px)}
.alert{background:rgba(239,68,68,.15);color:#f87171;padding:12px;border-radius:10px;font-size:13px;font-weight:600;margin-bottom:16px;border:1px solid rgba(239,68,68,.2)}
</style>
</head>
<body>
<div class="stars" id="stars"></div>
<div class="card">
  <div class="moon-logo">🌕</div>
  <h2>Moon Workspace</h2>
  <p>Enter your PIN to unlock your personal space</p>
  {% if error %}<div class="alert">{{ error }}</div>{% endif %}
  <form action="/login" method="POST">
    <input type="password" name="pin" placeholder="••••" autocomplete="off" autofocus required>
    <button type="submit" class="btn">Unlock →</button>
  </form>
</div>
<script>
const s=document.getElementById('stars');
for(let i=0;i<80;i++){
  const d=document.createElement('div');
  d.className='star';
  const sz=Math.random()*2.5+.5;
  d.style.cssText=`width:${sz}px;height:${sz}px;top:${Math.random()*100}%;left:${Math.random()*100}%;animation-delay:${Math.random()*3}s;animation-duration:${2+Math.random()*3}s`;
  s.appendChild(d);
}
</script>
</body>
</html>
"""

# ── MAIN TEMPLATE ─────────────────────────────────────────────────────────────

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moon Workspace</title>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#f0f2f8;--surface:#fff;--surface2:#f8fafc;--border:#e2e8f0;
  --text:#0f172a;--text2:#64748b;--accent:#6366f1;--accent2:#8b5cf6;
  --shadow:rgba(99,102,241,.08);--danger:#ef4444;--r:18px;
}
body.dark{
  --bg:#07090f;--surface:#0f1729;--surface2:#1a2340;--border:#1e2d4a;
  --text:#f1f5f9;--text2:#94a3b8;--shadow:rgba(0,0,0,.5);
}
*{box-sizing:border-box;margin:0;padding:0;font-family:'Sora',sans-serif}
body{background:var(--bg);min-height:100vh;padding:24px 16px 60px;transition:background .3s}

/* ── TOPBAR ── */
.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;gap:12px;flex-wrap:wrap}
.logo{display:flex;align-items:center;gap:10px;text-decoration:none}
.moon-icon{font-size:36px;filter:drop-shadow(0 0 8px rgba(250,220,100,.5));animation:mp 4s ease-in-out infinite}
@keyframes mp{0%,100%{filter:drop-shadow(0 0 6px rgba(250,220,100,.3))}50%{filter:drop-shadow(0 0 18px rgba(250,220,100,.7))}}
.logo-text{font-size:18px;font-weight:700;color:var(--text)}
.topbar-right{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.ibtn{background:var(--surface);border:1px solid var(--border);color:var(--text2);padding:8px 14px;border-radius:12px;cursor:pointer;font-size:12px;font-weight:600;text-decoration:none;white-space:nowrap;transition:.2s;display:inline-flex;align-items:center;gap:5px}
.ibtn:hover{background:var(--surface2);color:var(--text)}
.ibtn.danger{color:var(--danger)}
.ibtn.danger:hover{background:rgba(239,68,68,.1)}

/* ── SEARCH BAR ── */
.search-wrap{position:relative;margin-bottom:18px}
.search-wrap input{width:100%;background:var(--surface);border:1.5px solid var(--border);border-radius:14px;padding:12px 16px 12px 44px;font-size:14px;color:var(--text);outline:none;transition:.2s;font-family:'Sora',sans-serif}
.search-wrap input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(99,102,241,.12)}
.search-wrap input::placeholder{color:var(--text2)}
.search-icon{position:absolute;left:14px;top:50%;transform:translateY(-50%);font-size:18px;pointer-events:none;opacity:.5}
.search-clear{position:absolute;right:12px;top:50%;transform:translateY(-50%);background:none;border:none;color:var(--text2);font-size:18px;cursor:pointer;display:none;padding:0;line-height:1}

/* ── TAG FILTER BAR ── */
.tag-bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px;align-items:center}
.tag-pill{padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600;cursor:pointer;border:1.5px solid var(--border);background:var(--surface);color:var(--text2);transition:.2s;white-space:nowrap}
.tag-pill:hover,.tag-pill.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.tag-label{font-size:12px;font-weight:600;color:var(--text2);white-space:nowrap}

/* ── FOLDERS ── */
.folders-section{margin-bottom:22px}
.folders-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.sec-title{font-size:12px;font-weight:700;color:var(--text2);text-transform:uppercase;letter-spacing:.08em}
.folders-grid{display:flex;gap:10px;flex-wrap:wrap}
.folder-chip{display:flex;align-items:center;gap:7px;padding:8px 16px;border-radius:14px;border:1.5px solid var(--border);background:var(--surface);cursor:pointer;font-size:13px;font-weight:600;color:var(--text);transition:.2s}
.folder-chip:hover{border-color:var(--accent);color:var(--accent)}
.folder-chip.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.folder-count{background:rgba(255,255,255,.25);padding:1px 7px;border-radius:20px;font-size:11px}
.folder-chip:not(.active) .folder-count{background:var(--surface2);color:var(--text2)}
.folder-add-btn{background:none;border:1.5px dashed var(--border);color:var(--text2);padding:8px 14px;border-radius:14px;font-size:12px;font-weight:600;cursor:pointer;transition:.2s}
.folder-add-btn:hover{border-color:var(--accent);color:var(--accent)}

/* ── FOLDER FORM ── */
.folder-form{background:var(--surface);border:1.5px solid var(--accent);border-radius:var(--r);padding:18px;margin-bottom:18px;display:none}
.folder-form.open{display:block}

/* ── CARDS ── */
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);margin-bottom:16px;overflow:hidden;box-shadow:0 4px 20px var(--shadow);transition:transform .2s,box-shadow .2s;animation:fadeup .3s ease}
@keyframes fadeup{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.card:hover{transform:translateY(-2px);box-shadow:0 8px 28px var(--shadow)}
.card[data-hidden="true"]{display:none!important}
.card-stripe{height:4px}
.color-default .card-stripe{background:linear-gradient(90deg,#6366f1,#8b5cf6)}
.color-rose    .card-stripe{background:linear-gradient(90deg,#f43f5e,#ec4899)}
.color-amber   .card-stripe{background:linear-gradient(90deg,#f59e0b,#ef4444)}
.color-emerald .card-stripe{background:linear-gradient(90deg,#10b981,#06b6d4)}
.color-sky     .card-stripe{background:linear-gradient(90deg,#0ea5e9,#6366f1)}
.color-indigo  .card-stripe{background:linear-gradient(90deg,#6366f1,#a855f7)}
.card-body{padding:20px}
.card-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}
.card-title{font-size:16px;font-weight:700;color:var(--text);flex:1}
.card-meta{display:flex;align-items:center;gap:6px;margin-bottom:8px;flex-wrap:wrap}
.folder-badge{font-size:11px;padding:2px 8px;background:rgba(99,102,241,.12);color:var(--accent);border-radius:8px;font-weight:600}
.tag-badge{font-size:11px;padding:2px 8px;background:var(--surface2);color:var(--text2);border-radius:8px;font-weight:500;border:1px solid var(--border)}
.card-actions{display:flex;gap:4px;margin-left:10px;flex-shrink:0}
.act{background:var(--surface2);border:1px solid var(--border);color:var(--text2);width:32px;height:32px;border-radius:10px;cursor:pointer;font-size:13px;display:flex;align-items:center;justify-content:center;transition:.2s}
.act:hover{background:var(--accent);color:#fff;border-color:var(--accent)}
.act.del:hover{background:var(--danger);border-color:var(--danger)}
.card-content{font-size:13px;color:var(--text);line-height:1.75;white-space:pre-wrap;margin-bottom:12px}
.card-link{display:inline-flex;align-items:center;gap:5px;font-size:12px;color:var(--accent);font-weight:600;text-decoration:none;background:rgba(99,102,241,.1);padding:5px 10px;border-radius:8px;word-break:break-all}
.card-link:hover{background:rgba(99,102,241,.2)}
.no-results{text-align:center;padding:40px 20px;color:var(--text2);font-size:14px}

/* ── FILES ── */
.files-section{margin-top:14px;border-top:1px solid var(--border);padding-top:12px}
.files-label{font-size:11px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px}
.files-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(100px,1fr));gap:8px}
.fthumb{position:relative;border-radius:10px;overflow:hidden;border:1px solid var(--border);background:var(--surface2);aspect-ratio:1;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:.2s}
.fthumb:hover{border-color:var(--accent)}
.fthumb img{width:100%;height:100%;object-fit:cover}
.fthumb .ficon{font-size:28px}
.fname{font-size:10px;color:var(--text2);text-align:center;padding:3px 4px;background:var(--surface);position:absolute;bottom:0;left:0;right:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fdel{position:absolute;top:3px;right:3px;background:rgba(0,0,0,.6);color:#fff;border:none;border-radius:5px;width:20px;height:20px;font-size:11px;cursor:pointer;display:none;align-items:center;justify-content:center}
.fthumb:hover .fdel{display:flex}

/* ── DROP ZONE ── */
.drop-zone{border:2px dashed var(--border);border-radius:12px;padding:16px;text-align:center;cursor:pointer;transition:.2s;color:var(--text2);font-size:12px;font-weight:500;margin-top:12px}
.drop-zone:hover,.drop-zone.dragover{border-color:var(--accent);background:rgba(99,102,241,.05);color:var(--accent)}
.drop-zone input{display:none}
.dz-prev{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.dz-chip{background:var(--surface2);border:1px solid var(--border);border-radius:7px;padding:3px 8px;font-size:11px;color:var(--text)}

/* ── FORMS ── */
.frow{margin-bottom:12px}
.flabel{font-size:11px;font-weight:600;color:var(--text2);margin-bottom:5px;display:block;text-transform:uppercase;letter-spacing:.06em}
input[type=text],textarea,select{width:100%;background:var(--surface2);border:1.5px solid var(--border);border-radius:10px;padding:10px 13px;font-size:13px;color:var(--text);outline:none;font-family:'Sora',sans-serif;transition:.2s}
input[type=text]:focus,textarea:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(99,102,241,.12)}
textarea{min-height:80px;resize:vertical;line-height:1.6}
select{cursor:pointer;appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%2394a3b8' fill='none' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 12px center}

/* ── COLOR PICKER ── */
.cpick{display:flex;gap:7px;flex-wrap:wrap}
.cdot{width:26px;height:26px;border-radius:50%;cursor:pointer;border:2px solid transparent;transition:.2s}
.cdot:hover,.cdot.active{border-color:var(--text);transform:scale(1.15)}
.cdot.cp-default{background:linear-gradient(135deg,#6366f1,#8b5cf6)}
.cdot.cp-rose{background:linear-gradient(135deg,#f43f5e,#ec4899)}
.cdot.cp-amber{background:linear-gradient(135deg,#f59e0b,#ef4444)}
.cdot.cp-emerald{background:linear-gradient(135deg,#10b981,#06b6d4)}
.cdot.cp-sky{background:linear-gradient(135deg,#0ea5e9,#6366f1)}
.cdot.cp-indigo{background:linear-gradient(135deg,#6366f1,#a855f7)}

/* ── BUTTONS ── */
.brow{display:flex;gap:8px;margin-top:12px}
.btn{padding:10px 18px;border-radius:12px;font-size:13px;font-weight:700;cursor:pointer;border:none;font-family:'Sora',sans-serif;transition:.2s;flex:1;text-align:center}
.btn-p{background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff}
.btn-p:hover{opacity:.9;transform:translateY(-1px)}
.btn-g{background:transparent;color:var(--text2);border:1.5px solid var(--border)}
.btn-g:hover{background:var(--surface2)}

/* ── ADD CARD BUTTON ── */
.add-btn{width:100%;background:var(--surface);border:2px dashed var(--border);color:var(--text2);padding:16px;border-radius:var(--r);font-size:14px;font-weight:600;cursor:pointer;display:flex;justify-content:center;align-items:center;gap:8px;transition:.2s;margin-bottom:16px}
.add-btn:hover{border-color:var(--accent);color:var(--accent)}
.add-card{background:var(--surface);border:1.5px solid var(--accent);border-radius:var(--r);padding:22px;margin-bottom:16px;box-shadow:0 8px 30px rgba(99,102,241,.12)}

/* ── ALERTS ── */
.alert{padding:12px 16px;border-radius:12px;font-size:13px;font-weight:600;margin-bottom:16px;text-align:center}
.alert-e{background:rgba(239,68,68,.12);color:#ef4444;border:1px solid rgba(239,68,68,.2)}
.alert-s{background:rgba(34,197,94,.12);color:#22c55e;border:1px solid rgba(34,197,94,.2)}

/* ── LIGHTBOX ── */
.lbox{display:none;position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:999;align-items:center;justify-content:center;padding:20px}
.lbox.open{display:flex}
.lbox img{max-width:90vw;max-height:85vh;border-radius:12px}
.lbox-close{position:fixed;top:18px;right:18px;background:rgba(255,255,255,.15);border:none;color:#fff;width:38px;height:38px;border-radius:50%;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center}

/* ── MOBILE ── */
@media(max-width:600px){
  body{padding:16px 12px 60px}
  .topbar{gap:10px}
  .logo-text{font-size:16px}
  .topbar-right{gap:6px}
  .ibtn{padding:7px 10px;font-size:11px}
  .card-body{padding:16px}
  .card-title{font-size:15px}
  .add-card{padding:16px}
  .folders-grid{gap:8px}
  .folder-chip{padding:7px 12px;font-size:12px}
  .brow{flex-direction:column}
  .files-grid{grid-template-columns:repeat(auto-fill,minmax(80px,1fr))}
}
@media(max-width:380px){
  .moon-icon{font-size:28px}
  .logo-text{font-size:14px}
}
</style>
</head>
<body>

<div style="max-width:700px;margin:0 auto">

  <!-- TOPBAR -->
  <div class="topbar">
    <div class="logo">
      <div class="moon-icon">🌕</div>
      <div class="logo-text">Moon Workspace</div>
    </div>
    <div class="topbar-right">
      <button class="ibtn" id="themeToggle">🌙 Dark</button>
      <a href="/logout" class="ibtn danger">🔒 Lock</a>
    </div>
  </div>

  {% if error %}<div class="alert alert-e">{{ error }}</div>{% endif %}
  {% if success %}<div class="alert alert-s">{{ success }}</div>{% endif %}

  <!-- SEARCH BAR -->
  <div class="search-wrap">
    <span class="search-icon">🔍</span>
    <input type="text" id="searchInput" placeholder="Search cards by title, content or tag..." oninput="doSearch(this.value)">
    <button class="search-clear" id="searchClear" onclick="clearSearch()">✕</button>
  </div>

  <!-- TAG FILTER -->
  {% set all_tags = [] %}
  {% for note in notes %}{% for t in note.tags.split(',') if t.strip() %}{% if t.strip() not in all_tags %}{% set _ = all_tags.append(t.strip()) %}{% endif %}{% endfor %}{% endfor %}
  {% if all_tags %}
  <div class="tag-bar">
    <span class="tag-label">🏷️ Tags:</span>
    <div class="tag-pill active" onclick="filterTag('',this)">All</div>
    {% for tag in all_tags %}
    <div class="tag-pill" onclick="filterTag('{{ tag }}',this)">{{ tag }}</div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- FOLDERS -->
  <div class="folders-section">
    <div class="folders-header">
      <span class="sec-title">📂 Folders</span>
      <button class="folder-add-btn" onclick="toggleFolderForm()">+ New Folder</button>
    </div>

    <!-- New folder form -->
    <div class="folder-form" id="folderForm">
      <form action="/folder" method="POST">
        <input type="hidden" name="action" value="add">
        <div class="frow"><input type="text" name="name" placeholder="Folder name..." required></div>
        <div class="brow">
          <button type="submit" class="btn btn-p">Create Folder</button>
          <button type="button" class="btn btn-g" onclick="toggleFolderForm()">Cancel</button>
        </div>
      </form>
    </div>

    <div class="folders-grid">
      <div class="folder-chip {% if not active_folder %}active{% endif %}" onclick="location.href='/'">
        🌕 All
        <span class="folder-count">{{ notes|length }}</span>
      </div>
      {% for folder in folders %}
      <div class="folder-chip {% if active_folder == folder.id %}active{% endif %}" onclick="location.href='/folder/{{ folder.id }}'">
        📂 {{ folder.name }}
        <span class="folder-count">{{ folder.notes|length }}</span>
      </div>
      {% endfor %}
    </div>
  </div>

  <!-- CARDS -->
  <div id="cardsContainer">
  {% set sorted_notes = notes|sort(attribute='pinned', reverse=True) %}
  {% for note in sorted_notes %}
  <div class="card color-{{ note.color or 'default' }}"
       id="card-{{ note.id }}"
       data-title="{{ note.title|lower }}"
       data-content="{{ (note.content or '')|lower }}"
       data-tags="{{ note.tags or '' }}"
       data-hidden="false">
    <div class="card-stripe"></div>
    <div class="card-body">

      <!-- VIEW MODE -->
      <div id="view-{{ note.id }}">
        <div class="card-header">
          <div>
            <div class="card-title">{% if note.pinned %}📌 {% endif %}{{ note.title }}</div>
            <div class="card-meta" style="margin-top:6px">
              {% if note.folder %}
              <span class="folder-badge">📂 {{ note.folder.name }}</span>
              {% endif %}
              {% for t in note.tags.split(',') if t.strip() %}
              <span class="tag-badge">{{ t.strip() }}</span>
              {% endfor %}
            </div>
          </div>
          <div class="card-actions">
            <button class="act" onclick="toggleEdit('{{ note.id }}')" title="Edit">✏️</button>
            <form action="/action" method="POST" style="display:inline">
              <input type="hidden" name="action_type" value="delete">
              <input type="hidden" name="note_id" value="{{ note.id }}">
              <button type="submit" class="act del" onclick="return confirm('Delete this card?')">🗑️</button>
            </form>
          </div>
        </div>
        {% if note.content %}<div class="card-content">{{ note.content }}</div>{% endif %}
        {% if note.link %}<a href="{{ note.link }}" target="_blank" class="card-link">🔗 {{ note.link }}</a>{% endif %}

        <!-- ATTACHMENTS -->
        {% if note.files %}
        <div class="files-section">
          <div class="files-label">📎 Attachments ({{ note.files|length }})</div>
          <div class="files-grid">
            {% for f in note.files %}
            <div class="fthumb" {% if f.mimetype and f.mimetype.startswith('image') %}onclick="openLB('/uploads/{{ f.filename }}')"{% else %}onclick="window.open('/uploads/{{ f.filename }}','_blank')"{% endif %}>
              {% if f.mimetype and f.mimetype.startswith('image') %}
              <img src="/uploads/{{ f.filename }}" alt="{{ f.original }}">
              {% else %}
              <div class="ficon">{{ '📄' if 'pdf' in (f.mimetype or '') else '🎵' if 'audio' in (f.mimetype or '') else '🎬' if 'video' in (f.mimetype or '') else '📊' if ('xls' in f.original or 'csv' in f.original) else '📝' }}</div>
              {% endif %}
              <div class="fname">{{ f.original }}</div>
              <form action="/action" method="POST" style="position:absolute;top:3px;right:3px">
                <input type="hidden" name="action_type" value="delete_file">
                <input type="hidden" name="file_id" value="{{ f.id }}">
                <input type="hidden" name="note_id" value="{{ note.id }}">
                <button type="submit" class="fdel" onclick="return confirm('Remove?')">✕</button>
              </form>
            </div>
            {% endfor %}
          </div>
        </div>
        {% endif %}

        <!-- QUICK FILE UPLOAD -->
        <form action="/action" method="POST" enctype="multipart/form-data">
          <input type="hidden" name="action_type" value="add_files">
          <input type="hidden" name="note_id" value="{{ note.id }}">
          <label class="drop-zone" id="dz-{{ note.id }}">
            <div>📎 Click or drop files to attach</div>
            <input type="file" name="files" multiple accept="image/*,.pdf,.txt,.doc,.docx,.xls,.xlsx,.csv,.zip,.mp3,.mp4,.mov" onchange="prevFiles(this,'{{ note.id }}')">
          </label>
          <div class="dz-prev" id="prev-{{ note.id }}"></div>
          <div id="upbtn-{{ note.id }}" style="display:none;margin-top:8px">
            <button type="submit" class="btn btn-p" style="width:100%">⬆️ Upload</button>
          </div>
        </form>
      </div>

      <!-- EDIT MODE -->
      <div id="edit-{{ note.id }}" style="display:none">
        <form action="/action" method="POST">
          <input type="hidden" name="action_type" value="edit">
          <input type="hidden" name="note_id" value="{{ note.id }}">
          <div class="frow"><label class="flabel">Title</label><input type="text" name="title" value="{{ note.title }}" required></div>
          <div class="frow"><label class="flabel">Content</label><textarea name="content">{{ note.content }}</textarea></div>
          <div class="frow"><label class="flabel">Link</label><input type="text" name="link" value="{{ note.link }}" placeholder="https://..."></div>
          <div class="frow">
            <label class="flabel">Tags (comma separated)</label>
            <input type="text" name="tags" value="{{ note.tags }}" placeholder="work, personal, finance">
          </div>
          <div class="frow">
            <label class="flabel">Folder</label>
            <select name="folder_id">
              <option value="">— No Folder —</option>
              {% for folder in folders %}
              <option value="{{ folder.id }}" {% if note.folder_id == folder.id %}selected{% endif %}>📂 {{ folder.name }}</option>
              {% endfor %}
            </select>
          </div>
          <div class="frow">
            <label class="flabel">Card Colour</label>
            <div class="cpick" id="cpe-{{ note.id }}">
              {% for c in ['default','rose','amber','emerald','sky','indigo'] %}
              <div class="cdot cp-{{ c }} {% if (note.color or 'default')==c %}active{% endif %}" onclick="pickC('cpe-{{ note.id }}','{{ c }}',this)"></div>
              {% endfor %}
            </div>
            <input type="hidden" name="color" id="ce-{{ note.id }}" value="{{ note.color or 'default' }}">
          </div>
          <div class="brow">
            <button type="submit" class="btn btn-p">💾 Save</button>
            <button type="button" class="btn btn-g" onclick="toggleEdit('{{ note.id }}')">Cancel</button>
          </div>
        </form>
      </div>

    </div>
  </div>
  {% endfor %}
  </div>

  <div id="noResults" class="no-results" style="display:none">🔍 No cards match your search</div>

  <!-- ADD NEW CARD -->
  <button class="add-btn" id="addBtn" onclick="showAdd()">➕ Add New Card</button>

  <div id="addCard" class="add-card" style="display:none">
    <div style="font-size:16px;font-weight:700;color:var(--text);margin-bottom:16px">✨ New Card</div>
    <form action="/action" method="POST" enctype="multipart/form-data">
      <input type="hidden" name="action_type" value="add">
      <div class="frow"><label class="flabel">Title *</label><input type="text" name="title" placeholder="Card title..." required></div>
      <div class="frow"><label class="flabel">Content</label><textarea name="content" placeholder="Write anything..."></textarea></div>
      <div class="frow"><label class="flabel">Link</label><input type="text" name="link" placeholder="https://..."></div>
      <div class="frow">
        <label class="flabel">Tags (comma separated)</label>
        <input type="text" name="tags" placeholder="work, personal, finance">
      </div>
      <div class="frow">
        <label class="flabel">Folder</label>
        <select name="folder_id">
          <option value="">— No Folder —</option>
          {% for folder in folders %}
          <option value="{{ folder.id }}">📂 {{ folder.name }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="frow">
        <label class="flabel">Attach Files / Photos</label>
        <label class="drop-zone" id="dz-new">
          <div>🖼️ Click to browse or drag & drop</div>
          <small style="opacity:.6;display:block;margin-top:3px">Images, PDF, Word, Excel, ZIP — max 50 MB</small>
          <input type="file" name="files" multiple accept="image/*,.pdf,.txt,.doc,.docx,.xls,.xlsx,.csv,.zip,.mp3,.mp4,.mov" onchange="prevFiles(this,'new')">
        </label>
        <div class="dz-prev" id="prev-new"></div>
      </div>
      <div class="frow">
        <label class="flabel">Card Colour</label>
        <div class="cpick" id="cpa">
          {% for c in ['default','rose','amber','emerald','sky','indigo'] %}
          <div class="cdot cp-{{ c }} {% if c=='default' %}active{% endif %}" onclick="pickC('cpa','{{ c }}',this)"></div>
          {% endfor %}
        </div>
        <input type="hidden" name="color" id="ca" value="default">
      </div>
      <div class="brow">
        <button type="submit" class="btn btn-p">➕ Add Card</button>
        <button type="button" class="btn btn-g" onclick="hideAdd()">Cancel</button>
      </div>
    </form>
  </div>

</div>

<!-- LIGHTBOX -->
<div class="lbox" id="lbox" onclick="closeLB()">
  <button class="lbox-close" onclick="closeLB()">✕</button>
  <img id="lbox-img" src="" alt="">
</div>

<script>
// Theme
const tb = document.getElementById('themeToggle');
function applyTheme(t){document.body.classList.toggle('dark',t==='dark');tb.innerHTML=t==='dark'?'☀️ Light':'🌙 Dark';}
applyTheme(localStorage.getItem('theme')||'light');
tb.addEventListener('click',()=>{const t=document.body.classList.contains('dark')?'light':'dark';localStorage.setItem('theme',t);applyTheme(t);});

// Edit toggle
function toggleEdit(id){
  const v=document.getElementById('view-'+id),e=document.getElementById('edit-'+id);
  v.style.display=v.style.display==='none'?'block':'none';
  e.style.display=e.style.display==='none'?'block':'none';
}

// Add card
function showAdd(){document.getElementById('addCard').style.display='block';document.getElementById('addBtn').style.display='none';document.getElementById('addCard').scrollIntoView({behavior:'smooth'});}
function hideAdd(){document.getElementById('addCard').style.display='none';document.getElementById('addBtn').style.display='flex';}

// Color picker
function pickC(cid,name,dot){
  document.querySelectorAll('#'+cid+' .cdot').forEach(d=>d.classList.remove('active'));
  dot.classList.add('active');
  const inp=document.getElementById(cid.replace('cpe-','ce-').replace('cpa','ca'));
  if(inp)inp.value=name;
}

// File preview
function prevFiles(input,id){
  const prev=document.getElementById('prev-'+id);
  prev.innerHTML='';
  const ub=document.getElementById('upbtn-'+id);
  if(ub&&input.files.length)ub.style.display='block';
  Array.from(input.files).forEach(f=>{
    const c=document.createElement('div');c.className='dz-chip';
    c.innerHTML=(f.type.startsWith('image')?'🖼️':'📎')+' '+f.name;
    prev.appendChild(c);
  });
  const dz=document.getElementById('dz-'+id);
  if(dz&&input.files.length)dz.style.borderColor='var(--accent)';
}

// Drag & drop
document.querySelectorAll('.drop-zone').forEach(z=>{
  z.addEventListener('dragover',e=>{e.preventDefault();z.classList.add('dragover');});
  z.addEventListener('dragleave',()=>z.classList.remove('dragover'));
  z.addEventListener('drop',e=>{
    e.preventDefault();z.classList.remove('dragover');
    const inp=z.querySelector('input[type=file]');
    if(inp){inp.files=e.dataTransfer.files;inp.dispatchEvent(new Event('change'));}
  });
});

// Folder form
function toggleFolderForm(){
  const f=document.getElementById('folderForm');
  f.classList.toggle('open');
}

// SEARCH
let activeTag='';
function doSearch(q){
  q=q.trim().toLowerCase();
  const clr=document.getElementById('searchClear');
  clr.style.display=q?'block':'none';
  filterCards(q,activeTag);
}
function clearSearch(){
  document.getElementById('searchInput').value='';
  document.getElementById('searchClear').style.display='none';
  filterCards('',activeTag);
}

// TAG FILTER
function filterTag(tag,el){
  document.querySelectorAll('.tag-pill').forEach(p=>p.classList.remove('active'));
  el.classList.add('active');
  activeTag=tag;
  const q=document.getElementById('searchInput').value.trim().toLowerCase();
  filterCards(q,tag);
}

// COMBINED FILTER
function filterCards(q,tag){
  let visible=0;
  document.querySelectorAll('.card').forEach(card=>{
    const title=card.dataset.title||'';
    const content=card.dataset.content||'';
    const tags=card.dataset.tags||'';
    const matchQ=!q||(title.includes(q)||content.includes(q)||tags.includes(q));
    const matchTag=!tag||tags.split(',').map(t=>t.trim()).includes(tag);
    const show=matchQ&&matchTag;
    card.dataset.hidden=show?'false':'true';
    if(show)visible++;
  });
  document.getElementById('noResults').style.display=visible===0?'block':'none';
}

// Lightbox
function openLB(src){document.getElementById('lbox-img').src=src;document.getElementById('lbox').classList.add('open');document.body.style.overflow='hidden';}
function closeLB(){document.getElementById('lbox').classList.remove('open');document.body.style.overflow='';}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeLB();});
</script>
</body>
</html>
"""

# ── ROUTES ────────────────────────────────────────────────────────────────────

def get_context(active_folder=None):
    folders = Folder.query.all()
    if active_folder:
        notes = WorkspaceNote.query.filter_by(folder_id=active_folder).all()
    else:
        notes = WorkspaceNote.query.all()
    return dict(folders=folders, notes=notes, active_folder=active_folder, error='', success='')

@app.route('/')
def index():
    if not session.get('authenticated'):
        return render_template_string(LOGIN_TEMPLATE, error='')
    return render_template_string(HTML_TEMPLATE, **get_context())

@app.route('/folder/<folder_id>')
def view_folder(folder_id):
    if not session.get('authenticated'):
        return redirect(url_for('index'))
    return render_template_string(HTML_TEMPLATE, **get_context(active_folder=folder_id))

@app.route('/folder', methods=['POST'])
def handle_folder():
    if not session.get('authenticated'):
        return redirect(url_for('index'))
    action = request.form.get('action')
    if action == 'add':
        name = request.form.get('name','').strip()
        if name:
            db.session.add(Folder(id=str(uuid.uuid4()), name=name))
            db.session.commit()
    elif action == 'delete':
        fid = request.form.get('folder_id')
        folder = Folder.query.get(fid)
        if folder:
            for n in folder.notes:
                n.folder_id = None
            db.session.delete(folder)
            db.session.commit()
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    if request.form.get('pin') == MASTER_PIN:
        session['authenticated'] = True
        return redirect(url_for('index'))
    return render_template_string(LOGIN_TEMPLATE, error='❌ Wrong PIN. Try again.')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if not session.get('authenticated'):
        abort(403)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/action', methods=['POST'])
def handle_action():
    if not session.get('authenticated'):
        return redirect(url_for('index'))
    action = request.form.get('action_type')

    if action == 'add':
        nid = str(uuid.uuid4())
        note = WorkspaceNote(
            id=nid,
            title=request.form.get('title','Untitled'),
            content=request.form.get('content',''),
            link=request.form.get('link',''),
            color=request.form.get('color','default'),
            tags=request.form.get('tags',''),
            folder_id=request.form.get('folder_id') or None
        )
        db.session.add(note)
        db.session.flush()
        save_files(request.files.getlist('files'), nid)
        db.session.commit()

    elif action == 'edit':
        nid = request.form.get('note_id')
        note = WorkspaceNote.query.get(nid)
        if note:
            note.title     = request.form.get('title', note.title)
            note.content   = request.form.get('content', note.content)
            note.link      = request.form.get('link', note.link)
            note.color     = request.form.get('color', note.color)
            note.tags      = request.form.get('tags', note.tags)
            note.folder_id = request.form.get('folder_id') or None
            db.session.commit()

    elif action == 'delete':
        nid = request.form.get('note_id')
        note = WorkspaceNote.query.get(nid)
        if note:
            for f in note.files:
                fp = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
                if os.path.exists(fp): os.remove(fp)
            db.session.delete(note)
            db.session.commit()

    elif action == 'add_files':
        nid = request.form.get('note_id')
        note = WorkspaceNote.query.get(nid)
        if note:
            save_files(request.files.getlist('files'), nid)
            db.session.commit()

    elif action == 'delete_file':
        fid = request.form.get('file_id')
        nf = NoteFile.query.get(fid)
        if nf:
            fp = os.path.join(app.config['UPLOAD_FOLDER'], nf.filename)
            if os.path.exists(fp): os.remove(fp)
            db.session.delete(nf)
            db.session.commit()

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
