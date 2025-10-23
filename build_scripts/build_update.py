import os
import sys
import shutil
import zipfile
import subprocess
import hashlib
import base64
import json
import time
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# ======================================
# KONFIGURACJA
# ======================================

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_DIR, "src")
DIST_DIR = os.path.join(PROJECT_DIR, "dist")
BUILD_DIR = os.path.join(PROJECT_DIR, "build")
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")

PRIVATE_KEY_PATH = os.path.join(PROJECT_DIR, "private_key.pem")
PUBLIC_KEY_PATH = os.path.join(PROJECT_DIR, "public_key.pem")
VERSION_PATH = os.path.join(PROJECT_DIR, "version.txt")

UPDATE_BASE_URL = "https://raw.githubusercontent.com/codepass0v12/Codepass/main/dist"

# ======================================
# FUNKCJE POMOCNICZE
# ======================================

def read_version():
    """Odczytuje aktualną wersję z version.txt."""
    if not os.path.exists(VERSION_PATH):
        raise FileNotFoundError(f"❌ Brak pliku version.txt w {VERSION_PATH}!")
    with open(VERSION_PATH, "r", encoding="utf-8") as f:
        return f.read().strip()


def set_version():
    """Pozwala wpisać wersję ręcznie, np. 2.1.0"""
    current = read_version()
    print(f"📄 Aktualna wersja: {current}")
    new_version = input("✏️  Podaj nową wersję (ENTER aby zostawić tę samą): ").strip()
    if not new_version:
        new_version = current
    with open(VERSION_PATH, "w", encoding="utf-8") as f:
        f.write(new_version)
    print(f"✅ Ustawiono wersję: {new_version}")
    return new_version


def prepare_build_folder(version: str):
    """Czyści i kopiuje źródła do folderu build/"""
    print(f"== 📦 Przygotowywanie build/ dla wersji {version} ==")
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR, exist_ok=True)

    for item in os.listdir(SRC_DIR):
        src_path = os.path.join(SRC_DIR, item)
        dst_path = os.path.join(BUILD_DIR, item)
        if os.path.isfile(src_path):
            shutil.copy2(src_path, dst_path)

    shutil.copy2(VERSION_PATH, BUILD_DIR)
    print("📂 Folder build/ gotowy.")


def build_exe():
    """Buduje CodePass.exe i czeka aż proces się zakończy."""
    print("== 🔨 Budowanie CodePass.exe ==")

    src_path = os.path.join(SRC_DIR, "main.py")
    icon_path = os.path.join(ASSETS_DIR, "logo.ico")

    if not os.path.exists(src_path):
        raise FileNotFoundError(f"❌ Nie znaleziono pliku: {src_path}")

    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        "--clean",
        "--paths", SRC_DIR,
        "--hidden-import=updater",
        "--hidden-import=winrt.windows.security.credentials.ui",
        "--hidden-import=winrt.windows.foundation",
        "--hidden-import=winrt.windows.security.credentials",
        "--name", "CodePass",
        "--icon", icon_path if os.path.exists(icon_path) else "NONE",
        src_path
    ]

    result = subprocess.run(pyinstaller_cmd)
    if result.returncode != 0:
        raise RuntimeError("❌ Błąd podczas kompilacji EXE.")

    exe_path = os.path.join(PROJECT_DIR, "dist", "CodePass.exe")
    for _ in range(10):
        if os.path.exists(exe_path):
            break
        print("⏳ Oczekiwanie na wygenerowanie EXE...")
        time.sleep(1)

    if not os.path.exists(exe_path):
        raise FileNotFoundError("❌ Nie znaleziono CodePass.exe po kompilacji!")

    print("✅ EXE zbudowany.")
    return exe_path


