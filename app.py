# app.py
# Flask-based Job Application Tracker with Search, Tracker, and Details pages

import os
import time
from flask import Flask, render_template_string, request, redirect, url_for, send_from_directory
import sqlite3
from datetime import datetime
from jinja2 import Template
import requests
from bs4 import BeautifulSoup
from werkzeug.utils import secure_filename

# CONFIGURATION
DB_PATH = 'jobs.db'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
PER_PAGE = 5
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# APP INIT
print(f"=== Loading UPDATED app.py at {time.asctime()} ===")
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# DB UTILITIES
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    c = get_conn().cursor()
    c.execute("""
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    title TEXT, company TEXT, location TEXT, url TEXT UNIQUE,
    date_posted TEXT, platform TEXT, requirements TEXT,
    fetched_at TIMESTAMP
)
""")
    c.execute("""
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY, job_id INTEGER,
    status TEXT, applied_at DATE,
    FOREIGN KEY(job_id) REFERENCES jobs(id)
)
""")
    c.execute("""
CREATE TABLE IF NOT EXISTS resume (
    id INTEGER PRIMARY KEY, filename TEXT, uploaded_at TIMESTAMP
)
""")
    get_conn().commit()

init_db()

# ALLOWED FILE
def allowed_file(fn):
    return '.' in fn and fn.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

# STUB FUNCTIONS
def fetch_linkedin_jobs(keyword, location):
    # Dummy data stub: return sample jobs based on keyword and location
    if not keyword:
        return []
    jobs = []
    for i in range(1, 6):
        jobs.append({
            'title': f"{keyword} Position {i}",
            'company': f"Company {i}",
            'location': location or f"Location {i}",
            'url': f"https://example.com/job/{i}"
        })
    return jobs
def fetch_job_details(url):
    return {'requirements': ['Req1','Req2'], 'date_posted': datetime.now().strftime('%Y-%m-%d'), 'platform': 'LinkedIn'}

# SAVE LISTINGS
def save_listings(listings):
    conn = get_conn(); c = conn.cursor()
    for job in listings:
        c.execute(
            "INSERT OR IGNORE INTO jobs (title,company,location,url,date_posted,platform,requirements,fetched_at) VALUES (?,?,?,?,?,?,?,?)",
            (job['title'],job['company'],job['location'],job['url'],job['date_posted'],job['platform'],','.join(job['requirements']),datetime.now())
        )
    conn.commit(); conn.close()

# APPLY EXTERNAL
@app.route('/apply_external/<int:job_id>')
def apply_external(job_id):
    conn = get_conn();
    row = conn.execute('SELECT url FROM jobs WHERE id=?',(job_id,)).fetchone();
    conn.execute('INSERT INTO applications (job_id,status,applied_at) VALUES (?,?,?)',(job_id,'Applied',datetime.now().strftime('%Y-%m-%d')))
    conn.commit(); conn.close()
    return redirect(row['url'])

# NAVBAR & FOOTER
NAVBAR = """
<nav class="navbar navbar-expand-lg navbar-light bg-light mb-4">
  <div class="container-fluid">
    <a class="navbar-brand" href="/search">JobApp</a>
    <div class="collapse navbar-collapse">
      <ul class="navbar-nav me-auto">
        <li class="nav-item"><a class="nav-link" href="/search">Search</a></li>
        <li class="nav-item"><a class="nav-link" href="/tracker">Tracker</a></li>
        <li class="nav-item"><a class="nav-link" href="/details">Details</a></li>
      </ul>
    </div>
  </div>
</nav>
"""
FOOTER = """
<script src='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js'></script>
</body></html>
"""

# TEMPLATES
SEARCH_HTML = NAVBAR + '''
<div class="container">
  <h2>Job Search</h2>
  <form method="post" class="row g-3 mb-3">
    <div class="col-md-5"><input name="keyword" placeholder="Role" value="{{keyword}}" class="form-control"/></div>
    <div class="col-md-5"><input name="location" placeholder="Location" value="{{location}}" class="form-control"/></div>
    <div class="col-md-2"><button class="btn btn-primary w-100">Search</button></div>
  </form>
  <form method="get" class="row g-3 mb-3">
    <div class="col-md-4"><input name="filter_loc" placeholder="Filter location" value="{{filter_loc}}" class="form-control"/></div>
    <div class="col-md-4">
      <select name="page" class="form-select">
      {% for p in range(1,pages+1) %}
        <option value="{{p}}" {% if p==page %}selected{% endif %}>Page {{p}}</option>
      {% endfor %}
      </select>
    </div>
    <div class="col-md-4"><button class="btn btn-secondary w-100">Apply Filters</button></div>
  </form>
  {% for job in rows %}
    <div class="card mb-3">
      <div class="card-body">
        <h5>{{job['title']}} <small class="text-muted">({{job['platform']}})</small></h5>
        <h6 class="card-subtitle mb-2 text-muted">{{job['company']}} - {{job['location']}}</h6>
        <p><small>Posted: {{job['date_posted']}}</small></p>
        <p>{{job['requirements']}}</p>
        <a href="/apply_external/{{job['id']}}" class="btn btn-success">Apply</a>
      </div>
    </div>
  {% endfor %}
</div>
''' + FOOTER

