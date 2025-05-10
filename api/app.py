# app.py
# Flask-based Job Application Tracker with Search, Tracker, and Details pages

import os
import time
from flask import Flask, request, redirect, url_for, send_from_directory, jsonify
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
import re
from collections import Counter
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import PyPDF2
import docx
from flask_cors import CORS
import traceback
import pandas as pd

# CONFIGURATION
DB_PATH = 'jobs.db'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
ALLOWED_EXCEL_EXTENSIONS = {'xlsx', 'xls', 'csv'}
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
    # North America
    'United States', 'Canada', 'Mexico',
    
    # Europe
    'United Kingdom', 'Germany', 'France', 'Netherlands', 'Spain', 'Italy',
    'Switzerland', 'Sweden', 'Denmark', 'Norway', 'Finland', 'Ireland',
    'Belgium', 'Austria', 'Poland', 'Portugal', 'Greece', 'Czech Republic',
    
    # Asia
    'India', 'China', 'Japan', 'South Korea', 'Singapore', 'Hong Kong',
    'Malaysia', 'Thailand', 'Vietnam', 'Indonesia', 'Philippines',
    
    # Middle East
    'UAE', 'Saudi Arabia', 'Qatar', 'Kuwait', 'Bahrain', 'Oman',
    
    # Africa
    'South Africa', 'Egypt', 'Nigeria', 'Kenya', 'Morocco',
    
    # South America
    'Brazil', 'Argentina', 'Chile', 'Colombia', 'Peru',
    
    # Oceania
    'Australia', 'New Zealand',
    
    # Remote Options
    'Remote', 'Work from Home', 'Anywhere'
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def rate_limit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Add a random delay between 5-10 seconds
        delay = random.uniform(5, 10)
        print(f"\nWaiting {delay:.2f} seconds before next request...")
        time.sleep(delay)
        return func(*args, **kwargs)
    return wrapper

def get_location_options():
    return sorted(COMMON_LOCATIONS)

@rate_limit
def fetch_linkedin_jobs(keyword, location):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'DNT': '1'
        }
        
        jobs = []
        # LinkedIn paginates with the 'start' parameter (0, 25, 50, ...)
        for start in range(0, 250, 25):  # Fetch 10 pages (0, 25, ..., 225)
            if location.lower() in ['remote', 'work from home', 'anywhere']:
                search_url = f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(keyword)}&location=Worldwide&f_WT=2&start={start}"
            else:
                search_url = f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(keyword)}&location={quote_plus(location)}&start={start}"
            print(f"\nFetching LinkedIn jobs from: {search_url}")
            session = requests.Session()
            try:
                response = session.get('https://www.linkedin.com', headers=headers, timeout=10)
                response.raise_for_status()
                time.sleep(random.uniform(2, 4))
            except Exception as e:
                print(f"Warning: Could not access LinkedIn main page: {str(e)}")
            response = session.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()
            print(f"LinkedIn response status code: {response.status_code}")
            print(f"LinkedIn response content type: {response.headers.get('content-type', 'unknown')}")
            print(f"LinkedIn response length: {len(response.text)}")
            soup = BeautifulSoup(response.text, 'html.parser')
            job_cards = soup.select('.jobs-search__results-list li') or soup.select('.job-card-container')
            print(f"Found {len(job_cards)} LinkedIn job cards on page starting at {start}")
            for job_card in job_cards:
                try:
                    title_elem = (
                        job_card.select_one('.base-search-card__title') or 
                        job_card.select_one('.job-card-list__title') or
                        job_card.select_one('.job-search-card__title')
                    )
                    company_elem = (
                        job_card.select_one('.base-search-card__subtitle') or 
                        job_card.select_one('.job-card-container__company-name') or
                        job_card.select_one('.job-search-card__company-name')
                    )
                    location_elem = (
                        job_card.select_one('.job-search-card__location') or 
                        job_card.select_one('.job-card-container__metadata-item') or
                        job_card.select_one('.job-search-card__location')
                    )
                    link_elem = (
                        job_card.select_one('a.base-card__full-link') or 
                        job_card.select_one('a.job-card-container__link') or
                        job_card.select_one('a.job-search-card__link')
                    )
                    if not all([title_elem, company_elem, location_elem, link_elem]):
                        continue
                    job_location = location_elem.text.strip()
                    job = {
                        'title': title_elem.text.strip(),
                        'company': company_elem.text.strip(),
                        'company_info': '',
                        'location': job_location,
                        'url': link_elem['href'],
                        'date_posted': datetime.now().strftime('%Y-%m-%d'),
                        'platform': 'LinkedIn',
                        'description': 'Click "Details" to view full description',
                        'requirements': [],
                        'match_score': 'N/A',
                        'salary_min': '',
                        'salary_max': '',
                        'salary_currency': '',
                        'benefits': []
                    }
                    jobs.append(job)
                    print(f"Added LinkedIn job: {job['title']} at {job['company']}")
                except Exception as e:
                    print(f"Error parsing LinkedIn job card: {str(e)}")
                    continue
            # Add a short delay between page fetches to avoid being blocked
            time.sleep(random.uniform(2, 4))
        print(f"Found {len(jobs)} total LinkedIn jobs across all pages")
        return jobs
    except Exception as e:
        print(f"Error fetching LinkedIn jobs: {str(e)}")
        return []

