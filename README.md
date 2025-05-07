# Quiztaker - Online Quiz Platform

A Flask-based web application for creating, taking, and managing quizzes. The platform supports both teachers and students with features like quiz creation, taking quizzes, viewing results, and bookmarking quizzes.

## Features

### For Teachers
- Create and manage quizzes
- Set time limits and attempt limits
- Add multiple-choice and descriptive questions
- View detailed quiz statistics and performance metrics
- Release grades to students
- Export quiz results
- View student feedback

### For Students
- Take quizzes with time limits
- View quiz history and performance
- Bookmark quizzes for later
- View detailed results after grades are released
- Submit feedback for quizzes
- Track progress across multiple attempts

## Project Structure

```
Quiztaker/
├── app/                      # Main application package
│   ├── models/              # Database models
│   │   ├── quiz.py         # Quiz, Question, Answer models
│   │   ├── user.py         # User model
│   │   ├── feedback.py     # QuizFeedback model
│   │   └── answer.py       # Answer model
│   │
│   ├── views/              # Route handlers
│   │   ├── quiz.py        # Quiz-related routes
│   │   └── main.py        # Main routes (home, profile, etc.)
│   │
│   ├── templates/          # HTML templates
│   │   ├── base.html      # Base template
│   │   ├── main/          # Main templates
│   │   ├── student/       # Student-specific templates
│   │   ├── quiz/          # Quiz-related templates
│   │   ├── teacher/       # Teacher-specific templates
│   │   ├── email/         # Email templates
│   │   ├── auth/          # Authentication templates
│   │   └── user/          # User-related templates
│   │
│   ├── static/            # Static files (CSS, JS, images)
│   ├── utils/             # Utility functions
│   ├── forms/             # Form definitions
│   └── __init__.py        # Application factory
│
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── run.py                # Application entry point
└── README.md             # Project documentation
```

## Setup Instructions

1. Clone the repository:
```bash
git clone https://github.com/yourusername/quiztaker.git
cd quiztaker
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python run.py
```

The application will automatically create a SQLite database file (`quizwizz.db`) in the project directory when first run.

## Dependencies

- Flask - Web framework
- SQLAlchemy - Database ORM
- Flask-Login - User authentication
- Flask-WTF - Form handling
- Flask-Mail - Email functionality
- Bootstrap - Frontend framework
- SQLite - Database (development)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Flask documentation
- Bootstrap documentation
- SQLAlchemy documentation 