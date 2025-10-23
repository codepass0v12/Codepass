import os
import sys
import shutil
import zipfile
import subprocess
import json
from datetime import datetime
from time import sleep
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# ======================================
# KONFIGURACJA
# ======================================

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_DIR, "src")
DIST_DIR = os.path.join(PROJECT_DIR, "dist")
BUILD_DIR = os.path.join(PROJECT_DIR, "build_temp")  # nie ruszamy src
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")

PRIVATE_KEY_PATH = os.path.join(PROJECT_DIR, "private_key.pem")
PUBLIC_KEY_PATH = os.path.join(PROJECT_DIR, "public_key.pem")
VERSION_PATH = os.path.join(PROJECT_DIR, "version.txt")

UPDATE_BASE_URL = "https://raw.githubusercontent.com/codepass0v12/Codepass/main/dist"
GITHUB_REPO = "codepass0v12/Codepass"

# ======================================
# FUNKCJE POMOCNICZE
# ======================================

def read_version() -> str:
    if not os.path.exists(VERSION_PATH):
        raise FileNotFoundError("Brak pliku version.txt!")
    with open(VERSION_PATH, "r", encoding="utf-8") as f:
        return f.read().strip()

def set_version(version: str):
    with open(VERSION_PATH, "w", encoding="utf-8") as f:
        f.write(version.strip())

def ask_version():
    current = read_version()
    print(f"📦 Aktualna wersja: {current}")
    new_version = input("🔹 Podaj nową wersję (ENTER = zostaw bez zmian): ").strip()
    if not new_version:
        return current
    set_version(new_version)
    print(f"✅ Zmieniono wersję: {current} → {new_version}")
    return new_version

def safe_prepare_build(version: str):
    """Tworzy tymczasowy folder build_temp bez usuwania źródeł."""
    print(f"== 📂 Przygotowywanie build_temp dla wersji {version} ==")
    os.makedirs(BUILD_DIR, exist_ok=True)

    # Kopiujemy pliki ze src (ale nie usuwamy oryginałów!)
    for foldername, _, filenames in os.walk(SRC_DIR):
        for filename in filenames:
            src = os.path.join(foldername, filename)
            rel = os.path.relpath(src, SRC_DIR)
            dst = os.path.join(BUILD_DIR, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)

    shutil.copy2(VERSION_PATH, BUILD_DIR)
    print("✅ Folder build_temp gotowy.")

def create_zip(version: str) -> str:
    os.makedirs(DIST_DIR, exist_ok=True)
    zip_path = os.path.join(DIST_DIR, f"update_{version}.zip")

    print(f"== 📦 Tworzenie {zip_path} ==")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for foldername, _, filenames in os.walk(BUILD_DIR):
            for filename in filenames:
                filepath = os.path.join(foldername, filename)
                relpath = os.path.relpath(filepath, BUILD_DIR)
                zipf.write(filepath, relpath)
    print("✅ ZIP gotowy.")
    return zip_path

def sign_zip(zip_path: str) -> str:
    sig_path = zip_path.replace(".zip", ".sig")
    print("🔏 Podpisywanie ZIP...")
    with open(PRIVATE_KEY_PATH, "rb") as key_file:
        private_key = serialization.load_pem_private_key(key_file.read(), password=None)
    with open(zip_path, "rb") as f:
        data = f.read()
    signature = private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())
    with open(sig_path, "wb") as f:
        f.write(signature)
    print(f"✅ Podpis zapisany: {sig_path}")
    return sig_path

def verify_signature(zip_path: str, sig_path: str):
    with open(PUBLIC_KEY_PATH, "rb") as key_file:
        public_key = serialization.load_pem_public_key(key_file.read())
    with open(zip_path, "rb") as f:
        data = f.read()
    with open(sig_path, "rb") as f:
        signature = f.read()
    public_key.verify(signature, data, padding.PKCS1v15(), hashes.SHA256())
    print("✅ Weryfikacja podpisu OK.")

def create_manifest(version: str, zip_path: str, sig_path: str):
    manifest = {
        "version": version,
        "timestamp": datetime.now().isoformat(),
        "download_url": f"{UPDATE_BASE_URL}/{os.path.basename(zip_path)}",
        "sig_url": f"{UPDATE_BASE_URL}/{os.path.basename(sig_path)}"
    }
    manifest_path = os.path.join(DIST_DIR, "update.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)
    print(f"✅ Manifest utworzony: {manifest_path}")
    return manifest_path

def build_exe():
    """Buduje plik CodePass.exe"""
    print("🔨 Budowanie CodePass.exe...")
    src_path = os.path.join(SRC_DIR, "main.py")
    icon_path = os.path.join(ASSETS_DIR, "logo.ico")

    cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        "--clean",
        "--name", "CodePass",
        "--hidden-import=winrt.windows.security.credentials.ui",
        "--hidden-import=winrt.windows.foundation",
        "--hidden-import=winrt.windows.security.credentials",
        "--icon", icon_path if os.path.exists(icon_path) else "NONE",
        src_path
    ]

    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError("❌ Błąd podczas kompilacji EXE.")
    print("✅ CodePass.exe zbudowany.")
    sleep(2)

def git_push_and_release(version: str):
    """Commituje, taguje i publikuje release na GitHubie."""
    print("🚀 Publikowanie aktualizacji na GitHub...")

    subprocess.run(["git", "add", "."], check=False)
    subprocess.run(["git", "commit", "-m", f"build: CodePass v{version}"], check=False)
    subprocess.run(["git", "push", "origin", "main"], check=False)

    subprocess.run(["git", "tag", f"v{version}"], check=False)
    subprocess.run(["git", "push", "--tags"], check=False)

    # Automatyczny release (jeśli masz zainstalowany `gh`)
    gh_status = subprocess.run(["gh", "--version"], capture_output=True, text=True)
    if gh_status.returncode == 0:
        print("📦 Tworzenie release na GitHubie...")
        subprocess.run([
            "gh", "release", "create", f"v{version}",
            os.path.join(DIST_DIR, f"update_{version}.zip"),
            os.path.join(DIST_DIR, f"update_{version}.sig"),
            os.path.join(DIST_DIR, "update.json"),
            "--notes", f"Automatycznie zbudowana wersja CodePass v{version}"
        ])
    else:
        print("⚠️ GitHub CLI (gh) nie jest dostępny – pomiń release.")

def open_dist_folder():
    try:
        subprocess.Popen(f'explorer "{DIST_DIR}"')
    except Exception:
        pass

# ======================================
# GŁÓWNY PROCES
# ======================================

def main():
    print("=== 🧱 CodePass Builder ===")
    version = ask_version()

    build_exe()
    safe_prepare_build(version)
    zip_path = create_zip(version)
    sig_path = sign_zip(zip_path)
    verify_signature(zip_path, sig_path)
    create_manifest(version, zip_path, sig_path)

    git_push_and_release(version)

    open_dist_folder()
    print(f"🎉 GOTOWE! CodePass v{version} zbudowany pomyślnie.")

if __name__ == "__main__":
    main()
