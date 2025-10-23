import os
import base64
from cryptography.fernet import Fernet
import win32crypt  # Windows DPAPI

KEY_FILE = "key.enc"

# ======================== 🔐 Klucz szyfrowania ========================

def load_or_create_fernet() -> Fernet:
    """
    Tworzy lub wczytuje klucz szyfrowania Fernet,
    zabezpieczony systemowo (DPAPI - przypisany do konta Windows).
    """
    try:
        if os.path.exists(KEY_FILE):
            with open(KEY_FILE, "rb") as f:
                encrypted_key = f.read()
            if not encrypted_key:
                raise ValueError("Plik key.enc pusty.")
            decrypted = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
            return Fernet(decrypted)
    except Exception as e:
        print(f"[Błąd klucza] {e} — generowanie nowego klucza.")

    # Tworzymy nowy klucz, jeśli nie udało się wczytać
    key = Fernet.generate_key()
    protected = win32crypt.CryptProtectData(key, None, None, None, None, 0)
    with open(KEY_FILE, "wb") as f:
        f.write(protected)
    return Fernet(key)

# ======================== 📂 Plik z hasłami ========================

def read_entries(fernet: Fernet, filename: str) -> list:
    """
    Odczytuje zaszyfrowany plik z hasłami (Hasła.enc).
    Zwraca listę wpisów lub pustą listę, jeśli plik nie istnieje.
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
    except Exception as e:
        print(f"[Błąd deszyfrowania] {e}")
        return ["(błąd deszyfrowania lub uszkodzony plik)"]

def append_entry(fernet: Fernet, filename: str, new_line: str):
    """
    Dodaje nowy wpis do pliku Hasła.enc.
    Wszystkie dane są szyfrowane w całości przy każdym zapisie.
    """
    entries = read_entries(fernet, filename)
    entries.append(new_line)
    data = "\n".join(entries).encode("utf-8")
    encrypted_data = fernet.encrypt(data)

    with open(filename, "wb") as f:
        f.write(encrypted_data)
