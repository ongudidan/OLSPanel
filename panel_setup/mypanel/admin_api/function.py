import os
import base64
from cryptography.fernet import Fernet
import secrets 

ENCODED_KEY_DIR = b"L3Zhci9saWIvLmNvbmZpZy8uc3lzZGF0YS8uY2FjaGUvaGlkZGVuL2tleXM="

def generate_random_api_key(length=32):
    # 32 hex chars = 16 bytes random
    return secrets.token_hex(length // 2)
    
def get_key_dir():
    decoded = base64.b64decode(ENCODED_KEY_DIR).decode()
    return decoded

KEY_DIR = get_key_dir()
KEY_FILENAME = "ol_sk.key"
KEY_PATH = os.path.join(KEY_DIR, KEY_FILENAME)
API_KEY_PATH = "/etc/admin_api_key"  # You can customize this too

def ensure_key_dir():
    if not os.path.exists(KEY_DIR):
        os.makedirs(KEY_DIR, exist_ok=True)
        os.chmod(KEY_DIR, 0o700)  # Only owner access

def generate_encryption_key():
    ensure_key_dir()
    if not os.path.exists(KEY_PATH):
        key = Fernet.generate_key()
        with open(KEY_PATH, "wb") as key_file:
            key_file.write(key)
        os.chmod(KEY_PATH, 0o600)  # Owner read/write only
        print(f"Encryption key generated and saved to {KEY_PATH}")

def load_encryption_key():
    if not os.path.exists(KEY_PATH):
        raise FileNotFoundError(f"Encryption key not found at {KEY_PATH}, generate it first.")
    with open(KEY_PATH, "rb") as key_file:
        return key_file.read()

def encrypt_and_store_api_key(api_key):
    generate_encryption_key()
    key = load_encryption_key()
    f = Fernet(key)
    encrypted = f.encrypt(api_key.encode())

    with open(API_KEY_PATH, "wb") as f_api:
        f_api.write(encrypted)
    os.chmod(API_KEY_PATH, 0o600)
    print(f"Encrypted API key saved to {API_KEY_PATH}")

def read_and_decrypt_api_key():
    if not os.path.exists(API_KEY_PATH):
        raise FileNotFoundError(f"Encrypted API key file not found at {API_KEY_PATH}.")

    key = load_encryption_key()
    f = Fernet(key)

    with open(API_KEY_PATH, "rb") as f_api:
        encrypted = f_api.read()

    decrypted = f.decrypt(encrypted)
    return decrypted.decode()

if __name__ == "__main__":
    random_api_key = generate_random_api_key(32)
    print("Generated API key:", random_api_key)
    encrypt_and_store_api_key(random_api_key)
    print("Decrypted API key:", read_and_decrypt_api_key())