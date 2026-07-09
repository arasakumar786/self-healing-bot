import json, os, bcrypt

USERS_FILE = "/app/data/users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE) as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def ensure_default_admin():
    users = load_users()
    if not users:
        password_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        users = [{"username": "admin", "password_hash": password_hash}]
        save_users(users)
        print("Created default admin user (admin / admin123) - CHANGE THIS PASSWORD IMMEDIATELY")

def verify_user(username, password):
    users = load_users()
    for u in users:
        if u["username"] == username:
            return bcrypt.checkpw(password.encode(), u["password_hash"].encode())
    return False

def create_user(username, password):
    users = load_users()
    if any(u["username"] == username for u in users):
        return False
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    users.append({"username": username, "password_hash": password_hash})
    save_users(users)
    return True
