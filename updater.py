import os
import requests
import zipfile
import subprocess
from tkinter import messagebox
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


# ======================= 🔐 Klucz publiczny (RSA PEM) =======================
PUBLIC_KEY_PEM = b"""
-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAs3zRigkJ22weSHhiI+qk
k5pirPfGuuDrokQtxJSol7EKFcHUn5dkuhxa8PNVKpyiw5xZ5pSrFr/zQOlSlgmV
ogRLKO1KODzBYyRt24h7+46Ee/ngwrSAe6e14JZVLg5JMpu9nuBs+63vC0HqCijr
yi7WhRQg89mtW7v1JiS2zdtuilIbhX8IE9/QFpPLI92guCwEmgdDBkt8/MrIP4Cc
IG8HYdhWd3i9fk/SAFqmLwVi/Mngv8LFT1tAfQOb1E/IFgaton7SqIX7xJs8brza
ZQEqTZG3EQOjzSpwr6C79wfSfW2UY+uUIprrAUKd4UALPFOSFmBZyoMWvnHj1RKp
CJ4SiSWsn1C822pl9HagExfwch3st+/A5VXPvP02K1Eq5N++KzI9rYAB4ARsrQbd
bZMo7YJxjJN67OkNugHHHHuNgP/RlTG8lqQCEnO1A5PgRwdDW1ymgHrw2mZSZE2F
2hsCCBbFUN2n/RfGSNOLKqTDpWT2/CqAiJwEfAArwwwRhcH74Pi6dM8ohwWlkMbS
O1tl4fGYNhiLZ0BZkJIsJyV7ulFyrRb8FaVZEGqeiPxRka1IsiEHoKuSqHdEPnDV
Rh4JjXlJKN/D3ksNmFNWWEaaajxAUHZUvZbxud8fjbXKpezYlPvccvboyFr7ecY+
EHCGxjhG7qbUrvYhLdeQi8ECAwEAAQ==
-----END PUBLIC KEY-----
"""


# ======================= 🔎 Weryfikacja podpisu ZIP =======================

def verify_zip_signature(zip_bytes: bytes, signature_b64: str) -> bool:
    """
    Sprawdza podpis ZIP-a (RSA + SHA256).
    Zwraca True jeśli podpis jest poprawny.
    """
    try:
        public_key = serialization.load_pem_public_key(PUBLIC_KEY_PEM)
        signature = base64.b64decode(signature_b64)

        public_key.verify(
            signature,
            zip_bytes,
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        print("✅ Podpis ZIP-a poprawny.")
        return True
    except Exception as e:
        print("❌ Weryfikacja podpisu nie powiodła się:", e)
        return False


# ======================= 📄 Wersja lokalna =======================

def get_local_version():
    try:
        with open("version.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0"


# ======================= 🌐 Sprawdzanie aktualizacji =======================

def check_for_updates(current_version: str, manifest_url: str):
    try:
        response = requests.get(manifest_url)
        response.raise_for_status()
        manifest = response.json()
    except Exception as e:
        print(f"[Błąd sprawdzania aktualizacji] {e}")
        return None

    latest_version = manifest.get("version", "0.0")
    print(f"Aktualna wersja: {current_version}, dostępna: {latest_version}")

    if latest_version == current_version:
        print("[Aktualizacja] Aplikacja jest aktualna.")
        return None

    return manifest


# ======================= ⚙️ Instalacja aktualizacji =======================

def perform_update_flow(manifest: dict):
    version = manifest.get("version", "Nieznana")
    download_url = manifest.get("download_url")
    signature_url = manifest.get("signature_url")

    if not download_url or not signature_url:
        messagebox.showerror("Błąd", "Brak linków do aktualizacji lub podpisu.")
        return

    try:
        print(f"[Aktualizacja] Pobieranie wersji {version}...")

        # 📥 Pobierz ZIP
        zip_response = requests.get(download_url, stream=True)
        zip_response.raise_for_status()
        zip_bytes = zip_response.content

        # 📥 Pobierz podpis
        sig_response = requests.get(signature_url)
        sig_response.raise_for_status()
        signature_b64 = sig_response.text.strip()

        # ✅ Weryfikacja podpisu
        if not verify_zip_signature(zip_bytes, signature_b64):
            messagebox.showerror("Błąd bezpieczeństwa", "Podpis aktualizacji jest nieprawidłowy!")
            return

        # 💾 Zapisz ZIP tymczasowo
        zip_filename = f"update_{version}.zip"
        with open(zip_filename, "wb") as f:
            f.write(zip_bytes)

        # 📦 Rozpakuj
        with zipfile.ZipFile(zip_filename, "r") as zip_ref:
            zip_ref.extractall(".")
        os.remove(zip_filename)

        # ✍️ Zapisz nową wersję
        with open("version.txt", "w", encoding="utf-8") as vf:
            vf.write(version)

        messagebox.showinfo("Aktualizacja", f"Zaktualizowano do wersji {version}.")

        # 🔁 Restart aplikacji
        exe_path = os.path.abspath("CodePass.exe")
        if os.path.exists(exe_path):
            subprocess.Popen([exe_path])
            os._exit(0)

    except Exception as e:
        messagebox.showerror("Błąd aktualizacji", f"Nie udało się pobrać lub zainstalować aktualizacji:\n{e}")
        print(f"[Błąd aktualizacji] {e}")
