# app.py
# Flask-based Job Application Tracker with Search, Tracker, and Details pages

import os
import time
from flask import Flask, render_template_string, request, redirect, url_for, send_from_directory, jsonify
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
            'User-Agent': get_random_user_agent(),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        search_url = f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(keyword)}&location={quote_plus(location)}"
        print(f"Fetching LinkedIn jobs from: {search_url}")
        response = requests.get(search_url, headers=headers, timeout=10)
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
                    'description': 'Click "Details" to view full description',
                    'requirements': [],
                    'match_score': 'N/A',
                    'salary_min': '',
                    'salary_max': '',
                    'salary_currency': '',
                    'benefits': []
                }
                
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
        print(f"Fetching Indeed jobs from: {search_url}")
        response = requests.get(search_url, headers=headers, timeout=10)
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
                    'description': 'Click "Details" to view full description',
                    'requirements': [],
                    'match_score': 'N/A',
                    'salary_min': '',
                    'salary_max': '',
                    'salary_currency': '',
                    'benefits': []
                }
                
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
        print(f"Fetching ZipRecruiter jobs from: {search_url}")
        response = requests.get(search_url, headers=headers, timeout=10)
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
                    'description': 'Click "Details" to view full description',
                    'requirements': [],
                    'match_score': 'N/A',
                    'salary_min': '',
                    'salary_max': '',
                    'salary_currency': '',
                    'benefits': []
                }
                
                jobs.append(job)
            except Exception as e:
                print(f"Error parsing ZipRecruiter job card: {str(e)}")
                continue
                
        return jobs
    except Exception as e:
        print(f"Error fetching ZipRecruiter jobs: {str(e)}")
        return []

