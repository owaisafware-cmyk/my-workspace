import os
import uuid
from flask import Flask, request, render_template_string, session, redirect, url_for, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "workspace_front_door_key_77"

# 🔒 MASTER PIN
MASTER_PIN = "1234"

# 📁 FILE UPLOAD SETTINGS
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'txt', 'doc', 'docx', 'xls', 'xlsx', 'csv', 'zip', 'mp3', 'mp4', 'mov'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max upload
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///local_fallback.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ─── MODELS ───────────────────────────────────────────────────────────────────

class WorkspaceNote(db.Model):
    id       = db.Column(db.String(50),  primary_key=True)
    title    = db.Column(db.String(150), nullable=False)
    content  = db.Column(db.Text,        nullable=True)
    link     = db.Column(db.String(500), nullable=True)
    color    = db.Column(db.String(20),  nullable=True, default='default')
    files    = db.relationship('NoteFile', backref='note', lazy=True, cascade='all, delete-orphan')

class NoteFile(db.Model):
    id          = db.Column(db.String(50),  primary_key=True)
    note_id     = db.Column(db.String(50),  db.ForeignKey('workspace_note.id'), nullable=False)
    filename    = db.Column(db.String(300), nullable=False)   # stored filename (uuid-based)
    original    = db.Column(db.String(300), nullable=False)   # original filename
    mimetype    = db.Column(db.String(100), nullable=True)

