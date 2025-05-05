# Job Application Tracker

A Flask-based web application to help you track your job applications, search for jobs, and manage your resume.

## Features

- 🔍 Job Search: Search for jobs with keywords and location filters
- 📊 Application Tracker: Track the status of your job applications
- 📝 Resume Management: Upload and manage your resume
- 📅 Application Timeline: Keep track of when you applied and follow-ups
- 🔄 Status Updates: Update application status (Applied, Rejected, No response)

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

4. Initialize the database:
```bash
python3 -m flask --app app.py init-db
```

5. Run the application:
```bash
python3 -m flask --app app.py --debug run
```

6. Open your browser and navigate to `http://localhost:5000`

## Project Structure

- `app.py` - Main Flask application
- `uploads/` - Directory for storing uploaded resumes
- `jobs.db` - SQLite database for storing job listings and applications

## Dependencies

- Flask
- SQLite3
- BeautifulSoup4
- Requests

## Contributing

Feel free to submit issues and enhancement requests! 