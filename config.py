import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-cambiame")
    SEND_FILE_MAX_AGE_DEFAULT = 0  # evita que el navegador guarde en caché CSS/JS viejos

    # Si no hay DATABASE_URL (Neon), usamos sqlite local para poder
    # probar la app sin configurar nada primero.
    _db_url = os.environ.get("DATABASE_URL")
    if _db_url and _db_url.startswith("postgres://"):
        # Neon a veces da la URL con el prefijo viejo "postgres://"
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = _db_url or f"sqlite:///{os.path.join(BASE_DIR, 'messechat.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB para fotos/adjuntos
