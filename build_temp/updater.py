import os
import sys
import json
import base64
import zipfile
import tempfile
import requests
import subprocess
from tkinter import messagebox
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# =======================================
# 🔑 Publiczny klucz RSA do weryfikacji podpisu
# =======================================
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

# =======================================
# 🔒 Weryfikacja podpisu ZIP
# =======================================
def verify_zip_signature(zip_bytes: bytes, signature_b64: str) -> bool:
    try:
        public_key = serialization.load_pem_public_key(PUBLIC_KEY_PEM)
        signature = base64.b64decode(signature_b64)
        public_key.verify(signature, zip_bytes, padding.PKCS1v15(), hashes.SHA256())
        print("✅ Weryfikacja podpisu ZIP OK.")
        return True
    except Exception as e:
        print(f"❌ Weryfikacja podpisu nie powiodła się: {e}")
        return False


# =======================================
# 📄 Wersja lokalna aplikacji
# =======================================
def get_local_version():
    try:
        with open("version.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0"


# =======================================
# 🌐 Sprawdzanie aktualizacji
# =======================================
def check_for_updates(current_version: str, manifest_url: str):
    try:
        response = requests.get(manifest_url, timeout=10)
        response.raise_for_status()
        manifest = response.json()
    except Exception as e:
        print(f"[Błąd aktualizacji] Nie udało się pobrać manifestu: {e}")
        return None

    latest_version = manifest.get("version", "0.0")
    print(f"[Aktualizacja] Lokalna: {current_version}, najnowsza: {latest_version}")

    if latest_version == current_version:
        print("[Aktualizacja] Brak nowych wersji.")
        return None
    return manifest


# =======================================
# ⚙️ Instalacja aktualizacji
# =======================================
def perform_update_flow(manifest: dict):
    version = manifest.get("version", "Nieznana")
    download_url = manifest.get("download_url")
    sig_url = manifest.get("sig_url")

    if not download_url:
        messagebox.showerror("Błąd", "Nie znaleziono linku do aktualizacji w manifest.json.")
        return

    try:
        print(f"[Aktualizacja] Pobieranie wersji {version} z {download_url}...")
        zip_data = requests.get(download_url, timeout=30).content

        # 🔐 Weryfikacja podpisu
        if sig_url:
            print("[Aktualizacja] Sprawdzanie podpisu...")
            sig_data = requests.get(sig_url, timeout=10).content
            sig_b64 = base64.b64encode(sig_data).decode()
            if not verify_zip_signature(zip_data, sig_b64):
                messagebox.showerror("Błąd", "Niepoprawny podpis aktualizacji. Anulowano.")
                return

        # 🧩 Przygotowanie katalogów
        app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        tmp_dir = os.path.join(tempfile.gettempdir(), f"CodePass_Update_{version}")
        os.makedirs(tmp_dir, exist_ok=True)
        zip_path = os.path.join(tmp_dir, f"update_{version}.zip")

        # 📦 Zapisanie ZIP
        with open(zip_path, "wb") as f:
            f.write(zip_data)

        # 📂 Rozpakowanie ZIP
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(tmp_dir)
        os.remove(zip_path)

        # 🔄 Podmiana plików
        print("[Aktualizacja] Kopiowanie plików...")
        for root_dir, _, files in os.walk(tmp_dir):
            for file in files:
                src = os.path.join(root_dir, file)
                rel_path = os.path.relpath(src, tmp_dir)
                dst = os.path.join(app_dir, rel_path)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                try:
                    if os.path.exists(dst):
                        os.remove(dst)
                    shutil.move(src, dst)
                except PermissionError:
                    print(f"⚠️ Brak dostępu do pliku: {dst}")
                except Exception as e:
                    print(f"⚠️ Błąd kopiowania {dst}: {e}")

        # 🧹 Sprzątanie
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass

        # ✍️ Zapis nowej wersji
        with open(os.path.join(app_dir, "version.txt"), "w", encoding="utf-8") as vf:
            vf.write(version)

        messagebox.showinfo("Aktualizacja", f"Pomyślnie zaktualizowano do wersji {version}!")

        # 🚀 Restart aplikacji
        exe_path = os.path.join(app_dir, os.path.basename(sys.argv[0]))

        # 🔓 Usunięcie blokady Windows (jeśli EXE pochodzi z internetu)
        try:
            subprocess.run(["powershell", "Unblock-File", exe_path], check=False)
        except Exception:
            pass

        # 🔁 Uruchom ponownie
        try:
            subprocess.Popen([exe_path])
            os._exit(0)
        except Exception as e:
            messagebox.showwarning(
                "Restart",
                f"Nie udało się uruchomić aplikacji automatycznie:\n{e}\n"
                "Uruchom CodePass.exe ręcznie z folderu instalacji."
            )

    except Exception as e:
        messagebox.showerror("Błąd aktualizacji", f"Nie udało się przeprowadzić aktualizacji:\n{e}")
        print(f"[Błąd aktualizacji] {e}")
