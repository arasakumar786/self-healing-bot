import jwt, time, os
from dotenv import load_dotenv

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret")
JWT_ALGO = "HS256"
JWT_EXPIRY_SECONDS = 3600 * 8  # 8 hour session

def create_token(username):
    payload = {"sub": username, "exp": time.time() + JWT_EXPIRY_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def verify_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return payload["sub"]
    except Exception:
        return None