TRACKER_HTML = NAVBAR + '''
<div class="container">
  <h2>Application Tracker</h2>
  <table class="table">
    <thead><tr><th>ID</th><th>Title</th><th>Status</th><th>Date Applied</th><th>Actions</th></tr></thead>
    <tbody>
    {% for app in apps %}
      <tr>
        <td>{{app['job_id']}}</td>
        <td>{{app['title']}}</td>
        <td>{{app['status']}}</td>
        <td>{{app['applied_at']}}</td>
        <td>
          <form method="post" action="/update_status/{{app['id']}}" class="d-flex gap-2">
            <select name="status" class="form-select form-select-sm">
              {% for s in ['Applied','Rejected','No response'] %}
                <option value="{{s}}" {% if s==app['status'] %}selected{% endif %}>{{s}}</option>
              {% endfor %}
            </select>
            <input type="date" name="applied_at" value="{{app['applied_at']}}" class="form-control form-control-sm"/>
            <button class="btn btn-sm btn-primary">Save</button>
          </form>
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</div>
''' + FOOTER

DETAILS_HTML = NAVBAR + '''
<div class="container">
  <h2>Resume Details</h2>
  {% if resume %}
    <p>Current: <a href="/uploads/{{resume['filename']}}">{{resume['filename']}}</a> ({{resume['uploaded_at']}})</p>
  {% endif %}
  <form method="post" enctype="multipart/form-data">
    <input type="file" name="file" class="form-control mb-3"/>
    <button class="btn btn-primary">Upload Resume</button>
  </form>
</div>
''' + FOOTER

# ROUTES
@app.route('/')
def home(): return redirect(url_for('search'))

@app.route('/search', methods=['GET','POST'])
def search():
    keyword = request.form.get('keyword','') if request.method=='POST' else ''
    location = request.form.get('location','') if request.method=='POST' else ''
    if request.method=='POST':
        lst = fetch_linkedin_jobs(keyword, location)
        save_listings(lst)
    conn = get_conn(); rows = conn.execute('SELECT * FROM jobs ORDER BY fetched_at DESC').fetchall(); conn.close()
    filter_loc = request.args.get('filter_loc','')
    page = request.args.get('page',1,type=int)
    if filter_loc: rows = [r for r in rows if filter_loc.lower() in r['location'].lower()]
    total=len(rows); pages=(total+PER_PAGE-1)//PER_PAGE
    page = max(1, min(page,pages))
    rows = rows[(page-1)*PER_PAGE : page*PER_PAGE]
    rows = [dict(r) for r in rows]
    return render_template_string(SEARCH_HTML,keyword=keyword,location=location,filter_loc=filter_loc,page=page,pages=pages,rows=rows)

@app.route('/tracker', methods=['GET','POST'])
def tracker():
    conn = get_conn(); apps = conn.execute('SELECT a.id,a.job_id,a.status,a.applied_at,j.title FROM applications a JOIN jobs j ON a.job_id=j.id').fetchall(); conn.close()
    apps = [dict(a) for a in apps]
    return render_template_string(TRACKER_HTML,apps=apps)

@app.route('/update_status/<int:id>', methods=['POST'])
def update_status(id):
    status = request.form['status']; date = request.form['applied_at']
    conn=get_conn(); conn.execute('UPDATE applications SET status=?,applied_at=? WHERE id=?',(status,date,id)); conn.commit(); conn.close()
    return redirect(url_for('tracker'))

@app.route('/details', methods=['GET','POST'])
def details():
    conn = get_conn(); res = conn.execute('SELECT * FROM resume ORDER BY uploaded_at DESC LIMIT 1').fetchone(); conn.close()
    resume = dict(res) if res else None
    if request.method=='POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            fn = secure_filename(file.filename); path=os.path.join(app.config['UPLOAD_FOLDER'],fn); file.save(path)
            conn=get_conn(); conn.execute('INSERT INTO resume (filename,uploaded_at) VALUES (?,?)',(fn,datetime.now().strftime('%Y-%m-%d %H:%M'))); conn.commit(); conn.close()
            return redirect(url_for('details'))
    return render_template_string(DETAILS_HTML,resume=resume)

@app.route('/uploads/<path:filename>')
def download(filename): return send_from_directory(app.config['UPLOAD_FOLDER'],filename)

@app.route('/_ping')
def ping(): return 'pong'

# RUNNING
# python3 -m flask --app app.py --debug run
