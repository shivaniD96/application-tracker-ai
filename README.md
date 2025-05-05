# Job Application Tracker

A Flask-based web application to help you track your job applications, search for jobs, and manage your resume.

## Features

- 🔍 Job Search: Search for jobs with keywords and location filters
- 📊 Application Tracker: Track the status of your job applications
- 📝 Resume Management: Upload and manage your resume
- 📅 Application Timeline: Keep track of when you applied and follow-ups
- 🔄 Status Updates: Update application status (Applied, Rejected, No response)
- 🌐 Multiple Job Boards: Search across LinkedIn, Indeed, Adzuna, and ZipRecruiter

## Setup Instructions

1. Clone the repository:
```bash
git clone https://github.com/shivaniD96/application-tracker-ai.git
cd application-tracker-ai
```

2. Create a virtual environment and activate it:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up API keys:
   Create a `.env` file in the project root with the following content:
   ```
   # Adzuna API Credentials
   ADZUNA_API_KEY=your_adzuna_api_key
   ADZUNA_API_SECRET=your_adzuna_api_secret

   # Indeed API Credentials
   INDEED_PUBLISHER_ID=your_indeed_publisher_id

   # LinkedIn API Credentials
   LINKEDIN_CLIENT_ID=your_linkedin_client_id
   LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret

   # ZipRecruiter API Credentials
   ZIPRECRUITER_API_KEY=your_ziprecruiter_api_key
   ```

   To get API keys:
   - Adzuna: https://developer.adzuna.com/
   - Indeed: https://www.indeed.com/publisher
   - LinkedIn: https://developer.linkedin.com/
   - ZipRecruiter: https://www.ziprecruiter.com/publishers

5. Initialize the database:
```bash
python3 -m flask --app app.py init-db
```

6. Run the application:
```bash
python3 -m flask --app app.py --debug run
```

7. Open your browser and navigate to `http://localhost:5000`

## Project Structure

- `app.py` - Main Flask application
- `uploads/` - Directory for storing uploaded resumes
- `jobs.db` - SQLite database for storing job listings and applications

## Dependencies

- Flask
- SQLite3
- BeautifulSoup4
- Requests
- python-dotenv

## Contributing

Feel free to submit issues and enhancement requests! 