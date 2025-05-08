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
CORS(app)  # Allow all origins
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['HOST'] = '0.0.0.0'  # Use IP instead of localhost
app.config['PORT'] = 5000

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

@app.route('/search', methods=['GET','POST'])
def search():
    conn = get_conn()
    try:
        keyword = request.form.get('keyword','') if request.method=='POST' else request.args.get('keyword','')
        location = request.form.get('location','') if request.method=='POST' else request.args.get('location','')
        platform = request.form.get('platform','') if request.method=='POST' else request.args.get('platform','')
        
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
        sort_by = request.args.get('sort_by', 'recent')
        application_status = request.args.get('application_status', '')
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
                
                row['match_percentage'] = round(match_percentage, 1)
                row['matched_skills'] = matched_skills
                row['missing_skills'] = missing_skills
                row['suggestions'] = generate_improvement_suggestions(missing_skills, row['description'])
        
        return jsonify({
            'jobs': rows,
            'total': total,
            'pages': pages,
            'current_page': page,
            'locations': locations,
            'platforms': platforms
        })
    finally:
        conn.close()

@app.route('/api/tracker', methods=['GET'])
def tracker():
    conn = get_conn()
    apps = conn.execute('SELECT a.id,a.job_id,a.status,a.applied_at,j.title FROM applications a JOIN jobs j ON a.job_id=j.id').fetchall()
    conn.close()
    apps = [dict(a) for a in apps]
    return jsonify({'applications': apps})

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

@app.route('/api/job_details/<int:job_id>')
def job_details(job_id):
    print(f"\nFetching job details for job_id: {job_id}")
    conn = get_conn()
    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    resume = conn.execute('SELECT * FROM resume ORDER BY uploaded_at DESC LIMIT 1').fetchone()
    conn.close()
    
    if not job:
        print("Job not found")
        return jsonify({"error": "Job not found"}), 404
    
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
            return jsonify({"error": str(e)}), 500
    
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
            r'(\d+)\+\s*(?:years?|yrs?)\s*(?:of)?\s*experience',
            r'experience\s*(?:of)?\s*(\d+)\+\s*(?:years?|yrs?)'
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
                    "List relevant industry experience prominently",
                    "Highlight industry-specific projects and achievements",
                    "Mention industry certifications and training",
                    "Include industry-specific tools and technologies you've used"
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
        job['match_percentage'] = None
        job['matched_skills'] = {}
        job['missing_skills'] = {}
        job['suggestions'] = []
    
    return jsonify(job)

@app.route('/api/update_application_status/<int:job_id>', methods=['POST'])
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

