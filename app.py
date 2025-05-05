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
import json
from concurrent.futures import ThreadPoolExecutor
import random
import time
from functools import wraps
from urllib.parse import urljoin, quote_plus

# CONFIGURATION
DB_PATH = 'jobs.db'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
PER_PAGE = 5
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Scraping Configuration
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
]

# Add this near the top of the file, after the imports
COMMON_LOCATIONS = [
    # United States
    'United States', 'New York', 'San Francisco', 'Los Angeles', 'Chicago', 'Boston', 'Seattle', 'Austin', 'Remote',
    # India
    'India', 'Bangalore', 'Mumbai', 'Delhi', 'Hyderabad', 'Pune', 'Chennai', 'Gurgaon', 'Noida',
    # UAE
    'UAE', 'Dubai', 'Abu Dhabi', 'Sharjah', 'Ras Al Khaimah',
    # Europe
    'United Kingdom', 'London', 'Germany', 'Berlin', 'France', 'Paris', 'Netherlands', 'Amsterdam',
    # Asia
    'Singapore', 'Hong Kong', 'Tokyo', 'Seoul', 'Shanghai', 'Beijing',
    # Canada
    'Canada', 'Toronto', 'Vancouver', 'Montreal',
    # Australia
    'Australia', 'Sydney', 'Melbourne'
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def rate_limit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        time.sleep(random.uniform(2, 5))  # Random delay between 2-5 seconds
        return func(*args, **kwargs)
    return wrapper

def get_location_options():
    return sorted(COMMON_LOCATIONS)

@rate_limit
def fetch_linkedin_jobs(keyword, location):
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        # Handle country-level searches
        if location in ['India', 'UAE', 'United States', 'United Kingdom', 'Germany', 'France', 'Netherlands', 'Singapore', 'Canada', 'Australia']:
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(keyword)}&location={quote_plus(location)}"
        else:
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(keyword)}&location={quote_plus(location)}"
        
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        jobs = []
        
        for job_card in soup.select('.jobs-search__results-list li'):
            try:
                title_elem = job_card.select_one('.base-search-card__title')
                company_elem = job_card.select_one('.base-search-card__subtitle')
                location_elem = job_card.select_one('.job-search-card__location')
                link_elem = job_card.select_one('a.base-card__full-link')
                
                if not all([title_elem, company_elem, location_elem, link_elem]):
                    continue
                
                job_location = location_elem.text.strip()
                # Standardize location format
                if 'India' in job_location:
                    job_location = 'India'
                elif 'UAE' in job_location or 'Dubai' in job_location:
                    job_location = 'UAE'
                
                job = {
                    'title': title_elem.text.strip(),
                    'company': company_elem.text.strip(),
                    'company_info': '',
                    'location': job_location,
                    'url': link_elem['href'],
                    'date_posted': datetime.now().strftime('%Y-%m-%d'),
                    'platform': 'LinkedIn',
                    'description': '',
                    'requirements': [],
                    'match_score': 'N/A',
                    'salary_min': '',
                    'salary_max': '',
                    'salary_currency': '',
                    'benefits': []
                }
                
                # Fetch job details
                job_details = fetch_linkedin_job_details(job['url'])
                job.update(job_details)
                
                jobs.append(job)
            except Exception as e:
                print(f"Error parsing LinkedIn job card: {str(e)}")
                continue
                
        return jobs
    except Exception as e:
        print(f"Error fetching LinkedIn jobs: {str(e)}")
        return []