@rate_limit
def fetch_indeed_jobs(keyword, location):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'DNT': '1'
        }
        
        # Handle remote locations
        if location.lower() in ['remote', 'work from home', 'anywhere']:
            search_url = f"https://www.indeed.com/jobs?q={quote_plus(keyword)}&sc=0kf%3Aattr(FSFW)%3B"
        else:
            search_url = f"https://www.indeed.com/jobs?q={quote_plus(keyword)}&l={quote_plus(location)}"
        
        print(f"\nFetching Indeed jobs from: {search_url}")
        session = requests.Session()
        
        # First make a GET request to the main page
        try:
            response = session.get('https://www.indeed.com', headers=headers, timeout=10)
            response.raise_for_status()
            time.sleep(random.uniform(2, 4))  # Wait before the next request
        except Exception as e:
            print(f"Warning: Could not access Indeed main page: {str(e)}")
        
        # Now fetch the search results
        response = session.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        print(f"Indeed response status code: {response.status_code}")
        print(f"Indeed response content type: {response.headers.get('content-type', 'unknown')}")
        print(f"Indeed response length: {len(response.text)}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        jobs = []
        
        # Try different selectors for job cards
        job_cards = soup.select('.job_seen_beacon') or soup.select('.jobsearch-ResultsList > div')
        print(f"Found {len(job_cards)} Indeed job cards")
        
        for job_card in job_cards:
            try:
                # Try different selectors for each element
                title_elem = (
                    job_card.select_one('.jobTitle') or 
                    job_card.select_one('.jcs-JobTitle') or
                    job_card.select_one('.jobsearch-JobComponent-title')
                )
                company_elem = (
                    job_card.select_one('.companyName') or 
                    job_card.select_one('.companyLocation') or
                    job_card.select_one('.jobsearch-CompanyInfoContainer')
                )
                location_elem = (
                    job_card.select_one('.companyLocation') or 
                    job_card.select_one('.jobsearch-CompanyLocation') or
                    job_card.select_one('.jobsearch-CompanyInfoContainer')
                )
                link_elem = (
                    job_card.select_one('a.jcs-JobTitle') or 
                    job_card.select_one('a.jobLink') or
                    job_card.select_one('a.jobsearch-JobComponent-title')
                )
                
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
                    'description': 'Click "Details" to view full description',
                    'requirements': [],
                    'match_score': 'N/A',
                    'salary_min': '',
                    'salary_max': '',
                    'salary_currency': '',
                    'benefits': []
                }
                
                jobs.append(job)
                print(f"Added Indeed job: {job['title']} at {job['company']}")
            except Exception as e:
                print(f"Error parsing Indeed job card: {str(e)}")
                continue
        
        print(f"Found {len(jobs)} Indeed jobs")
        return jobs
    except Exception as e:
        print(f"Error fetching Indeed jobs: {str(e)}")
        return []

@rate_limit
def fetch_ziprecruiter_jobs(keyword, location):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'DNT': '1'
        }
        
        # Handle remote locations
        if location.lower() in ['remote', 'work from home', 'anywhere']:
            search_url = f"https://www.ziprecruiter.com/jobs-search?search={quote_plus(keyword)}&location=Remote"
        else:
            search_url = f"https://www.ziprecruiter.com/jobs-search?search={quote_plus(keyword)}&location={quote_plus(location)}"
        
        print(f"\nFetching ZipRecruiter jobs from: {search_url}")
        session = requests.Session()
        
        # First make a GET request to the main page
        try:
            response = session.get('https://www.ziprecruiter.com', headers=headers, timeout=10)
            response.raise_for_status()
            time.sleep(random.uniform(2, 4))  # Wait before the next request
        except Exception as e:
            print(f"Warning: Could not access ZipRecruiter main page: {str(e)}")
        
        # Now fetch the search results
        response = session.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        print(f"ZipRecruiter response status code: {response.status_code}")
        print(f"ZipRecruiter response content type: {response.headers.get('content-type', 'unknown')}")
        print(f"ZipRecruiter response length: {len(response.text)}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        jobs = []
        
        # Try different selectors for job cards
        job_cards = soup.select('.job_content') or soup.select('.job-listing')
        print(f"Found {len(job_cards)} ZipRecruiter job cards")
        
        for job_card in job_cards:
            try:
                # Try different selectors for each element
                title_elem = (
                    job_card.select_one('.job_title') or 
                    job_card.select_one('.job-title') or
                    job_card.select_one('.job-listing-title')
                )
                company_elem = (
                    job_card.select_one('.company_name') or 
                    job_card.select_one('.company-name') or
                    job_card.select_one('.job-listing-company')
                )
                location_elem = (
                    job_card.select_one('.location') or 
                    job_card.select_one('.job-location') or
                    job_card.select_one('.job-listing-location')
                )
                link_elem = (
                    job_card.select_one('a.job_link') or 
                    job_card.select_one('a.job-link') or
                    job_card.select_one('a.job-listing-link')
                )
                
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
                    'description': 'Click "Details" to view full description',
                    'requirements': [],
                    'match_score': 'N/A',
                    'salary_min': '',
                    'salary_max': '',
                    'salary_currency': '',
                    'benefits': []
                }
                
                jobs.append(job)
                print(f"Added ZipRecruiter job: {job['title']} at {job['company']}")
            except Exception as e:
                print(f"Error parsing ZipRecruiter job card: {str(e)}")
                continue
        
        print(f"Found {len(jobs)} ZipRecruiter jobs")
        return jobs
    except Exception as e:
        print(f"Error fetching ZipRecruiter jobs: {str(e)}")
        return []

def fetch_all_jobs(keyword, location):
    print(f"\nFetching jobs for keyword: {keyword}, location: {location}")
    jobs = []
    
    # Clear existing jobs from database for this search
    conn = get_conn()
    conn.execute('DELETE FROM jobs')
    conn.commit()
    conn.close()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(fetch_linkedin_jobs, keyword, location),
            executor.submit(fetch_indeed_jobs, keyword, location),
            executor.submit(fetch_ziprecruiter_jobs, keyword, location)
        ]
        
        for future in futures:
            try:
                platform_jobs = future.result()
                if platform_jobs:  # Only extend if we got jobs
                    jobs.extend(platform_jobs)
            except Exception as e:
                print(f"Error in job fetch: {str(e)}")
    
    # Remove duplicates based on URL
    seen_urls = set()
    unique_jobs = []
    for job in jobs:
        if job['url'] not in seen_urls:
            seen_urls.add(job['url'])
            unique_jobs.append(job)
    
    print(f"Total unique jobs found: {len(unique_jobs)}")
    # Print first few jobs for debugging
    for i, job in enumerate(unique_jobs[:3]):
        print(f"Job {i+1}: {job['title']} at {job['company']} in {job['location']}")
    
    # Save the jobs to the database
    if unique_jobs:
        save_listings(unique_jobs)
    
    return unique_jobs

