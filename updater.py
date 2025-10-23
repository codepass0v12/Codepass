import os
import sys
import json
import zipfile
import requests
from tkinter import Tk, messagebox
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# =========================================
# KONFIGURACJA
# =========================================
APP_NAME = "CodePass"
VERSION_FILE = "version.txt"
MANIFEST_URL = "https://raw.githubusercontent.com/codepass0v12/Codepass/main/update.json"
PUBLIC_KEY_PATH = "public_key.pem"
UPDATE_FOLDER = os.getcwd()


# =========================================
# FUNKCJE POMOCNICZE
# =========================================
def get_local_version() -> str:
    if not os.path.exists(VERSION_FILE):
        return "0.0"
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def save_local_version(version: str):
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(version.strip())


def get_manifest() -> dict:
    try:
        r = requests.get(MANIFEST_URL, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[Błąd pobierania manifestu] {e}")
        return None


def verify_signature(file_path: str, sig_path: str) -> bool:
    try:
        with open(PUBLIC_KEY_PATH, "rb") as f:
            pub = serialization.load_pem_public_key(f.read())
        with open(file_path, "rb") as f:
            data = f.read()
        with open(sig_path, "rb") as f:
            sig = f.read()

        pub.verify(sig, data, padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception as e:
        print("❌ Weryfikacja podpisu nie powiodła się:", e)
        return False
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def decrypt_update(enc_path: str, key_path: str, out_path: str):
    """
    Odszyfrowuje pobrany plik ZIP z aktualizacją.
    """
    try:
        # Wczytaj prywatny klucz (do odszyfrowania AES)
        with open("private_key.pem", "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)

        # Wczytaj zaszyfrowany klucz AES
        with open(key_path, "rb") as f:
            encrypted_key = f.read()

        aes_key = private_key.decrypt(encrypted_key, padding.PKCS1v15())

        # Odszyfrowanie danych ZIP
        with open(enc_path, "rb") as f:
            iv = f.read(16)
            encrypted_data = f.read()

        cipher = Cipher(algorithms.AES(aes_key), modes.CFB(iv))
        decryptor = cipher.decryptor()
        data = decryptor.update(encrypted_data) + decryptor.finalize()

        with open(out_path, "wb") as f:
            f.write(data)

        return True

    except Exception as e:
        messagebox.showerror("Błąd aktualizacji", f"Nie udało się odszyfrować pliku:\n{e}")
        return False


def download_file(url: str, out_path: str):
    r = requests.get(url, stream=True, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)


def apply_update_zip(zip_path: str, version: str):
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(UPDATE_FOLDER)
        save_local_version(version)
        messagebox.showinfo("Aktualizacja", f"Pomyślnie zaktualizowano do wersji {version}")
    except Exception as e:
        messagebox.showerror("Błąd aktualizacji", f"Nie udało się rozpakować aktualizacji:\n{e}")


# =========================================
# GŁÓWNY MECHANIZM AKTUALIZACJI
# =========================================
def check_for_updates(auto_check: bool = False):
    """
    auto_check=True — uruchamiane przy starcie programu (bez konieczności klikania)
    """
    manifest = get_manifest()
    if not manifest:
        return

    current_version = get_local_version()
    remote_version = manifest.get("version", "0.0")
    zip_url = manifest.get("download_url")
    sig_url = manifest.get("sig_url")

    if not zip_url or not sig_url:
        if not auto_check:
            messagebox.showerror("Błąd", "Manifest nie zawiera linków do plików aktualizacji.")
        return

    if remote_version == current_version:
        print("[Aktualizacja] Aplikacja jest aktualna.")
        return

    # zapytaj użytkownika tylko raz przy starcie
    if messagebox.askyesno(
        "Nowa wersja dostępna",
        f"Dostępna wersja {remote_version}.\nCzy chcesz zaktualizować teraz?"
    ):
        perform_update(remote_version, zip_url, sig_url)


def perform_update(version: str, zip_url: str, sig_url: str):
    temp_zip = "update_temp.zip"
    temp_sig = "update_temp.zip.sig"

    try:
        messagebox.showinfo("Aktualizacja", "Pobieranie aktualizacji...")
        download_file(zip_url, temp_zip)
        download_file(sig_url, temp_sig)

        if not verify_signature(temp_zip, temp_sig):
            messagebox.showerror("Błąd aktualizacji", "Niepoprawny podpis — plik może być uszkodzony.")
            os.remove(temp_zip)
            os.remove(temp_sig)
            return

        # zamiast apply_update_zip(temp_zip, version)
        # daj to:

        if not decrypt_update(temp_zip, temp_zip + ".key", "update_decoded.zip"):
            return

        apply_update_zip("update_decoded.zip", version)
        os.remove("update_decoded.zip")

        os.remove(temp_zip)
        os.remove(temp_sig)

        messagebox.showinfo("Aktualizacja", "Aplikacja została zaktualizowana. Uruchom ponownie program.")
        sys.exit(0)

    except Exception as e:
        messagebox.showerror("Błąd aktualizacji", f"Wystąpił problem:\n{e}")
        for f in (temp_zip, temp_sig):
            if os.path.exists(f):
                os.remove(f)


# =========================================
# AUTOMATYCZNE SPRAWDZENIE AKTUALIZACJI PRZY STARCIE
# =========================================
def auto_update_check():
    try:
        root = Tk()
        root.withdraw()
        check_for_updates(auto_check=True)
        root.destroy()
    except Exception as e:
        print(f"[Błąd auto-aktualizacji] {e}")


if __name__ == "__main__":
    auto_update_check()
