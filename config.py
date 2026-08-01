import os


class Config:
    """Application configuration."""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
    SECRET_KEY = os.environ.get('SECRET_KEY', 'clauseguard-secret-key-2024')

    @staticmethod
    def init_app(app):
        """Initialize app with config and ensure upload folder exists."""
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
