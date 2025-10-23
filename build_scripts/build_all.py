import os
import shutil
import subprocess
import zipfile
import base64
import json
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


# 🔧 Ścieżki
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
ASSETS_DIR = os.path.join(ROOT_DIR, "assets")
DIST_DIR = os.path.join(ROOT_DIR, "dist")
BUILD_SCRIPT_DIR = os.path.join(ROOT_DIR, "build_scripts")

SPEC_FILE = os.path.join(BUILD_SCRIPT_DIR, "CodePass.spec")
VERSION_FILE = os.path.join(ROOT_DIR, "version.txt")
PRIVATE_KEY = os.path.join(ROOT_DIR, "private_key.pem")

# 🔹 Wczytanie wersji
def read_version():
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0.0"


# 🔹 Kompilacja EXE przy użyciu pliku .spec
def build_exe():
    print("== Budowanie CodePass.exe ==")
    os.makedirs(DIST_DIR, exist_ok=True)
    result = subprocess.run(
        ["pyinstaller", SPEC_FILE, "--clean"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("❌ Błąd podczas budowania EXE")
    print("✅ EXE zbudowane pomyślnie.")


# 🔹 Tworzenie ZIP-a z całym programem
def create_zip(version):
    print("📦 Tworzenie ZIP...")
    zip_path = os.path.join(DIST_DIR, f"update_{version}.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        # dodaj główne pliki
        for folder in ["src", "assets"]:
            folder_path = os.path.join(ROOT_DIR, folder)
            for root, _, files in os.walk(folder_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, ROOT_DIR)
                    zipf.write(full_path, rel_path)

        # dodaj inne pliki
        for file in ["version.txt", "update.json"]:
            full_path = os.path.join(ROOT_DIR, file)
            if os.path.exists(full_path):
                zipf.write(full_path, os.path.basename(full_path))

        # dodaj exe z dist
        exe_path = os.path.join(DIST_DIR, "CodePass", "CodePass.exe")
        if os.path.exists(exe_path):
            zipf.write(exe_path, "CodePass.exe")

    print(f"✅ ZIP zapisany: {zip_path}")
    return zip_path


# 🔹 Podpis ZIP-a kluczem prywatnym
def sign_zip(zip_path):
    print("🔑 Podpisywanie ZIP-a...")
    with open(PRIVATE_KEY, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)

    with open(zip_path, "rb") as f:
        zip_bytes = f.read()

    signature = private_key.sign(zip_bytes, padding.PKCS1v15(), hashes.SHA256())
    sig_b64 = base64.b64encode(signature)

    sig_path = zip_path.replace(".zip", ".sig")
    with open(sig_path, "wb") as f:
        f.write(signature)

    print(f"✅ Podpis zapisany: {sig_path}")
    return sig_path


# 🔹 Aktualizacja manifestu
def update_manifest(version):
    print("📝 Aktualizacja update.json...")
    manifest = {
        "version": version,
        "download_url": f"https://github.com/codepass0v12/Codepass/releases/download/v{version}/update_{version}.zip",
        "sig_url": f"https://github.com/codepass0v12/Codepass/releases/download/v{version}/update_{version}.sig",
        "timestamp": datetime.now().isoformat()
    }
    with open(os.path.join(DIST_DIR, "update.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print("✅ update.json zapisany.")


# 🔹 Główna logika
def main():
    version = read_version()
    print(f"== Budowanie CodePass v{version} ==")

    build_exe()
    zip_path = create_zip(version)
    sign_zip(zip_path)
    update_manifest(version)

    print("\n🎉 GOTOWE! Wszystko zbudowane i podpisane.")


if __name__ == "__main__":
    main()