@rate_limit
def fetch_linkedin_job_details(url):
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
        
        print(f"\nFetching LinkedIn job details from: {url}")
        session = requests.Session()
        
        # First make a GET request to the main page
        try:
            response = session.get('https://www.linkedin.com', headers=headers, timeout=10)
            response.raise_for_status()
            time.sleep(random.uniform(2, 4))  # Wait before the next request
        except Exception as e:
            print(f"Warning: Could not access LinkedIn main page: {str(e)}")
        
        # Now fetch the job details
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        print(f"Response status code: {response.status_code}")
        print(f"Response content type: {response.headers.get('content-type', 'unknown')}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Debug: Print the first 500 characters of the response
        print("\nFirst 500 characters of response:")
        print(response.text[:500])
        
        # Try to find the job description
        description = None
        description_text = ""
        
        # Try multiple approaches to find the description
        selectors = [
            'div.description__text',
            'div.job-description',
            'div.show-more-less-html__markup',
            '#job-details',
            'div.job-view-layout',
            'div.job-description-container',
            'div.job-description__content'
        ]
        
        for selector in selectors:
            print(f"\nTrying selector: {selector}")
            description = soup.select_one(selector)
            if description:
                print(f"Found description with selector: {selector}")
                break
        
        if description:
            # Remove unwanted elements
            for element in description.find_all(['script', 'style', 'button', 'a', 'div.job-description__footer']):
                element.decompose()
            
            # Get the text content
            description_text = description.get_text(separator='\n', strip=True)
            
            # Clean up the text
            lines = [line.strip() for line in description_text.split('\n') if line.strip()]
            description_text = '\n'.join(lines)
            
            # Remove common unwanted text
            unwanted = ['See more', 'See less', 'Show more', 'Show less', 'Apply now', 'Apply for this job']
            for text in unwanted:
                description_text = description_text.replace(text, '')
            
            print(f"\nFound description with length: {len(description_text)}")
            print("First 200 characters of description:")
            print(description_text[:200])
        else:
            print("\nNo description found with any selector")
            # Try to find any text content that might be a description
            main_content = soup.find('main') or soup.find('div', {'role': 'main'})
            if main_content:
                print("\nTrying to extract description from main content")
                description_text = main_content.get_text(separator='\n', strip=True)
                lines = [line.strip() for line in description_text.split('\n') if line.strip()]
                description_text = '\n'.join(lines)
                print(f"Extracted text with length: {len(description_text)}")
        
        # Try to find requirements
        requirements = []
        
        # Try multiple approaches to find requirements
        req_selectors = [
            'div.description__job-criteria',
            'div.job-criteria',
            'div.job-requirements',
            'ul.job-requirements-list',
            'div.job-requirements-container',
            'div.job-criteria-container'
        ]
        
        for selector in req_selectors:
            print(f"\nTrying requirements selector: {selector}")
            req_section = soup.select_one(selector)
            if req_section:
                req_items = req_section.find_all('li')
                requirements = [item.get_text(strip=True) for item in req_items if item.get_text(strip=True)]
                if requirements:
                    print(f"Found {len(requirements)} requirements with selector: {selector}")
                    break
        
        # If no requirements found, try to extract from description
        if not requirements and description:
            print("\nTrying to extract requirements from description")
            # Look for bullet points
            bullets = description.find_all(['ul', 'ol'])
            for bullet_list in bullets:
                items = bullet_list.find_all('li')
                requirements.extend([item.get_text(strip=True) for item in items if item.get_text(strip=True)])
            if requirements:
                print(f"Found {len(requirements)} requirements from description bullets")
        
        print(f"\nTotal requirements found: {len(requirements)}")
        
        return {
            'description': description_text,
            'requirements': requirements,
            'benefits': [],
            'salary_range': ''
        }
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print("\nRate limited by LinkedIn. Waiting longer before next request...")
            time.sleep(random.uniform(30, 60))  # Wait 30-60 seconds before next request
        print(f"\nError fetching LinkedIn job details: {str(e)}")
        return {
            'description': '',
            'requirements': [],
            'benefits': [],
            'salary_range': ''
        }
    except Exception as e:
        print(f"\nError fetching LinkedIn job details: {str(e)}")
        return {
            'description': '',
            'requirements': [],
            'benefits': [],
            'salary_range': ''
        }

@rate_limit
def fetch_indeed_job_details(url):
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
        
        print(f"\nFetching Indeed job details from: {url}")
        session = requests.Session()
        
        # First make a GET request to the main page
        try:
            response = session.get('https://www.indeed.com', headers=headers, timeout=10)
            response.raise_for_status()
            time.sleep(random.uniform(2, 4))  # Wait before the next request
        except Exception as e:
            print(f"Warning: Could not access Indeed main page: {str(e)}")
        
        # Now fetch the job details
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        print(f"Response status code: {response.status_code}")
        print(f"Response content type: {response.headers.get('content-type', 'unknown')}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Debug: Print the first 500 characters of the response
        print("\nFirst 500 characters of response:")
        print(response.text[:500])
        
        # Try to find the job description
        description = None
        description_text = ""
        
        # Try multiple approaches to find the description
        selectors = [
            '#jobDescriptionText',
            '.jobsearch-jobDescriptionText',
            '.job-description',
            '#jobDescription',
            '.jobsearch-jobDescription',
            '.jobsearch-jobDescriptionText',
            'div[data-testid="jobDescriptionText"]'
        ]
        
        for selector in selectors:
            print(f"\nTrying selector: {selector}")
            description = soup.select_one(selector)
            if description:
                print(f"Found description with selector: {selector}")
                break
        
        if description:
            # Remove unwanted elements
            for element in description.find_all(['script', 'style', 'button', 'a']):
                element.decompose()
            
            # Get the text content
            description_text = description.get_text(separator='\n', strip=True)
            
            # Clean up the text
            lines = [line.strip() for line in description_text.split('\n') if line.strip()]
            description_text = '\n'.join(lines)
            
            # Remove common unwanted text
            unwanted = ['See more', 'See less', 'Show more', 'Show less', 'Apply now', 'Apply for this job']
            for text in unwanted:
                description_text = description_text.replace(text, '')
            
            print(f"\nFound description with length: {len(description_text)}")
            print("First 200 characters of description:")
            print(description_text[:200])
        else:
            print("\nNo description found with any selector")
            # Try to find any text content that might be a description
            main_content = soup.find('main') or soup.find('div', {'role': 'main'})
            if main_content:
                print("\nTrying to extract description from main content")
                description_text = main_content.get_text(separator='\n', strip=True)
                lines = [line.strip() for line in description_text.split('\n') if line.strip()]
                description_text = '\n'.join(lines)
                print(f"Extracted text with length: {len(description_text)}")
        
        # Try to find requirements
        requirements = []
        
        # Try multiple approaches to find requirements
        req_selectors = [
            '.jobsearch-ReqAndQualSection',
            '.job-requirements',
            '.job-requirements-list',
            '.jobsearch-jobDescriptionText ul li',
            '.jobsearch-jobDescriptionText ol li',
            'div[data-testid="jobDescriptionText"] ul li'
        ]
        
        for selector in req_selectors:
            print(f"\nTrying requirements selector: {selector}")
            req_items = soup.select(selector)
            if req_items:
                requirements = [item.get_text(strip=True) for item in req_items if item.get_text(strip=True)]
                if requirements:
                    print(f"Found {len(requirements)} requirements with selector: {selector}")
                    break
        
        # If no requirements found, try to extract from description
        if not requirements and description:
            print("\nTrying to extract requirements from description")
            # Look for bullet points
            bullets = description.find_all(['ul', 'ol'])
            for bullet_list in bullets:
                items = bullet_list.find_all('li')
                requirements.extend([item.get_text(strip=True) for item in items if item.get_text(strip=True)])
            if requirements:
                print(f"Found {len(requirements)} requirements from description bullets")
        
        print(f"\nTotal requirements found: {len(requirements)}")
        
        return {
            'description': description_text,
            'requirements': requirements,
            'benefits': [],
            'salary_range': ''
        }
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print("\nRate limited by Indeed. Waiting longer before next request...")
            time.sleep(random.uniform(30, 60))  # Wait 30-60 seconds before next request
        print(f"\nError fetching Indeed job details: {str(e)}")
        return {
            'description': '',
            'requirements': [],
            'benefits': [],
            'salary_range': ''
        }
    except Exception as e:
        print(f"\nError fetching Indeed job details: {str(e)}")
        return {
            'description': '',
            'requirements': [],
            'benefits': [],
            'salary_range': ''
        }

@rate_limit
def fetch_ziprecruiter_job_details(url):
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
        
        print(f"\nFetching ZipRecruiter job details from: {url}")
        session = requests.Session()
        
        # First make a GET request to the main page
        try:
            response = session.get('https://www.ziprecruiter.com', headers=headers, timeout=10)
            response.raise_for_status()
            time.sleep(random.uniform(2, 4))  # Wait before the next request
        except Exception as e:
            print(f"Warning: Could not access ZipRecruiter main page: {str(e)}")
        
        # Now fetch the job details
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        print(f"Response status code: {response.status_code}")
        print(f"Response content type: {response.headers.get('content-type', 'unknown')}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Debug: Print the first 500 characters of the response
        print("\nFirst 500 characters of response:")
        print(response.text[:500])
        
        # Try to find the job description
        description = None
        description_text = ""
        
        # Try multiple approaches to find the description
        selectors = [
            '.job_description',
            '.job-description',
            '.job-details',
            '#job-description',
            '.job-description-content',
            '.job-description-text',
            'div[data-testid="jobDescription"]'
        ]
        
        for selector in selectors:
            print(f"\nTrying selector: {selector}")
            description = soup.select_one(selector)
            if description:
                print(f"Found description with selector: {selector}")
                break
        
        if description:
            # Remove unwanted elements
            for element in description.find_all(['script', 'style', 'button', 'a']):
                element.decompose()
            
            # Get the text content
            description_text = description.get_text(separator='\n', strip=True)
            
            # Clean up the text
            lines = [line.strip() for line in description_text.split('\n') if line.strip()]
            description_text = '\n'.join(lines)
            
            # Remove common unwanted text
            unwanted = ['See more', 'See less', 'Show more', 'Show less', 'Apply now', 'Apply for this job']
            for text in unwanted:
                description_text = description_text.replace(text, '')
            
            print(f"\nFound description with length: {len(description_text)}")
            print("First 200 characters of description:")
            print(description_text[:200])
        else:
            print("\nNo description found with any selector")
            # Try to find any text content that might be a description
            main_content = soup.find('main') or soup.find('div', {'role': 'main'})
            if main_content:
                print("\nTrying to extract description from main content")
                description_text = main_content.get_text(separator='\n', strip=True)
                lines = [line.strip() for line in description_text.split('\n') if line.strip()]
                description_text = '\n'.join(lines)
                print(f"Extracted text with length: {len(description_text)}")
        
        # Try to find requirements
        requirements = []
        
        # Try multiple approaches to find requirements
        req_selectors = [
            '.job_requirements li',
            '.job-requirements li',
            '.requirements-list li',
            '.job-description ul li',
            '.job-description ol li',
            'div[data-testid="jobDescription"] ul li'
        ]
        
        for selector in req_selectors:
            print(f"\nTrying requirements selector: {selector}")
            req_items = soup.select(selector)
            if req_items:
                requirements = [item.get_text(strip=True) for item in req_items if item.get_text(strip=True)]
                if requirements:
                    print(f"Found {len(requirements)} requirements with selector: {selector}")
                    break
        
        # If no requirements found, try to extract from description
        if not requirements and description:
            print("\nTrying to extract requirements from description")
            # Look for bullet points
            bullets = description.find_all(['ul', 'ol'])
            for bullet_list in bullets:
                items = bullet_list.find_all('li')
                requirements.extend([item.get_text(strip=True) for item in items if item.get_text(strip=True)])
            if requirements:
                print(f"Found {len(requirements)} requirements from description bullets")
        
        print(f"\nTotal requirements found: {len(requirements)}")
        
        return {
            'description': description_text,
            'requirements': requirements,
            'benefits': [],
            'salary_range': ''
        }
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print("\nRate limited by ZipRecruiter. Waiting longer before next request...")
            time.sleep(random.uniform(30, 60))  # Wait 30-60 seconds before next request
        print(f"\nError fetching ZipRecruiter job details: {str(e)}")
        return {
            'description': '',
            'requirements': [],
            'benefits': [],
            'salary_range': ''
        }
    except Exception as e:
        print(f"\nError fetching ZipRecruiter job details: {str(e)}")
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
    c.execute("""
CREATE TABLE IF NOT EXISTS saved_jobs (
    id INTEGER PRIMARY KEY,
    job_id INTEGER,
    saved_at TIMESTAMP,
    FOREIGN KEY(job_id) REFERENCES jobs(id)
)
""")
    get_conn().commit()

init_db()

# ALLOWED FILE
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Application Tracker</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
</head>
<body>
<div class="d-flex">
  <!-- Sidebar -->
  <div class="sidebar bg-dark text-white">
    <div class="sidebar-header p-3">
      <h4 class="mb-0 text-white">JobApp</h4>
      <p class="text-muted small mb-0">Track your job search</p>
    </div>
    <ul class="nav flex-column">
      <li class="nav-item">
        <a class="nav-link {% if request.endpoint == 'search' %}active{% endif %}" href="/search">
          <i class="bi bi-search"></i>
          <span>Search Jobs</span>
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link {% if request.endpoint == 'tracker' %}active{% endif %}" href="/tracker">
          <i class="bi bi-list-check"></i>
          <span>Application Tracker</span>
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link {% if request.endpoint == 'saved_jobs' %}active{% endif %}" href="/saved_jobs">
          <i class="bi bi-bookmark"></i>
          <span>Saved Jobs</span>
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link {% if request.endpoint == 'details' %}active{% endif %}" href="/details">
          <i class="bi bi-file-earmark-text"></i>
          <span>Resume Details</span>
        </a>
      </li>
    </ul>
    <div class="sidebar-footer p-3">
      <div class="d-flex align-items-center">
        <i class="bi bi-gear me-2"></i>
        <span>Settings</span>
      </div>
    </div>
  </div>

  <!-- Main Content -->
  <div class="main-content">
"""
FOOTER = """
  </div>
</div>

<style>
  /* Sidebar Styles */
  .sidebar {
    width: 250px;
    min-height: 100vh;
    position: fixed;
    top: 0;
    left: 0;
    z-index: 1000;
    transition: all 0.3s;
  }

  .sidebar-header {
    border-bottom: 1px solid rgba(255,255,255,0.1);
  }

  .sidebar .nav-link {
    color: rgba(255,255,255,0.8);
    padding: 0.8rem 1rem;
    display: flex;
    align-items: center;
    transition: all 0.3s;
  }

  .sidebar .nav-link:hover {
    color: #fff;
    background: rgba(255,255,255,0.1);
  }

  .sidebar .nav-link.active {
    color: #fff;
    background: rgba(255,255,255,0.1);
    border-left: 4px solid #0d6efd;
  }

  .sidebar .nav-link i {
    margin-right: 10px;
    font-size: 1.1rem;
  }

  .sidebar-footer {
    position: absolute;
    bottom: 0;
    width: 100%;
    border-top: 1px solid rgba(255,255,255,0.1);
  }

  /* Main Content Styles */
  .main-content {
    margin-left: 250px;
    padding: 20px;
    min-height: 100vh;
    background-color: #f8f9fa;
  }

  /* Responsive Design */
  @media (max-width: 768px) {
    .sidebar {
      width: 70px;
    }
    
    .sidebar .nav-link span {
      display: none;
    }
    
    .sidebar-header h4, .sidebar-header p {
      display: none;
    }
    
    .main-content {
      margin-left: 70px;
    }
    
    .sidebar-footer span {
      display: none;
    }
  }

  /* Additional Styles */
  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  }

  .card {
    border: none;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  }

  .btn {
    font-weight: 500;
  }

  .form-control, .form-select {
    border-radius: 8px;
  }

  .badge {
    font-weight: 500;
  }
</style>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# TEMPLATES
SEARCH_HTML = NAVBAR + '''
<div class="container-fluid py-4">
  <div class="row mb-4">
    <div class="col-12">
      <h2 class="display-5 mb-4 text-primary">Job Search</h2>
      <div class="card shadow-sm">
        <div class="card-body">
          <form method="post" class="row g-3">
            <div class="col-md-5">
              <div class="input-group">
                <span class="input-group-text bg-primary text-white">
                  <i class="bi bi-search"></i>
                </span>
                <input name="keyword" placeholder="Role (e.g., Software Engineer, Product Manager)" 
                       value="{{keyword}}" class="form-control form-control-lg"/>
              </div>
            </div>
            <div class="col-md-3">
              <select name="location" class="form-select form-select-lg">
                <option value="">All Locations</option>
                {% for loc in locations %}
                  <option value="{{loc}}" {% if loc==location %}selected{% endif %}>{{loc}}</option>
                {% endfor %}
              </select>
            </div>
            <div class="col-md-3">
              <select name="platform" class="form-select form-select-lg">
                <option value="">All Platforms</option>
                {% for plat in platforms %}
                  <option value="{{plat}}" {% if plat==platform %}selected{% endif %}>{{plat}}</option>
                {% endfor %}
              </select>
            </div>
            <div class="col-md-1">
              <button class="btn btn-primary btn-lg w-100">
                <i class="bi bi-search"></i>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>

  <div class="row mb-4">
    <div class="col-12">
      <div class="card shadow-sm">
        <div class="card-body">
          <form method="get" class="row g-3">
            <div class="col-md-4">
              <select name="filter_loc" class="form-select">
                <option value="">Filter by Location</option>
                {% for loc in locations %}
                  <option value="{{loc}}" {% if loc==filter_loc %}selected{% endif %}>{{loc}}</option>
                {% endfor %}
              </select>
            </div>
            <div class="col-md-4">
              <select name="filter_platform" class="form-select">
                <option value="">Filter by Platform</option>
                {% for plat in platforms %}
                  <option value="{{plat}}" {% if plat==filter_platform %}selected{% endif %}>{{plat}}</option>
                {% endfor %}
              </select>
            </div>
            <div class="col-md-3">
              <select name="sort_by" class="form-select">
                <option value="recent" {% if sort_by=='recent' %}selected{% endif %}>Recently Posted</option>
                <option value="oldest" {% if sort_by=='oldest' %}selected{% endif %}>Oldest First</option>
                <option value="a_to_z" {% if sort_by=='a_to_z' %}selected{% endif %}>Title (A to Z)</option>
                <option value="z_to_a" {% if sort_by=='z_to_a' %}selected{% endif %}>Title (Z to A)</option>
                <option value="company_a_to_z" {% if sort_by=='company_a_to_z' %}selected{% endif %}>Company (A to Z)</option>
                <option value="company_z_to_a" {% if sort_by=='company_z_to_a' %}selected{% endif %}>Company (Z to A)</option>
              </select>
            </div>
            <div class="col-md-3">
              <select name="application_status" class="form-select">
                <option value="">All Applications</option>
                <option value="applied" {% if application_status=='applied' %}selected{% endif %}>Applied</option>
                <option value="not_applied" {% if application_status=='not_applied' %}selected{% endif %}>Not Applied</option>
              </select>
            </div>
            <div class="col-md-1">
              <button class="btn btn-primary btn-lg w-100">
                <i class="bi bi-search"></i>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>

  <!-- Top Pagination -->
  <div class="row mb-4">
    <div class="col-12">
      <nav aria-label="Page navigation">
        <ul class="pagination justify-content-center">
          <li class="page-item {% if page == 1 %}disabled{% endif %}">
            <a class="page-link" href="{{ url_for('search', page=page-1, filter_loc=filter_loc, filter_platform=filter_platform, sort_by=sort_by, application_status=application_status) if page > 1 else '#' }}" aria-label="Previous">
              <span aria-hidden="true">&laquo;</span>
            </a>
          </li>
          {% for p in range(max(1, page-2), min(pages+1, page+3)) %}
            <li class="page-item {% if p == page %}active{% endif %}">
              <a class="page-link" href="{{ url_for('search', page=p, filter_loc=filter_loc, filter_platform=filter_platform, sort_by=sort_by, application_status=application_status) }}">{{ p }}</a>
            </li>
          {% endfor %}
          <li class="page-item {% if page == pages %}disabled{% endif %}">
            <a class="page-link" href="{{ url_for('search', page=page+1, filter_loc=filter_loc, filter_platform=filter_platform, sort_by=sort_by, application_status=application_status) if page < pages else '#' }}" aria-label="Next">
              <span aria-hidden="true">&raquo;</span>
            </a>
          </li>
        </ul>
      </nav>
    </div>
  </div>

  <div class="row">
    <div class="col-12">
      <div class="job-list">
        {% for job in rows %}
          <div class="card mb-3">
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-start mb-2">
                <h5 class="card-title mb-0">
                  <a href="{{ job['url'] }}" target="_blank" class="text-decoration-none">
                    {{ job['title'] }}
                    {% if job.get('application_status') == 'Applied' %}
                    <i class="bi bi-check-circle-fill text-success ms-2" title="Applied"></i>
                    {% endif %}
                  </a>
                </h5>
                <div class="d-flex gap-2">
                  <button class="btn btn-sm btn-outline-primary view-details" data-job-id="{{ job['id'] }}">
                    <i class="bi bi-eye"></i> Details
                  </button>
                  <button class="btn btn-sm btn-outline-success save-job" data-job-id="{{ job['id'] }}" type="button">
                    <i class="bi bi-bookmark"></i> Save
                  </button>
                  {% if job.get('application_status') == 'Applied' %}
                  <button class="btn btn-sm btn-outline-danger didnt-apply" data-job-id="{{ job['id'] }}" type="button">
                    <i class="bi bi-x-circle"></i> Didn't Apply
                  </button>
                  {% else %}
                  <button class="btn btn-sm btn-outline-primary apply-job" data-job-id="{{ job['id'] }}" type="button">
                    <i class="bi bi-send"></i> Apply
                  </button>
                  {% endif %}
                </div>
              </div>
              <h6 class="card-subtitle mb-2 text-muted">{{ job['company'] }}</h6>
              <p class="card-text description-content">{{ job['description'] }}</p>
              
              <!-- AI Job Match Analysis Section - Initially Hidden -->
              <div class="match-analysis mt-4" style="display: none;">
                <h6 class="mb-3">AI Job Match Analysis</h6>
                
                <!-- Match Score -->
                <div class="match-score mb-3">
                  <div class="d-flex align-items-center">
                    <div class="match-percentage me-2">0%</div>
                    <div class="progress flex-grow-1" style="height: 8px;">
                      <div class="progress-bar"
                           role="progressbar"
                           style="width: 0%"
                           aria-valuenow="0"
                           aria-valuemin="0"
                           aria-valuemax="100"></div>
                    </div>
                  </div>
                </div>

                <!-- Matched Skills -->
                <div class="matched-skills mb-3">
                  <h6 class="mb-2">Matched Skills</h6>
                  <div class="skills-container"></div>
                </div>

                <!-- Suggestions -->
                <div class="suggestions">
                  <h6 class="mb-2">Improvement Suggestions</h6>
                  <div class="suggestions-container"></div>
                </div>
              </div>
            </div>
          </div>
        {% endfor %}
      </div>
    </div>
  </div>

  <!-- Bottom Pagination -->
  <div class="row mt-4">
    <div class="col-12">
      <nav aria-label="Page navigation">
        <ul class="pagination justify-content-center">
          <li class="page-item {% if page == 1 %}disabled{% endif %}">
            <a class="page-link" href="{{ url_for('search', page=page-1, filter_loc=filter_loc, filter_platform=filter_platform, sort_by=sort_by, application_status=application_status) if page > 1 else '#' }}" aria-label="Previous">
              <span aria-hidden="true">&laquo;</span>
            </a>
          </li>
          {% for p in range(max(1, page-2), min(pages+1, page+3)) %}
            <li class="page-item {% if p == page %}active{% endif %}">
              <a class="page-link" href="{{ url_for('search', page=p, filter_loc=filter_loc, filter_platform=filter_platform, sort_by=sort_by, application_status=application_status) }}">{{ p }}</a>
            </li>
          {% endfor %}
          <li class="page-item {% if page == pages %}disabled{% endif %}">
            <a class="page-link" href="{{ url_for('search', page=page+1, filter_loc=filter_loc, filter_platform=filter_platform, sort_by=sort_by, application_status=application_status) if page < pages else '#' }}" aria-label="Next">
              <span aria-hidden="true">&raquo;</span>
            </a>
          </li>
        </ul>
      </nav>
    </div>
  </div>
</div>

<!-- Loading Modal -->
<div class="modal fade" id="loadingModal" tabindex="-1" aria-hidden="true" data-bs-backdrop="static">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content">
      <div class="modal-body text-center p-4">
        <div class="spinner-border text-primary mb-3" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        <h5 class="mb-0">Loading job details...</h5>
      </div>
    </div>
  </div>
</div>

<style>
  .job-list {
    max-width: 100%;
    margin: 0 auto;
  }
  
  .job-description {
    max-height: 200px;
    overflow-y: auto;
    padding: 15px;
    background-color: #f8f9fa;
    border-radius: 8px;
    border: 1px solid #e9ecef;
  }
  
  .description-content {
    white-space: pre-wrap;
    word-wrap: break-word;
    font-size: 0.95rem;
    line-height: 1.5;
  }
  
  .hover-card {
    transition: all 0.3s ease;
  }
  
  .hover-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 16px rgba(0,0,0,0.1) !important;
  }

  /* Ensure proper scrolling */
  .main-content {
    overflow-x: hidden;
  }

  .card {
    width: 100%;
    margin-bottom: 1rem;
  }

  /* Pagination styles */
  .pagination {
    margin-bottom: 0;
  }

  .page-link {
    color: #0d6efd;
    border: 1px solid #dee2e6;
    padding: 0.5rem 1rem;
  }

  .page-item.active .page-link {
    background-color: #0d6efd;
    border-color: #0d6efd;
  }

  .page-item.disabled .page-link {
    color: #6c757d;
    pointer-events: none;
    background-color: #fff;
    border-color: #dee2e6;
  }

  /* Improve responsive behavior */
  @media (max-width: 768px) {
    .card-body {
      padding: 1rem;
    }
    
    .job-description {
      max-height: 150px;
    }

    .pagination {
      flex-wrap: wrap;
    }

    .page-link {
      padding: 0.375rem 0.75rem;
    }
  }

  .match-analysis {
    background-color: #f8f9fa;
    border-radius: 8px;
    padding: 1rem;
    margin-top: 1rem;
  }

  .match-score {
    margin-bottom: 1.5rem;
  }

  .match-percentage {
    font-size: 1.5rem;
    font-weight: bold;
    min-width: 60px;
  }

  .progress {
    background-color: #e9ecef;
    border-radius: 4px;
    overflow: hidden;
  }
  
  .suggestion-card {
    background-color: white;
    border-radius: 8px;
    border: 1px solid #e9ecef;
    overflow: hidden;
    margin-bottom: 1rem;
  }
  
  .suggestion-header {
    background-color: #e7f5ff;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #e9ecef;
    color: #0a58ca;
  }
  
  .suggestion-body {
    padding: 1rem;
  }
  
  .action-items ul {
    list-style-type: none;
    padding-left: 0;
    margin-bottom: 0;
  }
  
  .action-items li {
    position: relative;
    padding-left: 1.5rem;
    margin-bottom: 0.5rem;
  }
  
  .action-items li:before {
    content: "→";
    position: absolute;
    left: 0;
    color: #0dcaf0;
  }
  
  .action-items li:last-child {
    margin-bottom: 0;
  }
  
  .matched-skills .badge {
    font-size: 0.85rem;
    padding: 0.35em 0.65em;
  }
</style>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
''' + FOOTER

TRACKER_HTML = NAVBAR + '''
<div class="container-fluid py-4">
  <div class="row mb-4">
    <div class="col-12">
      <h2 class="display-5 mb-4 text-primary">Application Tracker</h2>
      <div class="card shadow-sm">
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-hover">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Title</th>
                  <th>Status</th>
                  <th>Date Applied</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
              {% for app in apps %}
                <tr>
                  <td>{{app['job_id']}}</td>
                  <td>{{app['title']}}</td>
                  <td>
                    <span class="badge {% if app['status'] == 'Applied' %}bg-primary{% elif app['status'] == 'Rejected' %}bg-danger{% else %}bg-warning{% endif %}">
                      {{app['status']}}
                    </span>
                  </td>
                  <td>{{app['applied_at']}}</td>
                  <td>
                    <form method="post" action="/update_status/{{app['id']}}" class="d-flex gap-2">
                      <select name="status" class="form-select form-select-sm">
                        {% for s in ['Applied','Rejected','No response'] %}
                          <option value="{{s}}" {% if s==app['status'] %}selected{% endif %}>{{s}}</option>
                        {% endfor %}
                      </select>
                      <input type="date" name="applied_at" value="{{app['applied_at']}}" class="form-control form-control-sm"/>
                      <button class="btn btn-sm btn-primary">
                        <i class="bi bi-save"></i>
                      </button>
                    </form>
                  </td>
                </tr>
              {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
''' + FOOTER

DETAILS_HTML = NAVBAR + '''
<div class="container-fluid py-4">
  <div class="row mb-4">
    <div class="col-12">
      <h2 class="display-5 mb-4 text-primary">Resume Details</h2>
      <div class="card shadow-sm">
        <div class="card-body">
          {% if resume %}
            <div class="alert alert-info d-flex justify-content-between align-items-center">
              <div>
                <i class="bi bi-file-earmark-text me-2"></i>
                Current Resume: <a href="/uploads/{{resume['filename']}}" class="alert-link" target="_blank">{{resume['filename']}}</a>
                <small class="text-muted">(Uploaded: {{resume['uploaded_at']}})</small>
              </div>
              <form method="post" action="/delete_resume" class="d-inline" onsubmit="return confirm('Are you sure you want to delete this resume?');">
                <button type="submit" class="btn btn-outline-danger btn-sm">
                  <i class="bi bi-trash"></i> Delete
                </button>
              </form>
            </div>
          {% else %}
            <div class="alert alert-warning">
              <i class="bi bi-exclamation-triangle me-2"></i>
              No resume uploaded yet. Please upload your resume to track your applications.
            </div>
          {% endif %}

          <form method="post" enctype="multipart/form-data" class="mt-4">
            <div class="row g-3">
              <div class="col-md-8">
                <div class="input-group">
                  <input type="file" name="file" class="form-control" accept=".pdf,.doc,.docx,.txt" required/>
                  <button type="submit" class="btn btn-primary">
                    <i class="bi bi-upload me-2"></i>Upload Resume
                  </button>
                </div>
                <small class="text-muted d-block mt-2">
                  Supported formats: PDF, DOC, DOCX, TXT (Max size: 5MB)
                </small>
              </div>
            </div>
          </form>

          {% if error %}
            <div class="alert alert-danger mt-3">
              <i class="bi bi-exclamation-circle me-2"></i>
              {{ error }}
            </div>
          {% endif %}
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  .alert {
    border-radius: 8px;
  }
  
  .alert-link {
    text-decoration: none;
  }
  
  .alert-link:hover {
    text-decoration: underline;
  }
  
  .input-group {
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  }
  
  .form-control:focus {
    box-shadow: none;
    border-color: #0d6efd;
  }
</style>
''' + FOOTER

# ROUTES
@app.route('/')
def home(): return redirect(url_for('search'))

@app.route('/search', methods=['GET','POST'])
def search():
    conn = get_conn()
    try:
        keyword = request.form.get('keyword','') if request.method=='POST' else ''
        location = request.form.get('location','') if request.method=='POST' else ''
        platform = request.form.get('platform','') if request.method=='POST' else ''
        
        if request.method=='POST':
            lst = fetch_all_jobs(keyword, location)
            save_listings(lst)
        
        rows = conn.execute('SELECT * FROM jobs ORDER BY fetched_at DESC').fetchall()
        resume = conn.execute('SELECT * FROM resume ORDER BY uploaded_at DESC LIMIT 1').fetchone()
        
        # Get application statuses for all jobs
        application_statuses = conn.execute('''
            SELECT job_id, status 
            FROM applications 
            WHERE job_id IN (SELECT id FROM jobs)
        ''').fetchall()
        
        # Create a dictionary of job_id to application status
        job_statuses = {row['job_id']: row['status'] for row in application_statuses}
        
        # Get unique locations and platforms for dropdowns
        locations = sorted(set(get_location_options() + [row['location'] for row in rows]))
        platforms = sorted(set(row['platform'] for row in rows))
        
        # Apply filters
        filter_loc = request.args.get('filter_loc','')
        filter_platform = request.args.get('filter_platform','')
        sort_by = request.args.get('sort_by', 'recent')  # Default sort by recent
        application_status = request.args.get('application_status', '')  # New filter
        page = request.args.get('page',1,type=int)
        
        if filter_loc:
            rows = [r for r in rows if filter_loc.lower() in r['location'].lower()]
        if filter_platform:
            rows = [r for r in rows if filter_platform.lower() == r['platform'].lower()]
        
        # Apply application status filter
        if application_status == 'applied':
            rows = [r for r in rows if r['id'] in job_statuses]
        elif application_status == 'not_applied':
            rows = [r for r in rows if r['id'] not in job_statuses]
        
        # Apply sorting
        if sort_by == 'recent':
            rows = sorted(rows, key=lambda x: x['date_posted'], reverse=True)
        elif sort_by == 'oldest':
            rows = sorted(rows, key=lambda x: x['date_posted'])
        elif sort_by == 'a_to_z':
            rows = sorted(rows, key=lambda x: x['title'].lower())
        elif sort_by == 'z_to_a':
            rows = sorted(rows, key=lambda x: x['title'].lower(), reverse=True)
        elif sort_by == 'company_a_to_z':
            rows = sorted(rows, key=lambda x: x['company'].lower())
        elif sort_by == 'company_z_to_a':
            rows = sorted(rows, key=lambda x: x['company'].lower(), reverse=True)
        
        total = len(rows)
        pages = (total + PER_PAGE - 1) // PER_PAGE
        page = max(1, min(page, pages))
        rows = rows[(page-1)*PER_PAGE : page*PER_PAGE]
        
        # Convert requirements from JSON string to list and calculate match percentage
        rows = [dict(r) for r in rows]
        for row in rows:
            try:
                row['requirements'] = json.loads(row['requirements'])
            except:
                row['requirements'] = []
            
            # Add application status
            row['application_status'] = job_statuses.get(row['id'])
            
            # Initialize default values
            row['match_percentage'] = 0
            row['matched_skills'] = {}
            row['missing_skills'] = {}
            row['suggestions'] = []
            
            # Only calculate match if we have both a resume and a complete job description
            if resume and row['description'] and row['description'] != 'Click "Details" to view full description':
                resume_path = os.path.join(app.config['UPLOAD_FOLDER'], resume['filename'])
                resume_text = extract_text_from_file(resume_path)
                resume_skills, resume_entities = extract_skills_from_text(resume_text)
                
                # Extract skills from job description
                job_skills, job_entities = extract_skills_from_text(row['description'])
                
                # Calculate match percentage
                match_percentage, matched_skills, missing_skills = calculate_job_match(
                    row['description'],
                    resume_skills
                )
                
                # Generate suggestions based on both resume and job description
                suggestions = []
                
                # Add missing skills suggestions
                for category, skills in missing_skills.items():
                    if skills:
                        # Check if any of these skills are mentioned in the job description
                        relevant_skills = [skill for skill in skills if skill in row['description'].lower()]
                        if relevant_skills:
                            suggestions.append({
                                'category': category,
                                'suggestion': f"The job requires {', '.join(relevant_skills)} which are not found in your resume. Consider adding these skills.",
                                'action_items': [
                                    f"Add {skill} to your skills section" for skill in relevant_skills
                                ]
                            })
                
                # Add experience suggestions based on job requirements
                experience_patterns = [
                    r'(\d+)[\+]?\s*(?:years?|yrs?)\s*(?:of)?\s*experience',
                    r'experience\s*(?:of)?\s*(\d+)[\+]?\s*(?:years?|yrs?)'
                ]
                
                for pattern in experience_patterns:
                    matches = re.finditer(pattern, row['description'].lower())
                    for match in matches:
                        years = match.group(1)
                        # Check if the resume mentions any experience
                        if not re.search(r'\d+\s*(?:years?|yrs?)\s*(?:of)?\s*experience', resume_text.lower()):
                            suggestions.append({
                                'category': 'Experience',
                                'suggestion': f"The job requires {years}+ years of experience. Your resume should clearly state your years of experience.",
                                'action_items': [
                                    "Add specific years of experience in your work history",
                                    "Quantify your experience with concrete examples",
                                    "Highlight relevant projects and achievements"
                                ]
                            })
                
                # Add education suggestions based on job requirements
                education_keywords = ['bachelor', 'master', 'phd', 'degree', 'diploma', 'certification']
                job_education = [keyword for keyword in education_keywords if keyword in row['description'].lower()]
                resume_education = [keyword for keyword in education_keywords if keyword in resume_text.lower()]
                
                missing_education = [edu for edu in job_education if edu not in resume_education]
                if missing_education:
                    suggestions.append({
                        'category': 'Education',
                        'suggestion': f"The job requires {', '.join(missing_education)} qualifications. Make sure your education section is complete.",
                        'action_items': [
                            "List your highest education degree first",
                            "Include relevant certifications",
                            "Highlight relevant coursework and achievements"
                        ]
                    })
                
                # Add soft skills suggestions
                soft_skills = ['communication', 'leadership', 'teamwork', 'problem-solving', 'time management', 'collaboration']
                job_soft_skills = [skill for skill in soft_skills if skill in row['description'].lower()]
                resume_soft_skills = [skill for skill in soft_skills if skill in resume_text.lower()]
                
                missing_soft_skills = [skill for skill in job_soft_skills if skill not in resume_soft_skills]
                if missing_soft_skills:
                    suggestions.append({
                        'category': 'Soft Skills',
                        'suggestion': f"The job emphasizes {', '.join(missing_soft_skills)}. Add examples of these skills in your experience.",
                        'action_items': [
                            f"Add specific examples of {skill} in your work experience" for skill in missing_soft_skills
                        ]
                    })
                
                # Add industry-specific suggestions
                industry_keywords = ['industry', 'sector', 'domain', 'field']
                if any(keyword in row['description'].lower() for keyword in industry_keywords):
                    # Check if resume mentions any industry experience
                    if not any(keyword in resume_text.lower() for keyword in industry_keywords):
                        suggestions.append({
                            'category': 'Industry Experience',
                            'suggestion': "The job requires specific industry experience. Highlight your relevant industry background.",
                            'action_items': [
                                "List relevant industry experience",
                                "Highlight industry-specific projects",
                                "Mention industry certifications if any"
                            ]
                        })
                
                row['match_percentage'] = round(match_percentage, 1)
                row['matched_skills'] = matched_skills
                row['missing_skills'] = missing_skills
                row['suggestions'] = suggestions
        
        return render_template_string(
            SEARCH_HTML,
            keyword=keyword,
            location=location,
            platform=platform,
            filter_loc=filter_loc,
            filter_platform=filter_platform,
            sort_by=sort_by,
            application_status=application_status,
            page=page,
            pages=pages,
            rows=rows,
            locations=locations,
            platforms=platforms,
            max=max,
            min=min
        )
    finally:
        conn.close()

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

@app.route('/details', methods=['GET', 'POST'])
def details():
    error = None
    conn = get_conn()
    res = conn.execute('SELECT * FROM resume ORDER BY uploaded_at DESC LIMIT 1').fetchone()
    conn.close()
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
                    # Create uploads directory if it doesn't exist
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    
                    # Check file size (5MB limit)
                    file_content = file.read()
                    file_size = len(file_content)
                    file.seek(0)  # Reset file pointer
                    
                    if file_size > 5 * 1024 * 1024:  # 5MB in bytes
                        error = 'File size exceeds 5MB limit'
                    else:
                        # Delete old resume if exists
                        if resume:
                            old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], resume['filename'])
                            if os.path.exists(old_file_path):
                                os.remove(old_file_path)
                        
                        # Save new resume
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        
                        # Update database
                        conn = get_conn()
                        conn.execute('INSERT INTO resume (filename, uploaded_at) VALUES (?,?)',
                                   (filename, datetime.now().strftime('%Y-%m-%d %H:%M')))
                        conn.commit()
                        conn.close()
                        
                        return redirect(url_for('details'))
                except Exception as e:
                    error = f'Error uploading file: {str(e)}'

    return render_template_string(DETAILS_HTML, resume=resume, error=error)