@rate_limit
def fetch_indeed_jobs(keyword, location):
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        search_url = f"https://www.indeed.com/jobs?q={quote_plus(keyword)}&l={quote_plus(location)}"
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        jobs = []
        
        for job_card in soup.select('.job_seen_beacon'):
            try:
                title_elem = job_card.select_one('.jobTitle')
                company_elem = job_card.select_one('.companyName')
                location_elem = job_card.select_one('.companyLocation')
                link_elem = job_card.select_one('a.jcs-JobTitle')
                
                if not all([title_elem, company_elem, location_elem, link_elem]):
                    continue
                
                job = {
                    'title': title_elem.text.strip(),
                    'company': company_elem.text.strip(),
                    'company_info': '',
                    'location': location_elem.text.strip(),
                    'url': urljoin('https://www.indeed.com', link_elem['href']),
                    'date_posted': datetime.now().strftime('%Y-%m-%d'),
                    'platform': 'Indeed',
                    'description': '',
                    'requirements': [],
                    'match_score': 'N/A',
                    'salary_min': '',
                    'salary_max': '',
                    'salary_currency': '',
                    'benefits': []
                }
                
                # Fetch job details
                job_details = fetch_indeed_job_details(job['url'])
                job.update(job_details)
                
                jobs.append(job)
            except Exception as e:
                print(f"Error parsing Indeed job card: {str(e)}")
                continue
                
        return jobs
    except Exception as e:
        print(f"Error fetching Indeed jobs: {str(e)}")
        return []

@rate_limit
def fetch_ziprecruiter_jobs(keyword, location):
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        search_url = f"https://www.ziprecruiter.com/jobs-search?search={quote_plus(keyword)}&location={quote_plus(location)}"
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        jobs = []
        
        for job_card in soup.select('.job_content'):
            try:
                title_elem = job_card.select_one('.job_title')
                company_elem = job_card.select_one('.company_name')
                location_elem = job_card.select_one('.location')
                link_elem = job_card.select_one('a.job_link')
                
                if not all([title_elem, company_elem, location_elem, link_elem]):
                    continue
                
                job = {
                    'title': title_elem.text.strip(),
                    'company': company_elem.text.strip(),
                    'company_info': '',
                    'location': location_elem.text.strip(),
                    'url': link_elem['href'],
                    'date_posted': datetime.now().strftime('%Y-%m-%d'),
                    'platform': 'ZipRecruiter',
                    'description': '',
                    'requirements': [],
                    'match_score': 'N/A',
                    'salary_min': '',
                    'salary_max': '',
                    'salary_currency': '',
                    'benefits': []
                }
                
                # Fetch job details
                job_details = fetch_ziprecruiter_job_details(job['url'])
                job.update(job_details)
                
                jobs.append(job)
            except Exception as e:
                print(f"Error parsing ZipRecruiter job card: {str(e)}")
                continue
                
        return jobs
    except Exception as e:
        print(f"Error fetching ZipRecruiter jobs: {str(e)}")
        return []

def fetch_linkedin_job_details(url):
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        description = soup.select_one('.description__text')
        requirements = soup.select('.description__job-criteria-item')
        
        # Extract requirements from job criteria
        req_list = []
        for req in requirements:
            req_text = req.text.strip()
            if req_text:
                req_list.append(req_text)
        
        return {
            'description': description.text.strip() if description else '',
            'requirements': req_list,
            'benefits': [],
            'salary_range': ''
        }
    except Exception as e:
        print(f"Error fetching LinkedIn job details: {str(e)}")
        return {
            'description': '',
            'requirements': [],
            'benefits': [],
            'salary_range': ''
        }

def fetch_indeed_job_details(url):
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        description = soup.select_one('#jobDescriptionText')
        requirements = soup.select('.jobsearch-ReqAndQualSection-item')
        
        # Extract requirements from job description
        req_list = []
        if description:
            # Look for bullet points or numbered lists
            bullets = description.select('ul li, ol li')
            for bullet in bullets:
                req_text = bullet.text.strip()
                if req_text:
                    req_list.append(req_text)
        
        return {
            'description': description.text.strip() if description else '',
            'requirements': req_list,
            'benefits': [],
            'salary_range': ''
        }
    except Exception as e:
        print(f"Error fetching Indeed job details: {str(e)}")
        return {
            'description': '',
            'requirements': [],
            'benefits': [],
            'salary_range': ''
        }

def fetch_ziprecruiter_job_details(url):
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        description = soup.select_one('.job_description')
        requirements = soup.select('.job_requirements li')
        
        # Extract requirements from job requirements section
        req_list = []
        for req in requirements:
            req_text = req.text.strip()
            if req_text:
                req_list.append(req_text)
        
        return {
            'description': description.text.strip() if description else '',
            'requirements': req_list,
            'benefits': [],
            'salary_range': ''
        }
    except Exception as e:
        print(f"Error fetching ZipRecruiter job details: {str(e)}")
        return {
            'description': '',
            'requirements': [],
            'benefits': [],
            'salary_range': ''
        }

