import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine  # type: ignore[import-not-found]
from sqlalchemy.orm import declarative_base, sessionmaker  # type: ignore[import-not-found]

# 1. This loads the variables from your .env file
def load_dotenv_file(path=".env"):
    """Load simple KEY=VALUE entries without requiring python-dotenv."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


load_dotenv_file()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "employee_db")

# 2. Safely encode the password in case it has symbols like @, #, etc.
encoded_password = quote_plus(DB_PASSWORD)

# 3. Build connection URL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()