@app.route('/delete_resume', methods=['POST'])
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
    return redirect(url_for('details'))

@app.route('/uploads/<path:filename>')
def download(filename): return send_from_directory(app.config['UPLOAD_FOLDER'],filename)

@app.route('/_ping')
def ping(): return 'pong'

@app.route('/init-db')
def init_db_route():
    init_db()
    return 'Database initialized successfully!'

@app.route('/job_details/<int:job_id>')
def job_details(job_id):
    print(f"\nFetching job details for job_id: {job_id}")
    conn = get_conn()
    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    resume = conn.execute('SELECT * FROM resume ORDER BY uploaded_at DESC LIMIT 1').fetchone()
    conn.close()
    
    if not job:
        print("Job not found")
        return "Job not found", 404
    
    job = dict(job)
    print(f"Found job: {job['title']}")
    
    # Only fetch details if they haven't been fetched before
    if not job.get('description') or job['description'] == 'Click "Details" to view full description':
        try:
            details = fetch_job_details(job['url'])
            job.update(details)
            
            # Update the database with the fetched details
            conn = get_conn()
            conn.execute('''
                UPDATE jobs 
                SET description = ?, requirements = ?
                WHERE id = ?
            ''', (
                job['description'],
                json.dumps(job['requirements']),
                job_id
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error fetching job details: {str(e)}")
    
    # Calculate job match if resume exists
    if resume:
        print(f"Found resume: {resume['filename']}")
        resume_path = os.path.join(app.config['UPLOAD_FOLDER'], resume['filename'])
        resume_text = extract_text_from_file(resume_path)
        resume_skills, resume_entities = extract_skills_from_text(resume_text)
        print(f"Extracted skills from resume: {resume_skills}")
        
        match_percentage, matched_skills, missing_skills = calculate_job_match(
            job['description'],
            resume_skills
        )
        print(f"Match percentage: {match_percentage}")
        print(f"Matched skills: {matched_skills}")
        print(f"Missing skills: {missing_skills}")
        
        # Generate personalized suggestions
        suggestions = []
        
        # 1. Skills Analysis
        for category, skills in missing_skills.items():
            if skills:
                # Check if these skills are mentioned in the job description
                relevant_skills = [skill for skill in skills if skill.lower() in job['description'].lower()]
                if relevant_skills:
                    suggestions.append({
                        'category': f'Missing {category}',
                        'suggestion': f"The job requires {', '.join(relevant_skills)} which are not found in your resume. These skills are specifically mentioned in the job description.",
                        'action_items': [
                            f"Add {skill} to your skills section" for skill in relevant_skills
                        ]
                    })
        
        # 2. Experience Analysis
        experience_patterns = [
            r'(\d+)[\+]?\s*(?:years?|yrs?)\s*(?:of)?\s*experience',
            r'experience\s*(?:of)?\s*(\d+)[\+]?\s*(?:years?|yrs?)'
        ]
        
        for pattern in experience_patterns:
            matches = re.finditer(pattern, job['description'].lower())
            for match in matches:
                years = match.group(1)
                # Check if resume mentions any experience
                if not re.search(r'\d+\s*(?:years?|yrs?)\s*(?:of)?\s*experience', resume_text.lower()):
                    suggestions.append({
                        'category': 'Experience Requirements',
                        'suggestion': f"The job requires {years}+ years of experience. Your resume should clearly state your years of experience.",
                        'action_items': [
                            "Add specific years of experience in your work history",
                            "Quantify your experience with concrete examples",
                            "Highlight relevant projects and achievements"
                        ]
                    })
        
        # 3. Education Analysis
        education_keywords = ['bachelor', 'master', 'phd', 'degree', 'diploma', 'certification']
        job_education = [keyword for keyword in education_keywords if keyword in job['description'].lower()]
        resume_education = [keyword for keyword in education_keywords if keyword in resume_text.lower()]
        
        missing_education = [edu for edu in job_education if edu not in resume_education]
        if missing_education:
            suggestions.append({
                'category': 'Education Requirements',
                'suggestion': f"The job requires {', '.join(missing_education)} qualifications. Make sure your education section is complete.",
                'action_items': [
                    "List your highest education degree first",
                    "Include relevant certifications",
                    "Highlight relevant coursework and achievements"
                ]
            })
        
        # 4. Soft Skills Analysis
        soft_skills = ['communication', 'leadership', 'teamwork', 'problem-solving', 'time management', 'collaboration']
        job_soft_skills = [skill for skill in soft_skills if skill in job['description'].lower()]
        resume_soft_skills = [skill for skill in soft_skills if skill in resume_text.lower()]
        
        missing_soft_skills = [skill for skill in job_soft_skills if skill not in resume_soft_skills]
        if missing_soft_skills:
            suggestions.append({
                'category': 'Soft Skills',
                'suggestion': f"The job emphasizes {', '.join(missing_soft_skills)}. Add examples of these skills in your experience.",
                'action_items': [
                    f"Add specific examples of {skill} in your work experience" for skill in missing_soft_skills
                ]
            })
        
        # 5. Industry Experience Analysis
        industry_keywords = ['industry', 'sector', 'domain', 'field']
        job_industry = [keyword for keyword in industry_keywords if keyword in job['description'].lower()]
        resume_industry = [keyword for keyword in industry_keywords if keyword in resume_text.lower()]
        
        if job_industry and not resume_industry:
            suggestions.append({
                'category': 'Industry Experience',
                'suggestion': "The job requires specific industry experience. Highlight your relevant industry background.",
                'action_items': [
                    "List relevant industry experience",
                    "Highlight industry-specific projects",
                    "Mention industry certifications if any"
                ]
            })
        
        # 6. Technical Requirements Analysis
        technical_requirements = re.findall(r'(?:required|must have|should have|experience with|proficient in|knowledge of)\s+([^.,]+)', job['description'].lower())
        if technical_requirements:
            missing_tech = []
            for req in technical_requirements:
                if req not in resume_text.lower():
                    missing_tech.append(req)
            if missing_tech:
                suggestions.append({
                    'category': 'Technical Requirements',
                    'suggestion': f"The job specifically requires experience with {', '.join(missing_tech)}. Consider adding these to your resume.",
                    'action_items': [
                        f"Add experience with {tech} to your skills or experience section" for tech in missing_tech
                    ]
                })
        
        # 7. Project Experience Analysis
        if 'project' in job['description'].lower() and 'project' not in resume_text.lower():
            suggestions.append({
                'category': 'Project Experience',
                'suggestion': "The job emphasizes project experience. Make sure to highlight your relevant projects.",
                'action_items': [
                    "Add a dedicated projects section to your resume",
                    "Include project details, technologies used, and outcomes",
                    "Highlight your role and contributions in each project"
                ]
            })
        
        job['match_percentage'] = round(match_percentage, 1)
        job['matched_skills'] = matched_skills
        job['missing_skills'] = missing_skills
        job['suggestions'] = suggestions
        print(f"Total suggestions generated: {len(suggestions)}")
    else:
        print("No resume found")
        job['match_percentage'] = 0
        job['matched_skills'] = {}
        job['missing_skills'] = {}
        job['suggestions'] = []
    
    print(f"Returning job details with {len(job.get('suggestions', []))} suggestions")
    return jsonify(job)

# RUNNING
# python3 -m flask --app app.py --debug run

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
    'Programming Languages': ['python', 'java', 'javascript', 'c++', 'ruby', 'php', 'swift', 'kotlin', 'go', 'rust'],
    'Web Technologies': ['html', 'css', 'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring', 'express'],
    'Databases': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'oracle', 'sqlite'],
    'Cloud Platforms': ['aws', 'azure', 'gcp', 'heroku', 'digitalocean'],
    'DevOps': ['docker', 'kubernetes', 'jenkins', 'git', 'ci/cd', 'terraform'],
    'AI/ML': ['machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn', 'nlp', 'computer vision'],
    'Data Science': ['pandas', 'numpy', 'matplotlib', 'seaborn', 'r', 'tableau', 'power bi'],
    'Mobile Development': ['android', 'ios', 'react native', 'flutter', 'xamarin'],
    'Security': ['cybersecurity', 'penetration testing', 'network security', 'cryptography'],
    'Project Management': ['agile', 'scrum', 'kanban', 'jira', 'trello', 'project management'],
    'Soft Skills': ['leadership', 'communication', 'teamwork', 'problem-solving', 'time management']
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
    
    # Extract skills using keyword matching
    found_skills = {}
    for category, skills in TECHNICAL_SKILLS.items():
        category_skills = []
        for skill in skills:
            if skill in text:
                category_skills.append(skill)
        if category_skills:
            found_skills[category] = category_skills
    
    return found_skills, entities

def calculate_job_match(job_description, resume_skills):
    """Calculate job match percentage based on skills and requirements."""
    # Convert job description to lowercase
    job_desc = job_description.lower()
    
    # Extract skills from job description
    job_skills = {}
    for category, skills in TECHNICAL_SKILLS.items():
        category_skills = []
        for skill in skills:
            if skill in job_desc:
                category_skills.append(skill)
        if category_skills:
            job_skills[category] = category_skills
    
    # Calculate match score
    total_required_skills = sum(len(skills) for skills in job_skills.values())
    if total_required_skills == 0:
        return 0, [], {}
    
    matched_skills = {}
    missing_skills = {}
    
    for category, skills in job_skills.items():
        resume_category_skills = resume_skills.get(category, [])
        matched = [skill for skill in skills if skill in resume_category_skills]
        missing = [skill for skill in skills if skill not in resume_category_skills]
        
        if matched:
            matched_skills[category] = matched
        if missing:
            missing_skills[category] = missing
    
    total_matched = sum(len(skills) for skills in matched_skills.values())
    match_percentage = (total_matched / total_required_skills) * 100
    
    return match_percentage, matched_skills, missing_skills

def generate_improvement_suggestions(missing_skills, job_description):
    """Generate AI-powered suggestions for improvement."""
    suggestions = []
    
    # Analyze missing skills
    for category, skills in missing_skills.items():
        if skills:
            suggestions.append({
                'category': category,
                'missing_skills': skills,
                'suggestion': f"Consider adding experience with {', '.join(skills)} to improve your match for this role.",
                'action_items': [
                    f"Add {skill} to your skills section" for skill in skills
                ]
            })
    
    # Analyze job description for additional requirements
    doc = nlp(job_description)
    
    # Look for experience requirements
    experience_patterns = [
        r'(\d+)[\+]?\s*(?:years?|yrs?)\s*(?:of)?\s*experience',
        r'experience\s*(?:of)?\s*(\d+)[\+]?\s*(?:years?|yrs?)'
    ]
    
    for pattern in experience_patterns:
        matches = re.finditer(pattern, job_description.lower())
        for match in matches:
            years = match.group(1)
            suggestions.append({
                'category': 'Experience',
                'suggestion': f"The job requires {years}+ years of experience. Make sure your resume highlights relevant experience.",
                'action_items': [
                    "Quantify your experience with specific years",
                    "Highlight relevant projects and achievements",
                    "Emphasize transferable skills from other roles"
                ]
            })
    
    # Look for education requirements
    education_keywords = ['bachelor', 'master', 'phd', 'degree', 'diploma', 'certification']
    for keyword in education_keywords:
        if keyword in job_description.lower():
            suggestions.append({
                'category': 'Education',
                'suggestion': f"The job mentions {keyword} requirements. Ensure your education qualifications are clearly stated.",
                'action_items': [
                    "List your highest education degree first",
                    "Include relevant certifications",
                    "Highlight relevant coursework"
                ]
            })
    
    # Look for specific responsibilities
    responsibility_keywords = ['responsible for', 'duties include', 'key responsibilities', 'role and responsibilities']
    for keyword in responsibility_keywords:
        if keyword in job_description.lower():
            suggestions.append({
                'category': 'Responsibilities',
                'suggestion': "The job description lists specific responsibilities. Align your experience with these requirements.",
                'action_items': [
                    "Review your past roles for similar responsibilities",
                    "Highlight relevant achievements in these areas",
                    "Use similar keywords in your experience descriptions"
                ]
            })
    
    # Look for soft skills
    soft_skills = ['communication', 'leadership', 'teamwork', 'problem-solving', 'time management', 'collaboration']
    found_soft_skills = []
    for skill in soft_skills:
        if skill in job_description.lower():
            found_soft_skills.append(skill)
    
    if found_soft_skills:
        suggestions.append({
            'category': 'Soft Skills',
            'suggestion': f"The job emphasizes these soft skills: {', '.join(found_soft_skills)}. Highlight your experience in these areas.",
            'action_items': [
                f"Add examples of {skill} in your experience" for skill in found_soft_skills
            ]
        })
    
    # Look for industry-specific requirements
    industry_keywords = ['industry', 'sector', 'domain', 'field']
    for keyword in industry_keywords:
        if keyword in job_description.lower():
            suggestions.append({
                'category': 'Industry Experience',
                'suggestion': "The job requires specific industry experience. Highlight your relevant industry background.",
                'action_items': [
                    "List relevant industry experience",
                    "Highlight industry-specific projects",
                    "Mention industry certifications if any"
                ]
            })
    
    return suggestions

# Add the SAVED_JOBS_HTML template
SAVED_JOBS_HTML = NAVBAR + '''
<div class="container-fluid py-4">
  <div class="row mb-4">
    <div class="col-12">
      <h2 class="display-5 mb-4 text-primary">Saved Jobs</h2>
      <div class="card shadow-sm">
        <div class="card-body">
          <div class="row">
            <div class="col-12">
              <div class="job-list">
                {% for job in saved_jobs %}
                  <div class="card mb-3 hover-card">
                    <div class="card-body">
                      <div class="d-flex justify-content-between align-items-start mb-2">
                        <div class="flex-grow-1">
                          <h5 class="card-title mb-1">
                            <a href="{{ job['url'] }}" target="_blank" class="text-decoration-none">{{ job['title'] }}</a>
                            {% if job.get('match_percentage') is not none %}
                            <span class="badge {{ 'bg-success' if job.get('match_percentage') >= 70 else 'bg-warning' if job.get('match_percentage') >= 40 else 'bg-danger' }} ms-2">
                              {{ job.get('match_percentage') }}% Match
                            </span>
                            {% endif %}
                          </h5>
                          <h6 class="card-subtitle mb-2 text-muted">{{ job['company'] }}</h6>
                          <div class="d-flex align-items-center text-muted mb-2">
                            <small class="me-3"><i class="bi bi-geo-alt"></i> {{ job['location'] }}</small>
                            <small class="me-3"><i class="bi bi-calendar"></i> Saved on {{ job['saved_at'] }}</small>
                            <small><i class="bi bi-globe"></i> {{ job['platform'] }}</small>
                          </div>
                        </div>
                        <div class="d-flex gap-2">
                          <button class="btn btn-sm btn-outline-primary view-details" data-job-id="{{ job['id'] }}">
                            <i class="bi bi-eye"></i> Details
                          </button>
                          <button class="btn btn-sm btn-outline-danger unsave-job" data-job-id="{{ job['id'] }}">
                            <i class="bi bi-bookmark-x"></i> Unsave
                          </button>
                          <button class="btn btn-sm btn-outline-primary apply-job" data-job-id="{{ job['id'] }}" type="button">
                            <i class="bi bi-send"></i> Apply
                          </button>
                        </div>
                      </div>
                      <p class="card-text description-content">{{ job['description'] }}</p>
                      
                      <!-- AI Job Match Analysis Section - Initially Hidden -->
                      <div class="match-analysis mt-4" style="display: none;">
                        <h6 class="mb-3">AI Job Match Analysis</h6>
                        
                        <!-- Match Score -->
                        <div class="match-score mb-3">
                          <div class="d-flex align-items-center">
                            <div class="match-percentage me-2">0%</div>
                            <div class="progress flex-grow-1" style="height: 8px;">
                              <div class="progress-bar"
                                   role="progressbar"
                                   style="width: 0%"
                                   aria-valuenow="0"
                                   aria-valuemin="0"
                                   aria-valuemax="100"></div>
                            </div>
                          </div>
                        </div>

                        <!-- Matched Skills -->
                        <div class="matched-skills mb-3">
                          <h6 class="mb-2">Matched Skills</h6>
                          <div class="skills-container"></div>
                        </div>

                        <!-- Suggestions -->
                        <div class="suggestions">
                          <h6 class="mb-2">Improvement Suggestions</h6>
                          <div class="suggestions-container"></div>
                        </div>
                      </div>
                    </div>
                  </div>
                {% endfor %}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  .job-list {
    max-width: 100%;
    margin: 0 auto;
  }
  
  .hover-card {
    transition: all 0.3s ease;
  }
  
  .hover-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 16px rgba(0,0,0,0.1) !important;
  }
  
  .description-content {
    white-space: pre-wrap;
    word-wrap: break-word;
    font-size: 0.95rem;
    line-height: 1.5;
    color: #6c757d;
  }
  
  .match-analysis {
    background-color: #f8f9fa;
    border-radius: 8px;
    padding: 1.5rem;
    margin-top: 1rem;
  }
  
  .match-score {
    margin-bottom: 1.5rem;
  }
  
  .match-percentage {
    font-size: 1.5rem;
    font-weight: bold;
    min-width: 60px;
  }
  
  .progress {
    background-color: #e9ecef;
    border-radius: 4px;
    overflow: hidden;
  }
  
  .suggestion-card {
    background-color: white;
    border-radius: 8px;
    border: 1px solid #e9ecef;
    overflow: hidden;
    margin-bottom: 1rem;
  }
  
  .suggestion-header {
    background-color: #e7f5ff;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #e9ecef;
    color: #0a58ca;
  }
  
  .suggestion-body {
    padding: 1rem;
  }
  
  .action-items ul {
    list-style-type: none;
    padding-left: 0;
    margin-bottom: 0;
  }
  
  .action-items li {
    position: relative;
    padding-left: 1.5rem;
    margin-bottom: 0.5rem;
  }
  
  .action-items li:before {
    content: "→";
    position: absolute;
    left: 0;
    color: #0dcaf0;
  }
  
  .action-items li:last-child {
    margin-bottom: 0;
  }
  
  .matched-skills .badge {
    font-size: 0.85rem;
    padding: 0.35em 0.65em;
  }
  
  .card {
    border: none;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  }
  
  .btn {
    font-weight: 500;
  }
  
  .badge {
    font-weight: 500;
  }
  
  .text-muted {
    color: #6c757d !important;
  }
  
  .bi {
    margin-right: 0.25rem;
  }
</style>

<script>
document.addEventListener('DOMContentLoaded', function() {
  const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
  
  // View Details functionality
  document.querySelectorAll('.view-details').forEach(button => {
    button.addEventListener('click', async function() {
      const jobId = this.dataset.jobId;
      loadingModal.show();
      
      try {
        const response = await fetch(`/job_details/${jobId}`);
        const job = await response.json();
        
        const card = this.closest('.card');
        const descriptionContent = card.querySelector('.description-content');
        if (descriptionContent) {
          descriptionContent.innerHTML = job.description.replace(/\\n/g, '<br>');
        }
        
        const matchAnalysis = card.querySelector('.match-analysis');
        if (matchAnalysis) {
          matchAnalysis.style.display = 'block';
          
          const matchScore = matchAnalysis.querySelector('.match-percentage');
          const progressBar = matchAnalysis.querySelector('.progress-bar');
          if (matchScore && progressBar && job.match_percentage !== undefined) {
            matchScore.textContent = `${job.match_percentage}%`;
            progressBar.style.width = `${job.match_percentage}%`;
            progressBar.setAttribute('aria-valuenow', job.match_percentage);
            progressBar.className = `progress-bar ${job.match_percentage >= 70 ? 'bg-success' : job.match_percentage >= 40 ? 'bg-warning' : 'bg-danger'}`;
          }
          
          const skillsContainer = matchAnalysis.querySelector('.skills-container');
          if (skillsContainer && job.matched_skills) {
            let skillsHtml = '';
            for (const [category, skills] of Object.entries(job.matched_skills)) {
              if (skills && skills.length > 0) {
                skillsHtml += `
                  <div class="mb-2">
                    <small class="text-muted">${category}:</small>
                    <div>
                      ${skills.map(skill => `<span class="badge bg-success me-1 mb-1">${skill}</span>`).join('')}
                    </div>
                  </div>
                `;
              }
            }
            skillsContainer.innerHTML = skillsHtml || '<p class="text-muted">No matched skills found.</p>';
          }
          
          const suggestionsContainer = matchAnalysis.querySelector('.suggestions-container');
          if (suggestionsContainer && job.suggestions) {
            if (job.suggestions.length > 0) {
              let suggestionsHtml = '';
              job.suggestions.forEach(suggestion => {
                suggestionsHtml += `
                  <div class="suggestion-card mb-3">
                    <div class="suggestion-header">
                      <i class="bi bi-lightbulb me-2"></i>
                      <strong>${suggestion.category}</strong>
                    </div>
                    <div class="suggestion-body">
                      <p class="mb-2">${suggestion.suggestion}</p>
                      ${suggestion.action_items ? `
                        <div class="action-items">
                          <small class="text-muted d-block mb-1">Recommended Actions:</small>
                          <ul class="mb-0">
                            ${suggestion.action_items.map(item => `<li>${item}</li>`).join('')}
                          </ul>
                        </div>
                      ` : ''}
                    </div>
                  </div>
                `;
              });
              suggestionsContainer.innerHTML = suggestionsHtml;
            } else {
              suggestionsContainer.innerHTML = '<p class="text-muted">No suggestions available.</p>';
            }
          }
        }
      } catch (error) {
        console.error('Error fetching job details:', error);
        alert('Error loading job details. Please try again.');
      } finally {
        loadingModal.hide();
      }
    });
  });
  
  // Unsave Job functionality
  document.querySelectorAll('.unsave-job').forEach(button => {
    button.addEventListener('click', async function() {
      const jobId = this.dataset.jobId;
      try {
        const response = await fetch(`/unsave_job/${jobId}`, { method: 'POST' });
        if (response.ok) {
          const card = this.closest('.card');
          card.remove();
        } else {
          alert('Error unsaving job. Please try again.');
        }
      } catch (error) {
        console.error('Error unsaving job:', error);
        alert('Error unsaving job. Please try again.');
      }
    });
  });
  
  // Initialize apply buttons
  document.querySelectorAll('.apply-job').forEach(button => {
    button.addEventListener('click', async function(e) {
      e.preventDefault();
      const jobId = this.dataset.jobId;
      
      try {
        const response = await fetch(`/apply_job/${jobId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
          // Replace Apply button with Didn't Apply button
          const didntApplyButton = document.createElement('button');
          didntApplyButton.className = 'btn btn-sm btn-outline-danger didnt-apply';
          didntApplyButton.dataset.jobId = jobId;
          didntApplyButton.type = 'button';
          didntApplyButton.innerHTML = '<i class="bi bi-x-circle"></i> Didn\'t Apply';
          this.replaceWith(didntApplyButton);
          
          // Add the applied icon to the title
          const card = this.closest('.card');
          const titleLink = card.querySelector('.card-title a');
          if (titleLink && !titleLink.querySelector('.bi-check-circle-fill')) {
            const appliedIcon = document.createElement('i');
            appliedIcon.className = 'bi bi-check-circle-fill text-success ms-2';
            appliedIcon.title = 'Applied';
            titleLink.appendChild(appliedIcon);
          }
          
          // Show success message
          const alert = document.createElement('div');
          alert.className = 'alert alert-success alert-dismissible fade show mt-3';
          alert.innerHTML = `
            <i class="bi bi-check-circle me-2"></i>
            Application recorded! You can track your application status in the Application Tracker.
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
          `;
          card.querySelector('.card-body').appendChild(alert);
          
          // Get the job URL and open it in a new tab
          const jobUrl = card.querySelector('.card-title a').href;
          window.open(jobUrl, '_blank');
          
          // Initialize the didn't apply button
          initializeDidntApplyButton(didntApplyButton);
        } else if (data.status === 'already_applied') {
          alert('You have already applied to this job.');
        } else {
          alert('Error recording application. Please try again.');
        }
      } catch (error) {
        console.error('Error applying to job:', error);
        alert('Error recording application. Please try again.');
      }
    });
  });
  
  // Initialize didn't apply buttons
  document.querySelectorAll('.didnt-apply').forEach(button => {
    button.addEventListener('click', async function(e) {
      e.preventDefault();
      const jobId = this.dataset.jobId;
      
      try {
        const response = await fetch(`/update_application_status/${jobId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify({ status: 'Not Applied' })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
          // Replace the button with Apply button
          const applyButton = document.createElement('button');
          applyButton.className = 'btn btn-sm btn-outline-primary apply-job';
          applyButton.dataset.jobId = jobId;
          applyButton.type = 'button';
          applyButton.innerHTML = '<i class="bi bi-send"></i> Apply';
          this.replaceWith(applyButton);
          
          // Remove the applied icon
          const card = this.closest('.card');
          const appliedIcon = card.querySelector('.bi-check-circle-fill');
          if (appliedIcon) {
            appliedIcon.remove();
          }
          
          // Show success message
          const alert = document.createElement('div');
          alert.className = 'alert alert-info alert-dismissible fade show mt-3';
          alert.innerHTML = `
            <i class="bi bi-info-circle me-2"></i>
            Application status updated to "Not Applied".
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
          `;
          card.querySelector('.card-body').appendChild(alert);
          
          // Reinitialize the apply button
          initializeApplyButton(applyButton);
        } else {
          alert('Error updating application status. Please try again.');
        }
      } catch (error) {
        console.error('Error updating application status:', error);
        alert('Error updating application status. Please try again.');
      }
    });
  });
  
  function initializeApplyButton(button) {
    button.addEventListener('click', async function(e) {
      e.preventDefault();
      const jobId = this.dataset.jobId;
      
      try {
        const response = await fetch(`/apply_job/${jobId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
          this.innerHTML = '<i class="bi bi-check-circle"></i> Applied';
          this.classList.remove('btn-outline-primary');
          this.classList.add('btn-success');
          this.disabled = true;
          
          // Show success message
          const card = this.closest('.card');
          const alert = document.createElement('div');
          alert.className = 'alert alert-success alert-dismissible fade show mt-3';
          alert.innerHTML = `
            <i class="bi bi-check-circle me-2"></i>
            Application recorded! You can track your application status in the Application Tracker.
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
          `;
          card.querySelector('.card-body').appendChild(alert);
          
          // Get the job URL and open it in a new tab
          const jobUrl = card.querySelector('.card-title a').href;
          window.open(jobUrl, '_blank');
        } else if (data.status === 'already_applied') {
          alert('You have already applied to this job.');
        } else {
          alert('Error recording application. Please try again.');
        }
      } catch (error) {
        console.error('Error applying to job:', error);
        alert('Error recording application. Please try again.');
      }
    });
  }
});
</script>

<style>
  .suggestions .alert {
    border-left: 4px solid #0dcaf0;
  }
  
  .suggestions .alert ul {
    list-style-type: none;
  }
  
  .suggestions .alert li {
    position: relative;
    padding-left: 1.5rem;
  }
  
  .suggestions .alert li:before {
    content: "•";
    position: absolute;
    left: 0.5rem;
    color: #0dcaf0;
  }
  
  .suggestions .alert strong {
    color: #0a58ca;
  }
  
  .suggestions .alert small {
    font-size: 0.875rem;
  }
</style>
''' + FOOTER

# Add new routes for saved jobs functionality
@app.route('/save_job/<int:job_id>', methods=['POST'])
def save_job(job_id):
    conn = get_conn()
    try:
        # Check if job exists
        job = conn.execute('SELECT id FROM jobs WHERE id = ?', (job_id,)).fetchone()
        if not job:
            return jsonify({'status': 'error', 'message': 'Job not found'}), 404

        # Check if job is already saved
        existing = conn.execute('SELECT id FROM saved_jobs WHERE job_id = ?', (job_id,)).fetchone()
        if existing:
            return jsonify({'status': 'already_saved'})

        # Save the job
        conn.execute('INSERT INTO saved_jobs (job_id, saved_at) VALUES (?, ?)',
                    (job_id, datetime.now()))
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error saving job: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/unsave_job/<int:job_id>', methods=['POST'])
def unsave_job(job_id):
    conn = get_conn()
    try:
        conn.execute('DELETE FROM saved_jobs WHERE job_id = ?', (job_id,))
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error unsaving job: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/saved_jobs')
def saved_jobs():
    conn = get_conn()
    saved_jobs = conn.execute('''
        SELECT j.*, sj.saved_at 
        FROM jobs j 
        JOIN saved_jobs sj ON j.id = sj.job_id 
        ORDER BY sj.saved_at DESC
    ''').fetchall()
    conn.close()
    
    saved_jobs = [dict(job) for job in saved_jobs]
    
    # Calculate match percentage for each saved job
    resume = get_conn().execute('SELECT * FROM resume ORDER BY uploaded_at DESC LIMIT 1').fetchone()
    if resume:
        resume_path = os.path.join(app.config['UPLOAD_FOLDER'], resume['filename'])
        resume_text = extract_text_from_file(resume_path)
        resume_skills, _ = extract_skills_from_text(resume_text)
        
        for job in saved_jobs:
            if job['description'] and job['description'] != 'Click "Details" to view full description':
                match_percentage, matched_skills, _ = calculate_job_match(
                    job['description'],
                    resume_skills
                )
                job['match_percentage'] = round(match_percentage, 1)
                job['matched_skills'] = matched_skills
    
    return render_template_string(SAVED_JOBS_HTML, saved_jobs=saved_jobs)

# Add the apply job route
@app.route('/apply_job/<int:job_id>', methods=['POST'])
def apply_job(job_id):
    conn = None
    try:
        conn = get_conn()
        
        # Check if job exists
        job = conn.execute('SELECT id FROM jobs WHERE id = ?', (job_id,)).fetchone()
        if not job:
            return jsonify({'status': 'error', 'message': 'Job not found'}), 404

        # Check if already applied
        existing = conn.execute('SELECT id FROM applications WHERE job_id = ?', (job_id,)).fetchone()
        if existing:
            return jsonify({'status': 'already_applied'})

        # Add to applications
        conn.execute('INSERT INTO applications (job_id, status, applied_at) VALUES (?, ?, ?)',
                    (job_id, 'Applied', datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error applying to job: {str(e)}")
        if conn:
            conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/update_application_status/<int:job_id>', methods=['POST'])
def update_application_status(job_id):
    conn = None
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'status': 'error', 'message': 'Status is required'}), 400
        
        conn = get_conn()
        
        # Check if job exists
        job = conn.execute('SELECT id FROM jobs WHERE id = ?', (job_id,)).fetchone()
        if not job:
            return jsonify({'status': 'error', 'message': 'Job not found'}), 404
            
        # Check if application exists
        application = conn.execute('SELECT id FROM applications WHERE job_id = ?', (job_id,)).fetchone()
        if not application:
            return jsonify({'status': 'error', 'message': 'No application found for this job'}), 404
            
        if new_status == 'Not Applied':
            # Remove the application record
            conn.execute('DELETE FROM applications WHERE job_id = ?', (job_id,))
        else:
            # Update the application status for other statuses
            conn.execute('UPDATE applications SET status = ? WHERE job_id = ?',
                        (new_status, job_id))
        
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