def create_zip(version: str) -> str:
    """Tworzy ZIP z plikami aplikacji i wymusza .zip."""
    os.makedirs(DIST_DIR, exist_ok=True)
    zip_name = f"update_{version}.zip"
    zip_path = os.path.join(DIST_DIR, zip_name)

    print(f"== 📦 Tworzenie {zip_name} ==")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for foldername, _, filenames in os.walk(BUILD_DIR):
            for filename in filenames:
                filepath = os.path.join(foldername, filename)
                relpath = os.path.relpath(filepath, BUILD_DIR)
                zipf.write(filepath, relpath)

    print(f"✅ Utworzono ZIP: {zip_path}")
    return zip_path


def sign_zip(zip_path: str) -> str:
    """Podpisuje ZIP przy użyciu klucza RSA."""
    sig_path = zip_path.replace(".zip", ".sig")
    print("🔏 Podpisywanie archiwum...")

    with open(PRIVATE_KEY_PATH, "rb") as key_file:
        private_key = serialization.load_pem_private_key(key_file.read(), password=None)
    with open(zip_path, "rb") as f:
        data = f.read()
    signature = private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())
    with open(sig_path, "wb") as sig_file:
        sig_file.write(signature)

    print(f"✅ Podpis zapisany jako: {sig_path}")
    return sig_path


def verify_signature(zip_path: str, sig_path: str):
    """Weryfikuje podpis ZIP."""
    print("🔍 Weryfikacja podpisu...")
    with open(PUBLIC_KEY_PATH, "rb") as key_file:
        public_key = serialization.load_pem_public_key(key_file.read())
    with open(zip_path, "rb") as f:
        data = f.read()
    with open(sig_path, "rb") as f:
        signature = f.read()
    public_key.verify(signature, data, padding.PKCS1v15(), hashes.SHA256())
    print("✅ Podpis ZIP poprawny.")


def create_manifest(version: str, zip_path: str, sig_path: str):
    """Tworzy plik update.json z pełnymi linkami."""
    print("📝 Tworzenie manifestu...")
    zip_name = os.path.basename(zip_path)
    sig_name = os.path.basename(sig_path)
    manifest = {
        "version": version,
        "timestamp": datetime.now().isoformat(),
        "download_url": f"{UPDATE_BASE_URL}/{zip_name}",
        "sig_url": f"{UPDATE_BASE_URL}/{sig_name}"
    }

    manifest_path = os.path.join(DIST_DIR, "update.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)
    print(f"✅ Manifest zapisany: {manifest_path}")
    return manifest_path


def git_push(version: str):
    """Wysyła build na GitHub."""
    print("🚀 Wysyłanie aktualizacji na GitHub...")

    cmds = [
        ["git", "add", "."],
        ["git", "commit", "-m", f"build: CodePass v{version}"],
        ["git", "push", "origin", "main"],
        ["git", "tag", f"v{version}"],
        ["git", "push", "--tags"]
    ]

    for cmd in cmds:
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"⚠️ Komenda nie powiodła się: {' '.join(cmd)}")
            break

    print("✅ Aktualizacja wysłana na GitHub.")


def open_dist_folder():
    """Otwiera folder dist w Eksploratorze."""
    try:
        subprocess.Popen(f'explorer "{DIST_DIR}"')
    except Exception:
        pass

# ======================================
# GŁÓWNY PROCES
# ======================================

def main():
    print("🚧 Uruchamianie procesu build CodePass...")

    version = set_version()
    print(f"== Build CodePass v{version} ==")

    build_exe()
    prepare_build_folder(version)
    zip_path = create_zip(version)
    sig_path = sign_zip(zip_path)
    verify_signature(zip_path, sig_path)
    create_manifest(version, zip_path, sig_path)

    choice = input("📦 Wysłać na GitHub? (ENTER = tak / n = tylko lokalnie): ").strip().lower()
    if choice != "n":
        git_push(version)
        print("✅ Wysłano nową wersję na GitHub.")
    else:
        print("🧪 Tryb testowy — pliki zostały zbudowane tylko lokalnie.")

    open_dist_folder()
    print(f"🎉 GOTOWE! CodePass v{version} zbudowany pomyślnie.")

if __name__ == "__main__":
    main()
