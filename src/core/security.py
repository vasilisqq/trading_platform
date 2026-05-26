import bcrypt
import jwt
from datetime import datetime, timedelta
from src.core.config import settings
import hashlib

def hash_password(password: str) -> str:
    password_with_pepper = password+settings.SECRET_PEPPER.get_secret_value()
    combined = password_with_pepper.encode()
    hash256 = hashlib.sha256(combined).digest()
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(hash256, salt)
    return hashed.decode()