def fetch_all_jobs(keyword, location):
    jobs = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(fetch_linkedin_jobs, keyword, location),
            executor.submit(fetch_indeed_jobs, keyword, location),
            executor.submit(fetch_ziprecruiter_jobs, keyword, location)
        ]
        
        for future in futures:
            try:
                jobs.extend(future.result())
            except Exception as e:
                print(f"Error in job fetch: {str(e)}")
    
    # Remove duplicates based on URL
    seen_urls = set()
    unique_jobs = []
    for job in jobs:
        if job['url'] not in seen_urls:
            seen_urls.add(job['url'])
            unique_jobs.append(job)
    
    return unique_jobs

def fetch_job_details(url):
    try:
        # Determine which platform the URL belongs to
        if 'linkedin.com' in url:
            return fetch_linkedin_job_details(url)
        elif 'indeed.com' in url:
            return fetch_indeed_job_details(url)
        elif 'ziprecruiter.com' in url:
            return fetch_ziprecruiter_job_details(url)
        else:
            return {
                'description': '',
                'requirements': [],
                'benefits': [],
                'salary_range': ''
            }
    except Exception as e:
        print(f"Error fetching job details: {str(e)}")
        return {
            'description': '',
            'requirements': [],
            'benefits': [],
            'salary_range': ''
        }

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
    title TEXT, company TEXT, company_info TEXT, location TEXT, url TEXT UNIQUE,
    date_posted TEXT, platform TEXT, requirements TEXT, description TEXT,
    match_score TEXT, fetched_at TIMESTAMP
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

