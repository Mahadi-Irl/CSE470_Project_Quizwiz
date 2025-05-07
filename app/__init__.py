from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from config import Config

db = SQLAlchemy()
login = LoginManager()
mail = Mail()
csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login.init_app(app)
    csrf.init_app(app)
    
    # Initialize mail only if email settings are configured
    if app.config.get('MAIL_SERVER'):
        mail.init_app(app)

    # Configure login
    login.login_view = 'auth.login'
    login.login_message = 'Please log in to access this page.'
    login.login_message_category = 'info'

    # Register blueprints
    from app.views.auth import auth_bp
    from app.views.main import main_bp
    from app.views.quiz import quiz_bp
    from app.views.user import user_bp
    from app.views.teacher import teacher_bp
    from app.views.student import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)

    # Create database tables
    with app.app_context():
        db.create_all()

    return app 