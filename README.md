# Quizwizz

A modern quiz platform for teachers and students built with Flask.

## Features

- User Authentication (Sign up, Login, Profile Management)
- Quiz Creation & Management
- Quiz Distribution & Access Control
- Quiz Analytics & Feedback
- Student Experience & History

## Project Structure

```
quizwizz/
├── app/
│   ├── models/         # Database models
│   ├── views/          # Route handlers
│   ├── controllers/    # Business logic
│   ├── static/         # CSS, JS, images
│   └── templates/      # HTML templates
├── config.py           # Configuration
├── run.py             # Application entry point
└── requirements.txt   # Project dependencies
```

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file with:
```
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///quizwizz.db
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

4. Run the application:
```bash
flask run
```

## Technologies Used

- Flask (Web Framework)
- SQLAlchemy (ORM)
- Flask-Login (Authentication)
- Flask-Mail (Email Support)
- HTML/CSS/JavaScript (Frontend) 