# SAVE LISTINGS
def save_listings(listings):
    conn = get_conn(); c = conn.cursor()
    for job in listings:
        # Ensure requirements is a list
        if isinstance(job['requirements'], str):
            requirements = job['requirements'].split(',')
        elif isinstance(job['requirements'], list):
            requirements = job['requirements']
        else:
            requirements = []
            
        c.execute(
            """INSERT OR IGNORE INTO jobs 
            (title, company, company_info, location, url, date_posted, platform, 
            requirements, description, match_score, fetched_at) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (job['title'], job['company'], job.get('company_info', ''),
             job['location'], job['url'], job['date_posted'], job['platform'],
             json.dumps(requirements), job.get('description', ''),
             job.get('match_score', 'N/A'), datetime.now())
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
  <h2 class="mb-4">Job Search</h2>
  <form method="post" class="row g-3 mb-4">
    <div class="col-md-4">
      <input name="keyword" placeholder="Role (e.g., Software Engineer, Product Manager)" value="{{keyword}}" class="form-control"/>
    </div>
    <div class="col-md-3">
      <select name="location" class="form-select">
        <option value="">All Locations</option>
        {% for loc in locations %}
          <option value="{{loc}}" {% if loc==location %}selected{% endif %}>{{loc}}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-md-3">
      <select name="platform" class="form-select">
        <option value="">All Platforms</option>
        {% for plat in platforms %}
          <option value="{{plat}}" {% if plat==platform %}selected{% endif %}>{{plat}}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-md-2">
      <button class="btn btn-primary w-100">Search</button>
    </div>
  </form>

  <form method="get" class="row g-3 mb-4">
    <div class="col-md-3">
      <select name="filter_loc" class="form-select">
        <option value="">Filter by Location</option>
        {% for loc in locations %}
          <option value="{{loc}}" {% if loc==filter_loc %}selected{% endif %}>{{loc}}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-md-3">
      <select name="filter_platform" class="form-select">
        <option value="">Filter by Platform</option>
        {% for plat in platforms %}
          <option value="{{plat}}" {% if plat==filter_platform %}selected{% endif %}>{{plat}}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-md-3">
      <select name="page" class="form-select">
        {% for p in range(1,pages+1) %}
          <option value="{{p}}" {% if p==page %}selected{% endif %}>Page {{p}}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-md-3">
      <button class="btn btn-secondary w-100">Apply Filters</button>
    </div>
  </form>

  <div class="row row-cols-1 row-cols-md-2 g-4">
    {% for job in rows %}
      <div class="col">
        <div class="card h-100">
          <div class="card-header bg-light">
            <div class="d-flex justify-content-between align-items-center">
              <h5 class="card-title mb-0">{{job['title']}}</h5>
              <span class="badge bg-info">{{job['platform']}}</span>
            </div>
          </div>
          <div class="card-body">
            <div class="mb-3">
              <h6 class="card-subtitle text-muted">{{job['company']}}</h6>
              <p class="text-muted mb-1">
                <i class="bi bi-geo-alt"></i> {{job['location']}}
              </p>
              <p class="text-muted small">
                <i class="bi bi-calendar"></i> Posted: {{job['date_posted']}}
              </p>
            </div>

            <div class="mb-3">
              <h6 class="card-subtitle">Description</h6>
              <div class="job-description">
                {% if job['description'] %}
                  <div class="description-content">
                    {{job['description'] | replace('\n', '<br>') | safe}}
                  </div>
                {% else %}
                  <p class="text-muted">No description available</p>
                {% endif %}
              </div>
            </div>

            {% if job['requirements'] %}
              <div class="mb-3">
                <h6 class="card-subtitle">Requirements</h6>
                <div class="d-flex flex-wrap gap-2">
                  {% for req in job['requirements'] %}
                    <span class="badge bg-primary">{{req}}</span>
                  {% endfor %}
                </div>
              </div>
            {% endif %}

            {% if job.get('salary_min') or job.get('salary_max') %}
              <div class="mb-3">
                <h6 class="card-subtitle">Salary Range</h6>
                <p class="mb-0">
                  {% if job['salary_min'] and job['salary_max'] %}
                    {{job['salary_min']}} - {{job['salary_max']}} {{job['salary_currency']}}
                  {% elif job['salary_min'] %}
                    From {{job['salary_min']}} {{job['salary_currency']}}
                  {% elif job['salary_max'] %}
                    Up to {{job['salary_max']}} {{job['salary_currency']}}
                  {% endif %}
                </p>
              </div>
            {% endif %}

            {% if job.get('benefits') %}
              <div class="mb-3">
                <h6 class="card-subtitle">Benefits</h6>
                <div class="d-flex flex-wrap gap-2">
                  {% for benefit in job['benefits'] %}
                    <span class="badge bg-success">{{benefit}}</span>
                  {% endfor %}
                </div>
              </div>
            {% endif %}
          </div>
          <div class="card-footer bg-white">
            <div class="d-flex justify-content-between align-items-center">
              {% if job['description'] or job['requirements'] %}
                <button type="button" class="btn btn-outline-primary" data-bs-toggle="modal" data-bs-target="#jobDetails{{job['id']}}">
                  <i class="bi bi-info-circle"></i> Details
                </button>
              {% else %}
                <button type="button" class="btn btn-outline-primary" disabled>
                  <i class="bi bi-info-circle"></i> No Details Available
                </button>
              {% endif %}
              <a href="{{job['url']}}" target="_blank" class="btn btn-success">
                <i class="bi bi-box-arrow-up-right"></i> Apply
              </a>
            </div>
          </div>
        </div>
      </div>

      <!-- Job Details Modal -->
      {% if job['description'] or job['requirements'] %}
        <div class="modal fade" id="jobDetails{{job['id']}}" tabindex="-1" aria-labelledby="jobDetailsLabel{{job['id']}}" aria-hidden="true">
          <div class="modal-dialog modal-lg">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title" id="jobDetailsLabel{{job['id']}}">{{job['title']}} at {{job['company']}}</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
              </div>
              <div class="modal-body">
                <div class="mb-4">
                  <h6>Company Information</h6>
                  <p class="mb-1"><strong>Location:</strong> {{job['location']}}</p>
                  <p class="mb-1"><strong>Posted:</strong> {{job['date_posted']}}</p>
                  <p class="mb-1"><strong>Platform:</strong> {{job['platform']}}</p>
                </div>

                {% if job['description'] %}
                  <div class="mb-4">
                    <h6>Job Description</h6>
                    <div class="job-description">
                      <div class="description-content">
                        {{job['description'] | replace('\n', '<br>') | safe}}
                      </div>
                    </div>
                  </div>
                {% endif %}

                {% if job['requirements'] %}
                  <div class="mb-4">
                    <h6>Requirements</h6>
                    <ul class="list-group">
                      {% for req in job['requirements'] %}
                        <li class="list-group-item">{{req}}</li>
                      {% endfor %}
                    </ul>
                  </div>
                {% endif %}

                {% if job.get('salary_min') or job.get('salary_max') %}
                  <div class="mb-4">
                    <h6>Salary Information</h6>
                    <p class="mb-0">
                      {% if job['salary_min'] and job['salary_max'] %}
                        {{job['salary_min']}} - {{job['salary_max']}} {{job['salary_currency']}}
                      {% elif job['salary_min'] %}
                        From {{job['salary_min']}} {{job['salary_currency']}}
                      {% elif job['salary_max'] %}
                        Up to {{job['salary_max']}} {{job['salary_currency']}}
                      {% endif %}
                    </p>
                  </div>
                {% endif %}

                {% if job.get('benefits') %}
                  <div class="mb-4">
                    <h6>Benefits</h6>
                    <div class="d-flex flex-wrap gap-2">
                      {% for benefit in job['benefits'] %}
                        <span class="badge bg-success">{{benefit}}</span>
                      {% endfor %}
                    </div>
                  </div>
                {% endif %}
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                <a href="{{job['url']}}" target="_blank" class="btn btn-success">Apply Now</a>
              </div>
            </div>
          </div>
        </div>
      {% endif %}
    {% endfor %}
  </div>
</div>

<style>
  .job-description {
    max-height: 200px;
    overflow-y: auto;
    padding: 10px;
    background-color: #f8f9fa;
    border-radius: 5px;
  }
  
  .description-content {
    white-space: pre-wrap;
    word-wrap: break-word;
  }
  
  .card {
    transition: transform 0.2s;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  }
  
  .card:hover {
    transform: translateY(-5px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
  }
  
  .badge {
    font-size: 0.9em;
    padding: 0.5em 0.8em;
  }
  
  .list-group-item {
    border-left: none;
    border-right: none;
  }
  
  .list-group-item:first-child {
    border-top: none;
  }
  
  .list-group-item:last-child {
    border-bottom: none;
  }
</style>

<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
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
    platform = request.form.get('platform','') if request.method=='POST' else ''
    
    if request.method=='POST':
        lst = fetch_all_jobs(keyword, location)
        save_listings(lst)
    
    conn = get_conn()
    rows = conn.execute('SELECT * FROM jobs ORDER BY fetched_at DESC').fetchall()
    conn.close()
    
    # Get unique locations and platforms for dropdowns
    locations = sorted(set(get_location_options() + [row['location'] for row in rows]))
    platforms = sorted(set(row['platform'] for row in rows))
    
    # Apply filters
    filter_loc = request.args.get('filter_loc','')
    filter_platform = request.args.get('filter_platform','')
    page = request.args.get('page',1,type=int)
    
    if filter_loc:
        rows = [r for r in rows if filter_loc.lower() in r['location'].lower()]
    if filter_platform:
        rows = [r for r in rows if filter_platform.lower() == r['platform'].lower()]
    
    total = len(rows)
    pages = (total + PER_PAGE - 1) // PER_PAGE
    page = max(1, min(page, pages))
    rows = rows[(page-1)*PER_PAGE : page*PER_PAGE]
    
    # Convert requirements from JSON string to list
    rows = [dict(r) for r in rows]
    for row in rows:
        try:
            row['requirements'] = json.loads(row['requirements'])
        except:
            row['requirements'] = []
    
    return render_template_string(
        SEARCH_HTML,
        keyword=keyword,
        location=location,
        platform=platform,
        filter_loc=filter_loc,
        filter_platform=filter_platform,
        page=page,
        pages=pages,
        rows=rows,
        locations=locations,
        platforms=platforms
    )

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

@app.route('/init-db')
def init_db_route():
    init_db()
    return 'Database initialized successfully!'

# RUNNING
# python3 -m flask --app app.py --debug run