def fetch_job_details(url):
    """Fetch detailed job information from the job posting URL."""
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract job description
        description = ''
        description_elem = (
            soup.select_one('.job-description') or 
            soup.select_one('.description__text') or
            soup.select_one('.job-description__content') or
            soup.select_one('.show-more-less-html__markup')
        )
        if description_elem:
            description = description_elem.get_text(strip=True)
        
        # Extract requirements
        requirements = []
        requirements_elem = (
            soup.select_one('.job-criteria-list') or
            soup.select_one('.job-criteria') or
            soup.select_one('.job-requirements')
        )
        if requirements_elem:
            requirements = [req.strip() for req in requirements_elem.get_text().split('\n') if req.strip()]
        
        # Extract benefits
        benefits = []
        benefits_elem = (
            soup.select_one('.job-benefits') or
            soup.select_one('.benefits') or
            soup.select_one('.job-perks')
        )
        if benefits_elem:
            benefits = [benefit.strip() for benefit in benefits_elem.get_text().split('\n') if benefit.strip()]
        
        # Extract salary information
        salary_info = ''
        salary_elem = (
            soup.select_one('.salary') or
            soup.select_one('.compensation') or
            soup.select_one('.job-salary')
        )
        if salary_elem:
            salary_info = salary_elem.get_text(strip=True)
        
        return {
            'description': description,
            'requirements': requirements,
            'benefits': benefits,
            'salary_info': salary_info
        }
    except Exception as e:
        print(f"Error fetching job details: {str(e)}")
        return {
            'description': 'Error fetching job details. Please try again later.',
            'requirements': [],
            'benefits': [],
            'salary_info': ''
        }

# APP INIT
print(f"=== Loading UPDATED app.py at {time.asctime()} ===")
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow all origins for all routes
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['HOST'] = '0.0.0.0'  # Use IP instead of localhost
app.config['PORT'] = 8080  # Update port to match frontend

# Add error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Add before_request handler to ensure proper CORS
@app.before_request
def before_request():
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept'
        return response

