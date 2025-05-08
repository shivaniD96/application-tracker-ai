.PHONY: setup install run clean init-db download-nlp-models check-python

# Python virtual environment name
VENV = venv

# Python version
PYTHON_VERSION = 3.9
PYTHON = python$(PYTHON_VERSION)
PIP = pip$(PYTHON_VERSION)

# Flask application name
FLASK_APP = app.py

check-python:
	@echo "Checking Python version..."
	@if ! command -v $(PYTHON) >/dev/null 2>&1; then \
		echo "Error: Python $(PYTHON_VERSION) is not installed. Please install it first."; \
		echo "On macOS, you can install it using: brew install python@$(PYTHON_VERSION)"; \
		exit 1; \
	fi
	@echo "Python $(PYTHON_VERSION) is installed."

setup: check-python
	$(PYTHON) -m venv $(VENV)
	@echo "Virtual environment created. Activate it with 'source venv/bin/activate'"

install: check-python
	. $(VENV)/bin/activate && pip install --upgrade pip
	. $(VENV)/bin/activate && pip install -r requirements.txt
	. $(VENV)/bin/activate && python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
	. $(VENV)/bin/activate && python -m spacy download en_core_web_sm
	@echo "Dependencies installed successfully"

run:
	. $(VENV)/bin/activate && python3 -m flask --app $(FLASK_APP) --debug run

init-db:
	. $(VENV)/bin/activate && flask --app $(FLASK_APP) init-db
	@echo "Database initialized successfully"

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name "*.egg" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".coverage" -exec rm -r {} +
	@echo "Cleaned up Python cache files"

help:
	@echo "Available commands:"
	@echo "  make check-python - Check if Python $(PYTHON_VERSION) is installed"
	@echo "  make setup       - Create Python virtual environment"
	@echo "  make install    - Install project dependencies and download NLP models"
	@echo "  make run        - Run the Flask application in debug mode"
	@echo "  make init-db    - Initialize the database"
	@echo "  make clean      - Clean up Python cache files"
	@echo "  make help       - Show this help message" 