@app.route('/api/search', methods=['GET','POST'])
def api_search():
    return search()

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
        'neural networks', 'cnn', 'rnn', 'lstm', 'gan', 'svm', 'random forest', 'xgboost', 'lightgbm'
    ],
    'Data Science': [
        'pandas', 'numpy', 'matplotlib', 'seaborn', 'r', 'tableau', 'power bi', 'looker', 'qlik',
        'apache spark', 'hadoop', 'hive', 'pig', 'kafka', 'airflow', 'dbt', 'databricks', 'jupyter',
        'data visualization', 'statistical analysis', 'a/b testing', 'experiment design'
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
        'risk management', 'stakeholder management'
    ],
    'Soft Skills': [
        'leadership', 'communication', 'teamwork', 'problem-solving', 'time management', 'collaboration',
        'adaptability', 'critical thinking', 'creativity', 'emotional intelligence', 'conflict resolution',
        'mentoring', 'presentation skills', 'negotiation', 'decision making', 'strategic thinking'
    ],
    'Methodologies': [
        'agile', 'scrum', 'kanban', 'waterfall', 'devops', 'ci/cd', 'tdd', 'bdd', 'pair programming',
        'code review', 'technical documentation', 'api design', 'microservices', 'domain-driven design',
        'test-driven development', 'behavior-driven development'
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
            # Check for exact matches and variations
            if skill in job_desc or f"{skill}s" in job_desc or f"{skill}ing" in job_desc:
                category_skills.append(skill)
        if category_skills:
            job_skills[category] = category_skills
    
    # Calculate match score with weighted categories
    category_weights = {
        'Programming Languages': 1.5,
        'Web Technologies': 1.3,
        'Databases': 1.2,
        'Cloud Platforms': 1.2,
        'DevOps & Tools': 1.3,
        'AI/ML': 1.4,
        'Data Science': 1.3,
        'Mobile Development': 1.2,
        'Security': 1.2,
        'Project Management': 1.1,
        'Soft Skills': 1.0,
        'Methodologies': 1.1
    }
    
    total_weighted_skills = 0
    total_matched_weighted_skills = 0
    matched_skills = {}
    missing_skills = {}
    
    for category, skills in job_skills.items():
        weight = category_weights.get(category, 1.0)
        resume_category_skills = resume_skills.get(category, [])
        
        # Calculate weighted matches
        matched = [skill for skill in skills if skill in resume_category_skills]
        missing = [skill for skill in skills if skill not in resume_category_skills]
        
        total_weighted_skills += len(skills) * weight
        total_matched_weighted_skills += len(matched) * weight
        
        if matched:
            matched_skills[category] = matched
        if missing:
            missing_skills[category] = missing
    
    # Calculate final match percentage
    if total_weighted_skills == 0:
        return 0, {}, {}
    
    match_percentage = (total_matched_weighted_skills / total_weighted_skills) * 100
    
    # Add skill level analysis
    skill_levels = {
        'expert': ['expert', 'advanced', 'senior', 'lead', 'architect'],
        'intermediate': ['intermediate', 'mid-level', 'experienced'],
        'basic': ['basic', 'entry-level', 'junior', 'familiar']
    }
    
    # Analyze required skill levels from job description
    required_levels = {}
    for level, keywords in skill_levels.items():
        for keyword in keywords:
            if keyword in job_desc:
                required_levels[level] = True
    
    # Add level information to matched and missing skills
    for category in matched_skills:
        matched_skills[category] = {
            'skills': matched_skills[category],
            'level': 'expert' if 'expert' in required_levels else 'intermediate' if 'intermediate' in required_levels else 'basic'
        }
    
    for category in missing_skills:
        missing_skills[category] = {
            'skills': missing_skills[category],
            'level': 'expert' if 'expert' in required_levels else 'intermediate' if 'intermediate' in required_levels else 'basic'
        }
    
    return match_percentage, matched_skills, missing_skills

def generate_improvement_suggestions(missing_skills, job_description):
    """Generate AI-powered suggestions for improvement."""
    suggestions = []
    
    # Analyze missing skills with context
    for category, skill_info in missing_skills.items():
        skills = skill_info['skills']
        level = skill_info['level']
        
        if skills:
            # Get context from job description
            context = []
            for skill in skills:
                # Look for sentences containing the skill
                sentences = re.findall(r'[^.]*' + re.escape(skill) + r'[^.]*\.', job_description.lower())
                if sentences:
                    context.extend(sentences)
            
            # Generate contextual suggestions
            if context:
                context_str = ' '.join(context)
                action_items = [
                    f"Add {skill} to your skills section with {level} level proficiency" for skill in skills
                ]
                action_items.extend([
                    f"Highlight relevant projects or experience with {', '.join(skills)}",
                    f"Consider taking advanced courses or certifications in {', '.join(skills)}"
                ])
                suggestions.append({
                    'category': f'Missing {category} Skills',
                    'suggestion': f"The job requires {level} level knowledge of {', '.join(skills)}. Based on the job description: {context_str}",
                    'action_items': action_items
                })
            else:
                # If no specific context found, provide general suggestions
                suggestions.append({
                    'category': f'Missing {category} Skills',
                    'suggestion': f"The job requires {level} level knowledge of {', '.join(skills)}. These skills are important for this role.",
                    'action_items': [
                        f"Add {skill} to your skills section with {level} level proficiency" for skill in skills
                    ]
                })
    
    # Analyze experience requirements
    experience_patterns = [
        r'(\d+)\+\s*(?:years?|yrs?)\s*(?:of)?\s*experience',
        r'experience\s*(?:of)?\s*(\d+)\+\s*(?:years?|yrs?)',
        r'(\d+)\s*(?:years?|yrs?)\s*(?:of)?\s*experience'
    ]
    
    for pattern in experience_patterns:
        matches = re.finditer(pattern, job_description.lower())
        for match in matches:
            years = match.group(1)
            suggestions.append({
                'category': 'Experience Requirements',
                'suggestion': f"The job requires {years}+ years of experience. Make sure your resume clearly demonstrates your relevant experience.",
                'action_items': [
                    "Quantify your experience with specific years and achievements",
                    "Highlight relevant projects and their impact",
                    "Include metrics and results from your past roles",
                    "Emphasize transferable skills from other experiences"
                ]
            })
    
    # Analyze education requirements
    education_keywords = {
        'bachelor': ['bachelor', 'bs', 'ba', 'b.s.', 'b.a.'],
        'master': ['master', 'ms', 'ma', 'm.s.', 'm.a.'],
        'phd': ['phd', 'doctorate', 'ph.d.'],
        'certification': ['certification', 'certified', 'certificate']
    }
    
    for degree, keywords in education_keywords.items():
        if any(keyword in job_description.lower() for keyword in keywords):
            suggestions.append({
                'category': 'Education Requirements',
                'suggestion': f"The job requires a {degree} degree. Ensure your education qualifications are prominently displayed.",
                'action_items': [
                    f"List your {degree} degree first in the education section",
                    "Include relevant coursework and projects",
                    "Highlight academic achievements and honors",
                    "Mention relevant certifications if applicable"
                ]
            })
    
    # Analyze soft skills requirements
    soft_skills = {
        'communication': ['communication', 'communicate', 'presentation', 'writing', 'speaking'],
        'leadership': ['leadership', 'lead', 'manage', 'supervise', 'mentor'],
        'teamwork': ['teamwork', 'collaboration', 'team player', 'cross-functional'],
        'problem-solving': ['problem-solving', 'analytical', 'critical thinking', 'troubleshooting'],
        'time management': ['time management', 'deadline', 'prioritization', 'organization']
    }
    
    for skill, keywords in soft_skills.items():
        if any(keyword in job_description.lower() for keyword in keywords):
            suggestions.append({
                'category': 'Soft Skills',
                'suggestion': f"The job emphasizes {skill} skills. Add specific examples of these skills in your experience.",
                'action_items': [
                    f"Add concrete examples of {skill} in your work experience",
                    "Include metrics or results that demonstrate {skill}",
                    "Highlight relevant projects where {skill} was crucial",
                    "Mention any training or certifications related to {skill}"
                ]
            })
    
    # Analyze industry-specific requirements
    industry_keywords = ['industry', 'sector', 'domain', 'field', 'market']
    if any(keyword in job_description.lower() for keyword in industry_keywords):
        suggestions.append({
            'category': 'Industry Experience',
            'suggestion': "The job requires specific industry experience. Highlight your relevant industry background.",
            'action_items': [
                "List relevant industry experience prominently",
                "Highlight industry-specific projects and achievements",
                "Mention industry certifications and training",
                "Include industry-specific tools and technologies you've used"
            ]
        })
    
    return suggestions

if __name__ == '__main__':
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