# DB UTILITIES
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    
    # Create jobs table
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY,
            title TEXT,
            company TEXT,
            company_info TEXT,
            location TEXT,
            url TEXT UNIQUE,
            date_posted TEXT,
            platform TEXT,
            requirements TEXT,
            description TEXT,
            match_score TEXT,
            fetched_at TIMESTAMP
        )
    ''')
    
    # Create applications table
    c.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY,
            job_id INTEGER,
            status TEXT,
            applied_at DATE,
            company TEXT,
            location TEXT,
            referral TEXT,
            job_link TEXT UNIQUE,
            referral_mail TEXT,
            title TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs (id)
        )
    ''')
    
    # Create saved_jobs table
    c.execute('''
        CREATE TABLE IF NOT EXISTS saved_jobs (
            id INTEGER PRIMARY KEY,
            job_id INTEGER,
            saved_at TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs (id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# ALLOWED FILE
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_excel_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXCEL_EXTENSIONS

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

@app.route('/api/search', methods=['GET', 'POST'])
def search():
    print("\n=== Search Request ===")
    print(f"Method: {request.method}")
    print(f"Form data: {request.form}")
    print(f"Args: {request.args}")
    
    keyword = request.args.get('keyword', '')
    location = request.args.get('location', '')
    platform = request.args.get('platform', '')
    page = int(request.args.get('page', 1))
    sort_by = request.args.get('sort_by', 'date_posted')  # New parameter for sorting
    sort_order = request.args.get('sort_order', 'desc')   # New parameter for sort order
    
    print(f"Search parameters - Keyword: {keyword}, Location: {location}, Platform: {platform}, Sort: {sort_by} {sort_order}")
    
    try:
        # Clear old jobs and fetch new ones
        conn = get_conn()
        conn.execute('DELETE FROM jobs')
        conn.commit()
        
        # Fetch jobs based on platform selection
        jobs = []
        if platform:
            if platform == 'LinkedIn':
                jobs.extend(fetch_linkedin_jobs(keyword, location))
            elif platform == 'Indeed':
                jobs.extend(fetch_indeed_jobs(keyword, location))
            elif platform == 'ZipRecruiter':
                jobs.extend(fetch_ziprecruiter_jobs(keyword, location))
        else:
            # Fetch from all platforms if no specific platform is selected
            jobs.extend(fetch_linkedin_jobs(keyword, location))
            try:
                jobs.extend(fetch_indeed_jobs(keyword, location))
            except Exception as e:
                print(f"Error fetching Indeed jobs: {str(e)}")
            try:
                jobs.extend(fetch_ziprecruiter_jobs(keyword, location))
            except Exception as e:
                print(f"Error fetching ZipRecruiter jobs: {str(e)}")
        
        print(f"DEBUG: Jobs fetched: {len(jobs)}")
        # Save the jobs to database
        if jobs:
            save_listings(jobs)
        
        # Get all jobs from database with sorting
        sort_column = {
            'date_posted': 'date_posted',
            'title': 'title',
            'company': 'company',
            'location': 'location',
            'match_score': 'match_score'
        }.get(sort_by, 'date_posted')
        
        sort_direction = 'DESC' if sort_order.lower() == 'desc' else 'ASC'
        
        # Handle special case for match_score which might be 'N/A'
        if sort_by == 'match_score':
            query = f'''
                SELECT * FROM jobs 
                ORDER BY 
                    CASE 
                        WHEN match_score = 'N/A' THEN 1 
                        ELSE 0 
                    END,
                    CAST(REPLACE(match_score, '%', '') AS FLOAT) {sort_direction}
            '''
        else:
            query = f'SELECT * FROM jobs ORDER BY {sort_column} {sort_direction}'
            
        jobs = conn.execute(query).fetchall()
        print(f"DEBUG: Jobs in DB after save: {len(jobs)}")
        conn.close()
        
        # Filter jobs based on search criteria with more flexible matching
        filtered_jobs = []
        for job in jobs:
            # More flexible keyword matching
            keyword_match = (
                not keyword or
                keyword.lower() in job['title'].lower() or
                keyword.lower() in job['company'].lower() or
                keyword.lower() in job['description'].lower()
            )
            # More flexible location matching
            if ',' in location:
                location_list = [loc.strip().lower() for loc in location.split(',') if loc.strip()]
            else:
                location_list = [location.lower()] if location else []
            location_match = any(loc in job['location'].lower() for loc in location_list)
            # Platform matching
            platform_match = not platform or platform == job['platform']
            if keyword_match and location_match and platform_match:
                filtered_jobs.append(dict(job))
        print(f"DEBUG: Filtered jobs: {len(filtered_jobs)}")
        # Deduplicate jobs by title, company, and location
        seen = set()
        unique_jobs = []
        for job in filtered_jobs:
            key = (job['title'].lower(), job['company'].lower(), job['location'].lower())
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)
        filtered_jobs = unique_jobs
        print(f"DEBUG: Unique jobs after deduplication: {len(filtered_jobs)}")
        # Pagination
        total_jobs = len(filtered_jobs)
        jobs_per_page = 5
        total_pages = (total_jobs + jobs_per_page - 1) // jobs_per_page
        start_idx = (page - 1) * jobs_per_page
        end_idx = start_idx + jobs_per_page
        paginated_jobs = filtered_jobs[start_idx:end_idx]
        print(f"DEBUG: Paginated jobs: {len(paginated_jobs)}")
        # Get unique locations and platforms for filters
        locations = sorted(list(set(job['location'] for job in jobs)))
        platforms = sorted(list(set(job['platform'] for job in jobs)))
        response_data = {
            'jobs': paginated_jobs,
            'total': total_jobs,
            'pages': total_pages,
            'current_page': page,
            'locations': locations,
            'platforms': platforms,
            'sort_by': sort_by,
            'sort_order': sort_order
        }
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in search function: {str(e)}")
        import traceback; traceback.print_exc()
        return jsonify({
            'error': str(e),
            'jobs': [],
            'total': 0,
            'pages': 0,
            'current_page': page,
            'locations': [],
            'platforms': [],
            'sort_by': sort_by,
            'sort_order': sort_order
        }), 500

@app.route('/api/db-status', methods=['GET'])
def db_status():
    try:
        conn = get_conn()
        cursor = conn.cursor()
        
        # Check applications table
        cursor.execute("SELECT COUNT(*) FROM applications")
        app_count = cursor.fetchone()[0]
        
        # Check jobs table
        cursor.execute("SELECT COUNT(*) FROM jobs")
        jobs_count = cursor.fetchone()[0]
        
        # Check table structure
        cursor.execute("PRAGMA table_info(applications)")
        app_columns = cursor.fetchall()
        
        cursor.execute("PRAGMA table_info(jobs)")
        jobs_columns = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'applications_count': app_count,
            'jobs_count': jobs_count,
            'applications_columns': [dict(col) for col in app_columns],
            'jobs_columns': [dict(col) for col in jobs_columns]
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/tracker', methods=['GET'])
def tracker():
    try:
        conn = get_conn()
        print('DEBUG: Checking database connection...')
        print('DEBUG: Database path:', DB_PATH)
        # First check if we have any applications
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM applications')
        count = cursor.fetchone()[0]
        print(f'DEBUG: Total applications in database: {count}')
        # Get all applications with their details
        apps = conn.execute('''
            SELECT a.*, j.title as job_title 
            FROM applications a 
            LEFT JOIN jobs j ON a.job_id = j.id 
            WHERE a.status = "Applied"
        ''').fetchall()
        print(f'DEBUG: Found {len(apps)} applied applications')
        for app in apps:
            print(f'DEBUG: Application: {dict(app)}')
        def safe_dict(row):
            d = dict(row)
            for k, v in d.items():
                if v is None:
                    d[k] = ''
            return d
        conn.close()
        return jsonify({'applications': [safe_dict(app) for app in apps]})
    except Exception as e:
        import traceback
        print(f"Error in /api/tracker: {str(e)}")
        traceback.print_exc()
        return jsonify({'applications': [], 'error': str(e)}), 500

@app.route('/api/saved_jobs', methods=['GET'])
def saved_jobs():
    conn = get_conn()
    try:
        page = request.args.get('page', 1, type=int)
        per_page = PER_PAGE
        all_jobs = conn.execute('''
            SELECT j.*, sj.saved_at 
            FROM jobs j 
            JOIN saved_jobs sj ON j.id = sj.job_id 
            ORDER BY sj.saved_at DESC
        ''').fetchall()
        total = len(all_jobs)
        pages = (total + per_page - 1) // per_page
        page = max(1, min(page, pages)) if pages > 0 else 1
        jobs = all_jobs[(page-1)*per_page : page*per_page]
        jobs = [dict(job) for job in jobs]
        return jsonify({
            'saved_jobs': jobs,
            'total': total,
            'pages': pages,
            'current_page': page
        })
    finally:
        conn.close()

@app.route('/api/details', methods=['GET', 'POST'])
def details():
    error = None
    conn = get_conn()
    res = conn.execute('SELECT * FROM resume ORDER BY uploaded_at DESC LIMIT 1').fetchone()
    resume = dict(res) if res else None
    if request.method == 'POST':
        if 'file' not in request.files:
            error = 'No file selected'
        else:
            file = request.files['file']
            if file.filename == '':
                error = 'No file selected'
            elif not allowed_file(file.filename):
                error = 'Invalid file type. Please upload PDF, DOC, DOCX, or TXT files only.'
            else:
                try:
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    file_content = file.read()
                    file_size = len(file_content)
                    file.seek(0)
                    if file_size > 5 * 1024 * 1024:
                        error = 'File size exceeds 5MB limit'
                    else:
                        if resume:
                            old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], resume['filename'])
                            if os.path.exists(old_file_path):
                                os.remove(old_file_path)
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        conn = get_conn()
                        conn.execute('INSERT INTO resume (filename, uploaded_at) VALUES (?,?)',
                                   (filename, datetime.now().strftime('%Y-%m-%d %H:%M')))
                        conn.commit()
                        conn.close()
                        resume = {'filename': filename, 'uploaded_at': datetime.now().strftime('%Y-%m-%d %H:%M')}
                except Exception as e:
                    error = f'Error uploading file: {str(e)}'
    conn.close()
    if error:
        return jsonify({'error': error})
    return jsonify({'resume': resume})

@app.route('/api/delete_resume', methods=['POST'])
def delete_resume():
    conn = get_conn()
    res = conn.execute('SELECT filename FROM resume ORDER BY uploaded_at DESC LIMIT 1').fetchone()
    
    if res:
        filename = res['filename']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Delete file from filesystem
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete from database
        conn.execute('DELETE FROM resume WHERE filename = ?', (filename,))
        conn.commit()
    
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/uploads/<path:filename>')
def download(filename): 
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/_ping')
def ping(): 
    return jsonify({'status': 'pong'})

@app.route('/api/init-db')
def init_db_route():
    init_db()
    return jsonify({'status': 'success', 'message': 'Database initialized successfully!'})

@app.route('/api/job_details/<int:job_id>', methods=['GET'])
def job_details(job_id):
    """Get detailed information about a specific job."""
    try:
        conn = get_conn()
        job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
        if not job:
            return jsonify({'error': 'Job not found'}), 404

        job = dict(job)
        
        # Only fetch details if they haven't been fetched before
        if not job.get('description') or job['description'] == 'Click "Details" to view full description':
            try:
                details = fetch_job_details(job['url'])
                job.update(details)
                
                # Update the database with the fetched details
                conn.execute('''
                    UPDATE jobs 
                    SET description = ?, requirements = ?
                    WHERE id = ?
                ''', (
                    job['description'],
                    json.dumps(job.get('requirements', [])),
                    job_id
                ))
                conn.commit()
            except Exception as e:
                print(f"Error fetching job details: {str(e)}")
                return jsonify({"error": str(e)}), 500
        
        # Get resume skills
        resume_skills = {}
        resume = conn.execute('SELECT * FROM resume ORDER BY uploaded_at DESC LIMIT 1').fetchone()
        if resume:
            resume_path = os.path.join(app.config['UPLOAD_FOLDER'], resume['filename'])
            if os.path.exists(resume_path):
                resume_text = extract_text_from_file(resume_path)
                resume_skills, _ = extract_skills_from_text(resume_text)
        
        # Calculate match percentage
        match_percentage, matched_skills, missing_skills = calculate_job_match(
            job['description'], resume_skills
        )
        
        # Add match information to job details
        job['match_percentage'] = round(match_percentage, 1)
        job['matched_skills'] = matched_skills
        job['missing_skills'] = missing_skills
        
        conn.close()
        return jsonify(job)
    except Exception as e:
        print(f"Error in job_details: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/apply_job/<int:job_id>', methods=['POST'])
def apply_job(job_id):
    conn = get_conn()
    try:
        data = request.get_json(silent=True) or {}
        status = data.get('status', 'Applied')
        # Fetch job details from jobs table
        job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
        if not job:
            return jsonify({'status': 'error', 'message': 'Job not found'}), 404
        # Extract job details
        company = job['company']
        location = job['location']
        job_link = job['url']
        title = job['title']
        # Check if application already exists
        app_row = conn.execute('SELECT id FROM applications WHERE job_id = ?', (job_id,)).fetchone()
        if app_row:
            # Update status and details if needed
            conn.execute('UPDATE applications SET status = ?, company = ?, location = ?, job_link = ?, title = ? WHERE job_id = ?', (status, company, location, job_link, title, job_id))
        else:
            conn.execute('INSERT INTO applications (job_id, status, company, location, job_link, title, applied_at) VALUES (?, ?, ?, ?, ?, ?, ?)', (job_id, status, company, location, job_link, title, datetime.now()))
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error in apply_job: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/update_application_status/<int:app_id>', methods=['POST'])
def update_application_status(app_id):
    conn = None
    try:
        data = request.get_json()
        new_status = data.get('status')
        referral = data.get('referral')
        referral_mail = data.get('referral_mail')
        
        if not new_status:
            return jsonify({'status': 'error', 'message': 'Status is required'}), 400
            
        conn = get_conn()
        
        # Check if application exists
        application = conn.execute('SELECT id FROM applications WHERE id = ?', (app_id,)).fetchone()
        if not application:
            return jsonify({'status': 'error', 'message': 'Application not found'}), 404
            
        if new_status == 'Open':
            # Remove the application record
            conn.execute('DELETE FROM applications WHERE id = ?', (app_id,))
        else:
            # Update the application status and other fields
            conn.execute('''
                UPDATE applications 
                SET status = ?, 
                    referral = ?,
                    referral_mail = ?
                WHERE id = ?
            ''', (new_status, referral, referral_mail, app_id))
            
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error updating application status: {str(e)}")
        if conn:
            conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/save_job/<int:job_id>', methods=['POST', 'DELETE'])
def save_job(job_id):
    conn = get_conn()
    try:
        if request.method == 'POST':
            # Check if already saved
            exists = conn.execute('SELECT 1 FROM saved_jobs WHERE job_id = ?', (job_id,)).fetchone()
            if exists:
                return jsonify({'status': 'already_saved'})
            conn.execute('INSERT INTO saved_jobs (job_id, saved_at) VALUES (?, ?)', (job_id, datetime.now()))
            conn.commit()
            return jsonify({'status': 'success'})
        elif request.method == 'DELETE':
            # Unsave job
            exists = conn.execute('SELECT 1 FROM saved_jobs WHERE job_id = ?', (job_id,)).fetchone()
            if not exists:
                return jsonify({'status': 'not_saved'})
            conn.execute('DELETE FROM saved_jobs WHERE job_id = ?', (job_id,))
            conn.commit()
            return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

# Load spaCy model
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    import subprocess
    subprocess.run(['python', '-m', 'spacy', 'download', 'en_core_web_sm'])
    nlp = spacy.load('en_core_web_sm')

# Common technical skills and keywords
TECHNICAL_SKILLS = {
    'Programming Languages': [
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'go', 'rust',
        'scala', 'perl', 'r', 'matlab', 'sql', 'bash', 'powershell', 'assembly', 'haskell', 'elixir'
    ],
    'Web Technologies': [
        'html', 'css', 'sass', 'less', 'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask',
        'spring', 'asp.net', 'laravel', 'ruby on rails', 'graphql', 'rest api', 'websocket', 'jquery',
        'bootstrap', 'tailwind', 'material-ui', 'next.js', 'nuxt.js', 'gatsby'
    ],
    'Databases': [
        'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'oracle', 'sqlite', 'cassandra', 'elasticsearch',
        'dynamodb', 'neo4j', 'couchdb', 'mariadb', 'firebase', 'cosmos db', 'bigquery', 'snowflake'
    ],
    'Cloud Platforms': [
        'aws', 'azure', 'gcp', 'heroku', 'digitalocean', 'linode', 'vultr', 'alibaba cloud', 'ibm cloud',
        'oracle cloud', 'cloudflare', 'netlify', 'vercel'
    ],
    'DevOps & Tools': [
        'docker', 'kubernetes', 'jenkins', 'git', 'ci/cd', 'terraform', 'ansible', 'puppet', 'chef',
        'prometheus', 'grafana', 'elk stack', 'splunk', 'nagios', 'jira', 'confluence', 'bitbucket',
        'github actions', 'gitlab ci', 'circleci', 'travis ci', 'teamcity'
    ],
    'AI/ML': [
        'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn', 'keras', 'nlp',
        'computer vision', 'opencv', 'nltk', 'spacy', 'bert', 'gpt', 'transformer', 'reinforcement learning',
        'neural networks', 'cnn', 'rnn', 'lstm', 'gan', 'svm', 'random forest', 'xgboost', 'lightgbm',
        'ai', 'artificial intelligence', 'ai-powered', 'ai applications'
    ],
    'Data Science': [
        'pandas', 'numpy', 'matplotlib', 'seaborn', 'r', 'tableau', 'power bi', 'looker', 'qlik',
        'apache spark', 'hadoop', 'hive', 'pig', 'kafka', 'airflow', 'dbt', 'databricks', 'jupyter',
        'data visualization', 'statistical analysis', 'a/b testing', 'experiment design', 'kpi analysis',
        'metrics tracking', 'data analytics'
    ],
    'Mobile Development': [
        'android', 'ios', 'react native', 'flutter', 'xamarin', 'swift', 'kotlin', 'objective-c',
        'mobile ui/ux', 'mobile testing', 'app store', 'play store', 'mobile security'
    ],
    'Security': [
        'cybersecurity', 'penetration testing', 'network security', 'cryptography', 'ssl/tls',
        'authentication', 'authorization', 'oauth', 'jwt', 'saml', 'mfa', 'vulnerability assessment',
        'security compliance', 'gdpr', 'hipaa', 'pci dss', 'iso 27001', 'nist', 'owasp'
    ],
    'Project Management': [
        'agile', 'scrum', 'kanban', 'jira', 'trello', 'asana', 'monday.com', 'project management',
        'product management', 'sprint planning', 'retrospectives', 'user stories', 'backlog grooming',
        'risk management', 'stakeholder management', 'product strategy', 'product development',
        'product lifecycle', 'product roadmap', 'market analysis', 'competitive analysis',
        'product requirements', 'mvp development', 'go-to-market strategy'
    ],
    'Soft Skills': [
        'leadership', 'communication', 'teamwork', 'problem-solving', 'time management', 'collaboration',
        'adaptability', 'critical thinking', 'creativity', 'emotional intelligence', 'conflict resolution',
        'mentoring', 'presentation skills', 'negotiation', 'decision making', 'strategic thinking',
        'team working', 'organizational skills', 'analytical skills', 'english', 'multilingual'
    ],
    'Business Skills': [
        'retail', 'e-commerce', 'sales', 'marketing', 'business development', 'customer service',
        'market research', 'competitive analysis', 'strategic planning', 'business strategy',
        'financial analysis', 'budgeting', 'forecasting', 'vendor management', 'client relations',
        'stakeholder management', 'contract negotiation', 'business operations', 'supply chain',
        'inventory management', 'retail operations', 'merchandising', 'brand management'
    ],
    'Methodologies': [
        'agile', 'scrum', 'kanban', 'waterfall', 'devops', 'ci/cd', 'tdd', 'bdd', 'pair programming',
        'code review', 'technical documentation', 'api design', 'microservices', 'domain-driven design',
        'test-driven development', 'behavior-driven development', 'lean methodology', 'six sigma',
        'design thinking', 'user-centered design'
    ],
    'Industry-Specific': [
        'pos', 'point of sale', 'point-of-sale', 'pos systems', 'pos technology', 'pos products',
        'hospitality', 'catering', 'food service', 'retail tech', 'digital screens', 'kitchen display',
        'kiosks', 'user-facing systems', 'physical systems', 'digital applications', 'contract catering',
        'hospitality industry', 'catering industry', 'food service industry', 'retail industry'
    ]
}

def extract_text_from_file(file_path):
    """Extract text from different file formats."""
    file_ext = file_path.split('.')[-1].lower()
    
    try:
        if file_ext == 'pdf':
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ''
                for page in pdf_reader.pages:
                    text += page.extract_text()
                return text
        elif file_ext in ['doc', 'docx']:
            doc = docx.Document(file_path)
            return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        elif file_ext == 'txt':
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        else:
            return ''
    except Exception as e:
        print(f"Error extracting text from file: {str(e)}")
        return ''

def extract_skills_from_text(text):
    """Extract skills from text using NLP and keyword matching."""
    # Convert text to lowercase
    text = text.lower()
    
    # Extract named entities using spaCy
    doc = nlp(text)
    entities = [ent.text.lower() for ent in doc.ents if ent.label_ in ['ORG', 'PRODUCT']]
    
    # Initialize skills dictionary
    found_skills = {
        'requirements': set(),
        'experience': set(),
        'responsibilities': set()
    }
    
    # Extract skills using context-based patterns
    skill_patterns = {
        'requirements': [
            r'required (?:skills|experience|knowledge) (?:in|with|of) ([^.,]+)',
            r'must have (?:experience|knowledge) (?:in|with|of) ([^.,]+)',
            r'should have (?:experience|knowledge) (?:in|with|of) ([^.,]+)',
            r'looking for (?:experience|knowledge) (?:in|with|of) ([^.,]+)',
            r'seeking (?:experience|knowledge) (?:in|with|of) ([^.,]+)',
            r'candidates should have (?:experience|knowledge) (?:in|with|of) ([^.,]+)'
        ],
        'experience': [
            r'experience (?:with|in|of) ([^.,]+)',
            r'familiar (?:with|in) ([^.,]+)',
            r'knowledge (?:of|in) ([^.,]+)',
            r'proficient (?:in|with) ([^.,]+)',
            r'expertise (?:in|with) ([^.,]+)',
            r'working (?:with|in) ([^.,]+)',
            r'using ([^.,]+)',
            r'([^.,]+) experience',
            r'([^.,]+) knowledge',
            r'([^.,]+) skills',
            r'([^.,]+) development',
            r'([^.,]+) programming',
            r'([^.,]+) systems',
            r'([^.,]+) products',
            r'([^.,]+) applications',
            r'([^.,]+) technology'
        ],
        'responsibilities': [
            r'responsible for ([^.,]+)',
            r'managing ([^.,]+)',
            r'developing ([^.,]+)',
            r'creating ([^.,]+)',
            r'building ([^.,]+)',
            r'designing ([^.,]+)',
            r'implementing ([^.,]+)',
            r'maintaining ([^.,]+)'
        ]
    }
    
    # Extract skills using patterns
    for context, patterns in skill_patterns.items():
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                skill = match.group(1).strip()
                # Clean up the skill text
                skill = re.sub(r'\b(?:and|or|with|in|of)\b', '', skill).strip()
                if len(skill) > 2:  # Avoid single words or very short phrases
                    found_skills[context].add(skill)
    
    # Match extracted skills against known technical skills
    matched_skills = {
        'requirements': set(),
        'experience': set(),
        'responsibilities': set()
    }
    
    for category, skills in TECHNICAL_SKILLS.items():
        for skill in skills:
            skill_lower = skill.lower()
            for context in found_skills:
                for extracted_skill in found_skills[context]:
                    if (skill_lower in extracted_skill.lower() or 
                        extracted_skill.lower() in skill_lower):
                        matched_skills[context].add(skill)
    
    # Convert sets to lists
    return {k: list(v) for k, v in matched_skills.items()}, entities

def calculate_job_match(job_description, resume_skills):
    """Calculate job match percentage based on skills and requirements."""
    # Extract skills from job description
    job_skills, _ = extract_skills_from_text(job_description)
    
    # Calculate match score
    total_skills = 0
    matched_skills = {}
    missing_skills = {}
    
    # Weight different contexts differently
    context_weights = {
        'requirements': 1.5,  # Required skills are most important
        'experience': 1.3,    # Experience is second most important
        'responsibilities': 1.0  # Responsibilities are least important
    }
    
    for context, skills in job_skills.items():
        weight = context_weights.get(context, 1.0)
        total_skills += len(skills) * weight
        
        # Find matches in resume
        matched = []
        missing = []
        
        for skill in skills:
            # Check for exact matches and partial matches
            skill_matched = False
            for resume_context, resume_skill_list in resume_skills.items():
                for resume_skill in resume_skill_list:
                    # Check for exact match or if one is contained in the other
                    if (skill.lower() == resume_skill.lower() or
                        skill.lower() in resume_skill.lower() or
                        resume_skill.lower() in skill.lower()):
                        matched.append(skill)
                        skill_matched = True
                        break
                if skill_matched:
                    break
            
            if not skill_matched:
                missing.append(skill)
        
        if matched:
            matched_skills[context] = {
                'skills': matched,
                'level': 'expert' if context == 'requirements' else 'intermediate' if context == 'experience' else 'basic'
            }
        
        if missing:
            missing_skills[context] = {
                'skills': missing,
                'level': 'expert' if context == 'requirements' else 'intermediate' if context == 'experience' else 'basic'
            }
    
    # Calculate match percentage
    if total_skills == 0:
        return 0, {}, {}
    
    match_percentage = (sum(len(matched_skills.get(context, {}).get('skills', [])) * context_weights.get(context, 1.0)
                        for context in job_skills.keys()) / total_skills) * 100
    
    return match_percentage, matched_skills, missing_skills

def generate_personalized_suggestions(job_requirements, resume_skills, resume_text):
    """Generate personalized suggestions based on job requirements and resume content."""
    suggestions = []
    
    # Extract skills from job description
    job_skills, _ = extract_skills_from_text(job_requirements['context'].get('description', ''))
    
    # Process each context
    for context, skills in job_skills.items():
        # Filter skills that are not in resume
        missing_skills = []
        for skill in skills:
            skill_found = False
            for resume_context, resume_skill_list in resume_skills.items():
                for resume_skill in resume_skill_list:
                    if (skill.lower() == resume_skill.lower() or
                        skill.lower() in resume_skill.lower() or
                        resume_skill.lower() in skill.lower()):
                        skill_found = True
                        break
                if skill_found:
                    break
            
            if not skill_found:
                missing_skills.append(skill)
        
        if missing_skills:
            # Generate personalized suggestion
            suggestion = {
                'category': f'Missing {context.title()}',
                'skills': missing_skills,
                'confidence': 1.0,
                'context': context,
                'action_items': []
            }
            
            # Add specific action items based on context and skill category
            for skill in missing_skills:
                # Find the category of the skill
                skill_category = None
                for category, skills_list in TECHNICAL_SKILLS.items():
                    if skill.lower() in [s.lower() for s in skills_list]:
                        skill_category = category
                        break
                
                if skill_category:
                    if context == 'requirements':
                        suggestion['action_items'].extend([
                            f"Highlight any relevant experience with {skill}",
                            f"Add specific examples of using {skill} in your work history",
                            f"Consider taking courses or certifications in {skill}"
                        ])
                    elif context == 'experience':
                        suggestion['action_items'].extend([
                            f"Add projects or work experience involving {skill}",
                            f"Quantify your achievements with {skill}",
                            f"Link your existing experience to {skill}"
                        ])
                    else:
                        suggestion['action_items'].extend([
                            f"Add examples of {skill} in your responsibilities",
                            f"Highlight how you've handled {skill} in past roles",
                            f"Demonstrate your ability to work with {skill}"
                        ])
            
            suggestions.append(suggestion)
    
    # Sort suggestions by confidence
    suggestions.sort(key=lambda x: x['confidence'], reverse=True)
    
    return suggestions

def migrate_applications_table():
    conn = get_conn()
    c = conn.cursor()
    # Add columns if they do not exist
    try:
        c.execute("ALTER TABLE applications ADD COLUMN company TEXT")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE applications ADD COLUMN location TEXT")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE applications ADD COLUMN referral TEXT")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE applications ADD COLUMN job_link TEXT")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE applications ADD COLUMN referral_mail TEXT")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE applications ADD COLUMN title TEXT")
    except Exception:
        pass
    conn.commit()
    conn.close()

@app.route('/api/migrate-applications', methods=['POST'])
def migrate_applications():
    migrate_applications_table()
    return jsonify({'status': 'success', 'message': 'Applications table migrated.'})

@app.route('/api/upload_applications_excel', methods=['POST'])
def upload_applications_excel():
    clear_applications_if_large()
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected'}), 400
    if not allowed_excel_file(file.filename):
        return jsonify({'status': 'error', 'message': 'Invalid file type'}), 400
    try:
        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(temp_path)
        # Read with pandas
        if filename.endswith('.csv'):
            df = pd.read_csv(temp_path)
        else:
            df = pd.read_excel(temp_path)
        # Clean up temp file
        os.remove(temp_path)
        # Map columns
        col_map = {
            'Company': 'company',
            'Location': 'location',
            'Referral': 'referral',
            'Link': 'job_link',
            'Status': 'status',
            'Referral mail': 'referral_mail',
        }
        df = df.rename(columns=col_map)
        # Upsert each row
        conn = get_conn()
        c = conn.cursor()
        for _, row in df.iterrows():
            company = str(row.get('company', '')).strip()
            location = str(row.get('location', '')).strip()
            referral = str(row.get('referral', '')).strip()
            job_link = str(row.get('job_link', '')).strip()
            status = str(row.get('status', '')).strip()
            referral_mail = str(row.get('referral_mail', '')).strip()
            if job_link:
                # First try to update existing record
                c.execute('''UPDATE applications 
                           SET company=?, location=?, referral=?, status=?, referral_mail=?
                           WHERE job_link=?''',
                        (company, location, referral, status, referral_mail, job_link))
                # If no record was updated, insert new one
                if c.rowcount == 0:
                    c.execute('''INSERT INTO applications 
                               (company, location, referral, job_link, status, referral_mail)
                               VALUES (?, ?, ?, ?, ?, ?)''',
                            (company, location, referral, job_link, status, referral_mail))
            else:
                # If no job_link, just insert as new record
                c.execute('''INSERT INTO applications 
                           (company, location, referral, status, referral_mail)
                           VALUES (?, ?, ?, ?, ?)''',
                        (company, location, referral, status, referral_mail))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Applications uploaded and updated.'})
    except Exception as e:
        print(f"Error uploading applications Excel: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Add this utility function near the top, after get_conn()
def clear_applications_if_large(threshold=200):
    conn = get_conn()
    count = conn.execute('SELECT COUNT(*) FROM applications').fetchone()[0]
    if count > threshold:
        print(f"Clearing applications table (had {count} rows)")
        conn.execute('DELETE FROM applications')
        conn.commit()
    conn.close()

# Call this at app startup
clear_applications_if_large()

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'init-db':
        init_db()
        print('Database initialized successfully!')
    else:
        # Download required NLTK data
        nltk.download('stopwords')
        nltk.download('punkt')
        nltk.download('averaged_perceptron_tagger')
        nltk.download('wordnet')
        # Load spaCy model
        try:
            nlp = spacy.load('en_core_web_sm')
        except OSError:
            print("Downloading spaCy model...")
            spacy.cli.download('en_core_web_sm')
            nlp = spacy.load('en_core_web_sm')
        # Create uploads directory if it doesn't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        # Run the app
        app.run(host=app.config['HOST'], port=app.config['PORT'], debug=True)