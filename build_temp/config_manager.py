import json, os, base64
from cryptography.fernet import Fernet
import win32crypt

CONFIG_FILE = "config.json"
KEY_FILE = "config.key"


def _load_or_create_key() -> bytes:
    """Tworzy lub wczytuje klucz do szyfrowania ustawień."""
    if os.path.exists(KEY_FILE):
        enc = open(KEY_FILE, "rb").read()
        return win32crypt.CryptUnprotectData(enc, None, None, None, 0)[1]
    key = Fernet.generate_key()
    enc = win32crypt.CryptProtectData(key, None, None, None, None, 0)
    open(KEY_FILE, "wb").write(enc)
    return key


FERNET = Fernet(_load_or_create_key())


def load_config() -> dict:
    """Wczytuje config z pliku."""
    if not os.path.exists(CONFIG_FILE):
        return {"pin": None}
    try:
        data = json.load(open(CONFIG_FILE, "r", encoding="utf-8"))
        if "pin" in data and data["pin"]:
            data["pin"] = FERNET.decrypt(base64.b64decode(data["pin"])).decode()
        return data
    except Exception:
        return {"pin": None}


def save_config(config: dict):
    """Zapisuje config do pliku."""
    data = dict(config)
    if data.get("pin"):
        data["pin"] = base64.b64encode(FERNET.encrypt(data["pin"].encode())).decode()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
