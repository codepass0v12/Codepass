import os
import base64
import json
from cryptography.fernet import Fernet
import win32crypt  # DPAPI — natywne szyfrowanie Windows


KEY_FILE = "key.enc"


# ======================== 🧩 Tworzenie / ładowanie klucza ========================

def load_or_create_fernet() -> Fernet:
    """
    Tworzy lub wczytuje klucz szyfrowania (Fernet),
    zabezpieczony systemowo przy użyciu Windows DPAPI.
    """
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            encrypted_key = f.read()
        decrypted = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
        return Fernet(decrypted)

    # Jeśli brak klucza — generuj nowy
    key = Fernet.generate_key()
    protected = win32crypt.CryptProtectData(key, None, None, None, None, 0)
    with open(KEY_FILE, "wb") as f:
        f.write(protected)
    return Fernet(key)


# ======================== 📂 Odczyt / zapis ========================

def read_entries(fernet: Fernet, filename: str) -> list:
    """
    Odczytuje i deszyfruje zawartość pliku z hasłami.
    """
    if not os.path.exists(filename):
        return []

    with open(filename, "rb") as f:
        encrypted_data = f.read()

    if not encrypted_data:
        return []

    try:
        decrypted_data = fernet.decrypt(encrypted_data).decode("utf-8")
        return decrypted_data.splitlines()
    except Exception:
        return ["(błąd deszyfrowania lub uszkodzony plik)"]


def append_entry(fernet: Fernet, filename: str, new_line: str):
    """
    Dodaje nowy wpis do zaszyfrowanego pliku haseł.
    """
    entries = read_entries(fernet, filename)
    entries.append(new_line)
    data = "\n".join(entries).encode("utf-8")
    encrypted_data = fernet.encrypt(data)

    with open(filename, "wb") as f:
        f.write(encrypted_data)