with app.app_context():
    db.create_all()
    if not WorkspaceNote.query.first():
        welcome = WorkspaceNote(
            id=str(uuid.uuid4()),
            title="📌 Welcome to Permanent Storage!",
            content="Your database connection is active. Everything you add now will stay saved forever!\n\nTry adding files, photos, or links to any card.",
            link="https://www.google.com",
            color="indigo"
        )
        db.session.add(welcome)
        db.session.commit()

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_image(filename):
    return filename.rsplit('.', 1)[-1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# ─── TEMPLATES ────────────────────────────────────────────────────────────────

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Workspace Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        *{box-sizing:border-box;margin:0;padding:0}
        body{background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);min-height:100vh;display:flex;justify-content:center;align-items:center;font-family:'Sora',sans-serif;padding:20px}
        .card{background:#1e293b;width:100%;max-width:380px;padding:44px 36px;border-radius:28px;box-shadow:0 24px 60px rgba(0,0,0,.5);border:1px solid #334155;text-align:center}
        .lock{font-size:48px;margin-bottom:16px}
        h2{color:#f8fafc;font-size:24px;font-weight:700;margin-bottom:8px}
        p{color:#94a3b8;font-size:14px;margin-bottom:28px;line-height:1.6}
        input[type=password]{width:100%;background:#0f172a;border:1.5px solid #475569;border-radius:14px;padding:16px;font-size:22px;color:#f8fafc;outline:none;text-align:center;letter-spacing:8px;transition:.2s;margin-bottom:16px;font-family:'Sora',sans-serif}
        input[type=password]:focus{border-color:#818cf8;box-shadow:0 0 0 3px rgba(129,140,248,.2)}
        .btn{width:100%;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;border:none;border-radius:14px;padding:16px;font-size:16px;font-weight:700;cursor:pointer;transition:.2s;font-family:'Sora',sans-serif;letter-spacing:.5px}
        .btn:hover{opacity:.9;transform:translateY(-1px)}
        .alert{background:rgba(239,68,68,.15);color:#f87171;padding:14px;border-radius:12px;font-size:14px;font-weight:600;margin-bottom:16px;border:1px solid rgba(239,68,68,.2)}
    </style>
</head>
<body>
    <div class="card">
        <div class="lock">🔐</div>
        <h2>Workspace Locked</h2>
        <p>Enter your master PIN to access your personal workspace.</p>
        {% if error %}<div class="alert">{{ error }}</div>{% endif %}
        <form action="/login" method="POST">
            <input type="password" name="pin" placeholder="••••" autocomplete="off" autofocus required>
            <button type="submit" class="btn">Unlock Dashboard</button>
        </form>
    </div>
</body>
</html>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Smart Workspace</title>
    <link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #f0f2f8;
            --surface: #ffffff;
            --surface2: #f8fafc;
            --border: #e2e8f0;
            --text: #0f172a;
            --text2: #64748b;
            --accent: #6366f1;
            --accent2: #8b5cf6;
            --shadow: rgba(99,102,241,.08);
            --danger: #ef4444;
            --radius: 20px;
        }
        body.dark {
            --bg: #0a0f1e;
            --surface: #111827;
            --surface2: #1e293b;
            --border: #1f2d45;
            --text: #f1f5f9;
            --text2: #94a3b8;
            --shadow: rgba(0,0,0,.4);
        }
        *{box-sizing:border-box;margin:0;padding:0;font-family:'Sora',sans-serif}
        body{background:var(--bg);min-height:100vh;padding:32px 16px;transition:background .3s}

        /* ── LAYOUT ── */
        .wrap{max-width:680px;margin:0 auto}

        /* ── TOPBAR ── */
        .topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:32px}
        .logo{display:flex;align-items:center;gap:10px}
        .logo-icon{width:40px;height:40px;background:linear-gradient(135deg,#6366f1,#8b5cf6);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:20px}
        .logo-text{font-size:20px;font-weight:700;color:var(--text)}
        .topbar-actions{display:flex;gap:8px}
        .icon-btn{background:var(--surface);border:1px solid var(--border);color:var(--text2);padding:8px 14px;border-radius:12px;cursor:pointer;font-size:13px;font-weight:600;text-decoration:none;transition:.2s;display:flex;align-items:center;gap:6px}
        .icon-btn:hover{background:var(--surface2);color:var(--text)}
        .icon-btn.danger{color:var(--danger)}
        .icon-btn.danger:hover{background:rgba(239,68,68,.1)}

        /* ── ALERTS ── */
        .alert{padding:14px 18px;border-radius:14px;font-size:14px;font-weight:600;margin-bottom:20px;text-align:center}
        .alert-error{background:rgba(239,68,68,.12);color:#ef4444;border:1px solid rgba(239,68,68,.2)}
        .alert-success{background:rgba(34,197,94,.12);color:#22c55e;border:1px solid rgba(34,197,94,.2)}

        /* ── CARDS ── */
        .card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);margin-bottom:18px;overflow:hidden;box-shadow:0 4px 20px var(--shadow);transition:transform .2s,box-shadow .2s}
        .card:hover{transform:translateY(-2px);box-shadow:0 8px 30px var(--shadow)}
        .card-stripe{height:4px;width:100%}
        .card-body{padding:22px}

        .color-default .card-stripe{background:linear-gradient(90deg,#6366f1,#8b5cf6)}
        .color-rose    .card-stripe{background:linear-gradient(90deg,#f43f5e,#ec4899)}
        .color-amber   .card-stripe{background:linear-gradient(90deg,#f59e0b,#ef4444)}
        .color-emerald .card-stripe{background:linear-gradient(90deg,#10b981,#06b6d4)}
        .color-sky     .card-stripe{background:linear-gradient(90deg,#0ea5e9,#6366f1)}
        .color-indigo  .card-stripe{background:linear-gradient(90deg,#6366f1,#a855f7)}

        .card-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px}
        .card-title{font-size:17px;font-weight:700;color:var(--text);flex:1}
        .card-actions{display:flex;gap:4px;margin-left:12px}
        .act-btn{background:var(--surface2);border:1px solid var(--border);color:var(--text2);width:34px;height:34px;border-radius:10px;cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;transition:.2s}
        .act-btn:hover{background:var(--accent);color:#fff;border-color:var(--accent)}
        .act-btn.del:hover{background:var(--danger);border-color:var(--danger)}

        .card-content{font-size:14px;color:var(--text);line-height:1.75;white-space:pre-wrap;margin-bottom:14px}
        .card-link{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--accent);font-weight:600;text-decoration:none;background:rgba(99,102,241,.1);padding:6px 12px;border-radius:8px;word-break:break-all}
        .card-link:hover{background:rgba(99,102,241,.2)}

        /* ── FILE ATTACHMENTS ── */
        .files-section{margin-top:16px;border-top:1px solid var(--border);padding-top:14px}
        .files-label{font-size:12px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px}
        .files-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:10px}
        
        .file-thumb{position:relative;border-radius:12px;overflow:hidden;border:1px solid var(--border);background:var(--surface2);aspect-ratio:1;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:.2s}
        .file-thumb:hover{border-color:var(--accent)}
        .file-thumb img{width:100%;height:100%;object-fit:cover}
        .file-thumb .file-icon{font-size:32px;line-height:1}
        .file-name{font-size:11px;color:var(--text2);text-align:center;padding:4px 6px;background:var(--surface);position:absolute;bottom:0;left:0;right:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .file-del{position:absolute;top:4px;right:4px;background:rgba(0,0,0,.6);color:#fff;border:none;border-radius:6px;width:22px;height:22px;font-size:12px;cursor:pointer;display:none;align-items:center;justify-content:center}
        .file-thumb:hover .file-del{display:flex}

        /* ── EDIT FORM ── */
        .edit-form{padding:18px;border-top:1px solid var(--border)}
        .form-row{margin-bottom:12px}
        .form-label{font-size:12px;font-weight:600;color:var(--text2);margin-bottom:6px;display:block;text-transform:uppercase;letter-spacing:.06em}
        input[type=text],textarea,select{width:100%;background:var(--surface2);border:1.5px solid var(--border);border-radius:10px;padding:11px 14px;font-size:14px;color:var(--text);outline:none;font-family:'Sora',sans-serif;transition:.2s}
        input[type=text]:focus,textarea:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(99,102,241,.15)}
        textarea{min-height:90px;resize:vertical;line-height:1.6}
        select{cursor:pointer;appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%2394a3b8' fill='none' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 14px center}

        /* ── FILE DROP ZONE ── */
        .drop-zone{border:2px dashed var(--border);border-radius:12px;padding:20px;text-align:center;cursor:pointer;transition:.2s;color:var(--text2);font-size:13px;font-weight:500}
        .drop-zone:hover,.drop-zone.dragover{border-color:var(--accent);background:rgba(99,102,241,.05);color:var(--accent)}
        .drop-zone input{display:none}
        .drop-zone .dz-icon{font-size:28px;margin-bottom:6px}
        .dz-files-preview{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
        .dz-chip{background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:4px 10px;font-size:12px;color:var(--text);display:flex;align-items:center;gap:6px}
        .dz-chip button{background:none;border:none;cursor:pointer;color:var(--text2);font-size:14px;padding:0;line-height:1}

        /* ── BUTTONS ── */
        .btn-row{display:flex;gap:10px;margin-top:14px}
        .btn{padding:11px 20px;border-radius:12px;font-size:14px;font-weight:700;cursor:pointer;border:none;font-family:'Sora',sans-serif;transition:.2s;flex:1}
        .btn-primary{background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff}
        .btn-primary:hover{opacity:.9;transform:translateY(-1px)}
        .btn-ghost{background:transparent;color:var(--text2);border:1.5px solid var(--border)}
        .btn-ghost:hover{background:var(--surface2);color:var(--text)}

        /* ── ADD CARD ── */
        .add-btn{width:100%;background:var(--surface);border:2px dashed var(--border);color:var(--text2);padding:18px;border-radius:var(--radius);font-size:15px;font-weight:600;cursor:pointer;display:flex;justify-content:center;align-items:center;gap:10px;transition:.2s;margin-bottom:18px}
        .add-btn:hover{border-color:var(--accent);color:var(--accent);background:rgba(99,102,241,.04)}
        .add-card{background:var(--surface);border:1.5px solid var(--accent);border-radius:var(--radius);padding:24px;margin-bottom:18px;box-shadow:0 8px 30px rgba(99,102,241,.12)}

        /* ── COLOR PICKER ── */
        .color-picker{display:flex;gap:8px;flex-wrap:wrap}
        .cp-dot{width:28px;height:28px;border-radius:50%;cursor:pointer;border:2px solid transparent;transition:.2s;flex-shrink:0}
        .cp-dot:hover,.cp-dot.active{border-color:var(--text);transform:scale(1.15)}
        .cp-default{background:linear-gradient(135deg,#6366f1,#8b5cf6)}
        .cp-rose{background:linear-gradient(135deg,#f43f5e,#ec4899)}
        .cp-amber{background:linear-gradient(135deg,#f59e0b,#ef4444)}
        .cp-emerald{background:linear-gradient(135deg,#10b981,#06b6d4)}
        .cp-sky{background:linear-gradient(135deg,#0ea5e9,#6366f1)}
        .cp-indigo{background:linear-gradient(135deg,#6366f1,#a855f7)}

        /* ── MODAL (lightbox) ── */
        .modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.8);z-index:1000;align-items:center;justify-content:center;padding:20px}
        .modal-overlay.open{display:flex}
        .modal-img{max-width:90vw;max-height:85vh;border-radius:14px;box-shadow:0 20px 60px rgba(0,0,0,.5)}
        .modal-close{position:fixed;top:20px;right:20px;background:rgba(255,255,255,.15);border:none;color:#fff;width:40px;height:40px;border-radius:50%;font-size:20px;cursor:pointer;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)}
    </style>
</head>
<body>

<div class="wrap">
    <!-- TOPBAR -->
    <div class="topbar">
        <div class="logo">
            <div class="logo-icon">🌐</div>
            <div class="logo-text">My Workspace</div>
        </div>
        <div class="topbar-actions">
            <button class="icon-btn" id="themeToggle" type="button">🌙 Dark</button>
            <a href="/logout" class="icon-btn danger">🔒 Lock</a>
        </div>
    </div>

    {% if error %}<div class="alert alert-error">{{ error }}</div>{% endif %}
    {% if success %}<div class="alert alert-success">{{ success }}</div>{% endif %}

    <!-- NOTES -->
    {% for note in notes %}
    <div class="card color-{{ note.color or 'default' }}" id="card-{{ note.id }}">
        <div class="card-stripe"></div>
        <div class="card-body">
            <!-- VIEW -->
            <div id="view-{{ note.id }}">
                <div class="card-header">
                    <div class="card-title">{{ note.title }}</div>
                    <div class="card-actions">
                        <button class="act-btn" onclick="toggleEdit('{{ note.id }}')" title="Edit">✏️</button>
                        <form action="/action" method="POST" style="display:inline;">
                            <input type="hidden" name="action_type" value="delete">
                            <input type="hidden" name="note_id" value="{{ note.id }}">
                            <button type="submit" class="act-btn del" title="Delete" onclick="return confirm('Delete this card?')">🗑️</button>
                        </form>
                    </div>
                </div>
                {% if note.content %}<div class="card-content">{{ note.content }}</div>{% endif %}
                {% if note.link %}<a href="{{ note.link }}" target="_blank" class="card-link">🔗 {{ note.link }}</a>{% endif %}

                <!-- FILE ATTACHMENTS -->
                {% if note.files %}
                <div class="files-section">
                    <div class="files-label">📎 Attachments ({{ note.files|length }})</div>
                    <div class="files-grid">
                        {% for f in note.files %}
                        <div class="file-thumb" {% if f.mimetype and f.mimetype.startswith('image') %}onclick="openLightbox('/uploads/{{ f.filename }}')"{% else %}onclick="window.open('/uploads/{{ f.filename }}','_blank')"{% endif %}>
                            {% if f.mimetype and f.mimetype.startswith('image') %}
                                <img src="/uploads/{{ f.filename }}" alt="{{ f.original }}">
                            {% else %}
                                <div class="file-icon">{{ '📄' if 'pdf' in (f.mimetype or '') else '🎵' if 'audio' in (f.mimetype or '') else '🎬' if 'video' in (f.mimetype or '') else '📦' if 'zip' in (f.original or '') else '📊' if ('xls' in (f.original or '') or 'csv' in (f.original or '')) else '📝' }}</div>
                            {% endif %}
                            <div class="file-name">{{ f.original }}</div>
                            <form action="/action" method="POST" style="position:absolute;top:4px;right:4px;">
                                <input type="hidden" name="action_type" value="delete_file">
                                <input type="hidden" name="file_id" value="{{ f.id }}">
                                <input type="hidden" name="note_id" value="{{ note.id }}">
                                <button type="submit" class="file-del" onclick="return confirm('Remove file?')" title="Remove">✕</button>
                            </form>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                {% endif %}

                <!-- QUICK ADD FILE to existing card -->
                <form action="/action" method="POST" enctype="multipart/form-data" style="margin-top:14px;">
                    <input type="hidden" name="action_type" value="add_files">
                    <input type="hidden" name="note_id" value="{{ note.id }}">
                    <label class="drop-zone" id="dz-{{ note.id }}">
                        <div class="dz-icon">📎</div>
                        <div>Click or drop files to attach</div>
                        <input type="file" name="files" multiple accept="image/*,.pdf,.txt,.doc,.docx,.xls,.xlsx,.csv,.zip,.mp3,.mp4,.mov" onchange="previewFiles(this,'{{ note.id }}')">
                    </label>
                    <div class="dz-files-preview" id="prev-{{ note.id }}"></div>
                    <div id="upload-btn-{{ note.id }}" style="display:none;margin-top:8px;">
                        <button type="submit" class="btn btn-primary" style="width:100%;">⬆️ Upload Files</button>
                    </div>
                </form>
            </div>

            <!-- EDIT FORM -->
            <div id="edit-{{ note.id }}" style="display:none;">
                <form action="/action" method="POST">
                    <input type="hidden" name="action_type" value="edit">
                    <input type="hidden" name="note_id" value="{{ note.id }}">
                    <div class="form-row">
                        <label class="form-label">Title</label>
                        <input type="text" name="title" value="{{ note.title }}" required>
                    </div>
                    <div class="form-row">
                        <label class="form-label">Notes / Content</label>
                        <textarea name="content">{{ note.content }}</textarea>
                    </div>
                    <div class="form-row">
                        <label class="form-label">Link (optional)</label>
                        <input type="text" name="link" value="{{ note.link }}" placeholder="https://...">
                    </div>
                    <div class="form-row">
                        <label class="form-label">Card Colour</label>
                        <div class="color-picker" id="cp-edit-{{ note.id }}">
                            {% for c in ['default','rose','amber','emerald','sky','indigo'] %}
                            <div class="cp-dot cp-{{ c }} {% if (note.color or 'default') == c %}active{% endif %}" onclick="pickColor('cp-edit-{{ note.id }}','{{ c }}',this)"></div>
                            {% endfor %}
                        </div>
                        <input type="hidden" name="color" id="color-edit-{{ note.id }}" value="{{ note.color or 'default' }}">
                    </div>
                    <div class="btn-row">
                        <button type="submit" class="btn btn-primary">💾 Save</button>
                        <button type="button" class="btn btn-ghost" onclick="toggleEdit('{{ note.id }}')">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    {% endfor %}

    <!-- ADD NEW CARD -->
    <button class="add-btn" id="addBtn" onclick="showAddForm()">➕ Add New Card</button>

    <div id="addCard" class="add-card" style="display:none;">
        <div style="font-size:17px;font-weight:700;color:var(--text);margin-bottom:18px;">✨ New Card</div>
        <form action="/action" method="POST" enctype="multipart/form-data">
            <input type="hidden" name="action_type" value="add">
            <div class="form-row">
                <label class="form-label">Title *</label>
                <input type="text" name="title" placeholder="Card title..." required>
            </div>
            <div class="form-row">
                <label class="form-label">Notes / Content</label>
                <textarea name="content" placeholder="Write anything here..."></textarea>
            </div>
            <div class="form-row">
                <label class="form-label">Link (optional)</label>
                <input type="text" name="link" placeholder="https://...">
            </div>
            <div class="form-row">
                <label class="form-label">Attach Files / Photos</label>
                <label class="drop-zone" id="dz-new">
                    <div class="dz-icon">🖼️</div>
                    <div>Click to browse or drag & drop files</div>
                    <small style="margin-top:4px;display:block;opacity:.6">Images, PDF, Word, Excel, ZIP, Video — max 50 MB</small>
                    <input type="file" name="files" multiple accept="image/*,.pdf,.txt,.doc,.docx,.xls,.xlsx,.csv,.zip,.mp3,.mp4,.mov" onchange="previewFiles(this,'new')">
                </label>
                <div class="dz-files-preview" id="prev-new"></div>
            </div>
            <div class="form-row">
                <label class="form-label">Card Colour</label>
                <div class="color-picker" id="cp-add">
                    {% for c in ['default','rose','amber','emerald','sky','indigo'] %}
                    <div class="cp-dot cp-{{ c }} {% if c == 'default' %}active{% endif %}" onclick="pickColor('cp-add','{{ c }}',this)"></div>
                    {% endfor %}
                </div>
                <input type="hidden" name="color" id="color-add" value="default">
            </div>
            <div class="btn-row">
                <button type="submit" class="btn btn-primary">➕ Add Card</button>
                <button type="button" class="btn btn-ghost" onclick="hideAddForm()">Cancel</button>
            </div>
        </form>
    </div>
</div>

<!-- LIGHTBOX -->
<div class="modal-overlay" id="lightbox" onclick="closeLightbox()">
    <button class="modal-close" onclick="closeLightbox()">✕</button>
    <img class="modal-img" id="lightbox-img" src="" alt="">
</div>

<script>
// ── THEME ──────────────────────────────────────────────────────────────────
const themeBtn = document.getElementById('themeToggle');
function applyTheme(t) {
    document.body.classList.toggle('dark', t === 'dark');
    themeBtn.innerHTML = t === 'dark' ? '☀️ Light' : '🌙 Dark';
}
applyTheme(localStorage.getItem('theme') || 'light');
themeBtn.addEventListener('click', () => {
    const t = document.body.classList.contains('dark') ? 'light' : 'dark';
    localStorage.setItem('theme', t); applyTheme(t);
});

// ── EDIT TOGGLE ────────────────────────────────────────────────────────────
function toggleEdit(id) {
    const v = document.getElementById('view-'+id), e = document.getElementById('edit-'+id);
    v.style.display = v.style.display === 'none' ? 'block' : 'none';
    e.style.display = e.style.display === 'none' ? 'block' : 'none';
}

// ── ADD FORM ───────────────────────────────────────────────────────────────
function showAddForm() {
    document.getElementById('addCard').style.display = 'block';
    document.getElementById('addBtn').style.display = 'none';
    document.getElementById('addCard').scrollIntoView({behavior:'smooth'});
}
function hideAddForm() {
    document.getElementById('addCard').style.display = 'none';
    document.getElementById('addBtn').style.display = 'flex';
}

// ── FILE PREVIEW ───────────────────────────────────────────────────────────
function previewFiles(input, id) {
    const prev = document.getElementById('prev-'+id);
    prev.innerHTML = '';
    const uploadBtn = document.getElementById('upload-btn-'+id);
    if (uploadBtn && input.files.length) uploadBtn.style.display = 'block';
    Array.from(input.files).forEach(f => {
        const chip = document.createElement('div');
        chip.className = 'dz-chip';
        const icon = f.type.startsWith('image') ? '🖼️' : f.name.endsWith('.pdf') ? '📄' : '📎';
        chip.innerHTML = `${icon} <span>${f.name}</span>`;
        prev.appendChild(chip);
    });
    // Highlight drop zone
    const dz = document.getElementById('dz-'+id);
    if (dz && input.files.length) dz.style.borderColor = 'var(--accent)';
}

// ── DRAG & DROP ────────────────────────────────────────────────────────────
document.querySelectorAll('.drop-zone').forEach(zone => {
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', e => {
        e.preventDefault(); zone.classList.remove('dragover');
        const input = zone.querySelector('input[type=file]');
        if (input) { input.files = e.dataTransfer.files; input.dispatchEvent(new Event('change')); }
    });
});

// ── COLOR PICKER ──────────────────────────────────────────────────────────
function pickColor(containerId, colorName, dot) {
    document.querySelectorAll('#'+containerId+' .cp-dot').forEach(d => d.classList.remove('active'));
    dot.classList.add('active');
    // update hidden input (replace cp-add/cp-edit-ID prefix)
    const inputId = containerId.replace('cp-', 'color-');
    const inp = document.getElementById(inputId);
    if (inp) inp.value = colorName;
}

// ── LIGHTBOX ───────────────────────────────────────────────────────────────
function openLightbox(src) {
    document.getElementById('lightbox-img').src = src;
    document.getElementById('lightbox').classList.add('open');
    document.body.style.overflow = 'hidden';
}
function closeLightbox() {
    document.getElementById('lightbox').classList.remove('open');
    document.body.style.overflow = '';
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeLightbox(); });
</script>
</body>
</html>
"""

# ─── ROUTES ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if not session.get('authenticated'):
        return render_template_string(LOGIN_TEMPLATE, error="")
    notes = WorkspaceNote.query.all()
    return render_template_string(HTML_TEMPLATE, notes=notes, error="", success="")

@app.route('/login', methods=['POST'])
def login():
    if request.form.get('pin') == MASTER_PIN:
        session['authenticated'] = True
        return redirect(url_for('index'))
    return render_template_string(LOGIN_TEMPLATE, error="❌ Invalid PIN. Try again.")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if not session.get('authenticated'):
        abort(403)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def save_files(files, note_id):
    """Save uploaded files and create NoteFile records."""
    for f in files:
        if f and f.filename and allowed_file(f.filename):
            ext = f.filename.rsplit('.', 1)[1].lower()
            stored_name = f"{uuid.uuid4()}.{ext}"
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], stored_name))
            nf = NoteFile(
                id=str(uuid.uuid4()),
                note_id=note_id,
                filename=stored_name,
                original=secure_filename(f.filename),
                mimetype=f.mimetype or ''
            )
            db.session.add(nf)

@app.route('/action', methods=['POST'])
def handle_action():
    if not session.get('authenticated'):
        return redirect(url_for('index'))

    action = request.form.get('action_type')

    if action == 'add':
        note_id = str(uuid.uuid4())
        note = WorkspaceNote(
            id=note_id,
            title=request.form.get('title', 'Untitled'),
            content=request.form.get('content', ''),
            link=request.form.get('link', ''),
            color=request.form.get('color', 'default')
        )
        db.session.add(note)
        db.session.flush()   # get the id before saving files
        save_files(request.files.getlist('files'), note_id)
        db.session.commit()

    elif action == 'edit':
        note_id = request.form.get('note_id')
        note = WorkspaceNote.query.get(note_id)
        if note:
            note.title   = request.form.get('title', note.title)
            note.content = request.form.get('content', note.content)
            note.link    = request.form.get('link', note.link)
            note.color   = request.form.get('color', note.color)
            db.session.commit()

    elif action == 'delete':
        note_id = request.form.get('note_id')
        note = WorkspaceNote.query.get(note_id)
        if note:
            # delete physical files
            for f in note.files:
                fpath = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
                if os.path.exists(fpath):
                    os.remove(fpath)
            db.session.delete(note)
            db.session.commit()

    elif action == 'add_files':
        note_id = request.form.get('note_id')
        note = WorkspaceNote.query.get(note_id)
        if note:
            save_files(request.files.getlist('files'), note_id)
            db.session.commit()

    elif action == 'delete_file':
        file_id = request.form.get('file_id')
        nf = NoteFile.query.get(file_id)
        if nf:
            fpath = os.path.join(app.config['UPLOAD_FOLDER'], nf.filename)
            if os.path.exists(fpath):
                os.remove(fpath)
            db.session.delete(nf)
            db.session.commit()

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
