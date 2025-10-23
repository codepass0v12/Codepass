import os
import shutil
import zipfile
import subprocess
import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# ====================== KONFIGURACJA ======================

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC_DIR = os.path.join(PROJECT_DIR, "src")
DIST_DIR = os.path.join(PROJECT_DIR, "dist")
BUILD_DIR = os.path.join(PROJECT_DIR, "build_temp")

PRIVATE_KEY_PATH = os.path.join(PROJECT_DIR, "private_key.pem")
PUBLIC_KEY_PATH = os.path.join(PROJECT_DIR, "public_key.pem")
VERSION_FILE = os.path.join(PROJECT_DIR, "version.txt")
UPDATE_JSON = os.path.join(DIST_DIR, "update.json")

RELEASE_BASE_URL = "https://github.com/codepass0v12/Codepass/releases/download"

# ===========================================================


def read_version():
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def build_exe():
    """Buduje CodePass.exe z folderu src."""
    print("== 🔨 Budowanie CodePass.exe ==")
    subprocess.run([
        "pyinstaller",
        "--onefile",
        "--icon", os.path.join(PROJECT_DIR, "assets", "logo.ico"),
        "--name", "CodePass",
        os.path.join(SRC_DIR, "main.py")
    ], check=True)
    print("✅ Zbudowano EXE w folderze dist/")


def prepare_build_folder(version):
    """Kopiuje wymagane pliki do folderu tymczasowego."""
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR)

    include_files = [
        "src",          # cały kod
        "assets",       # grafiki, ikony
        "version.txt",  # wersja
        "dist/CodePass.exe"
    ]

    for item in include_files:
        src = os.path.join(PROJECT_DIR, item)
        if not os.path.exists(src):
            print(f"⚠️  Pomijam {src} (nie znaleziono)")
            continue
        dst = os.path.join(BUILD_DIR, os.path.basename(item))
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    print("📁 Skopiowano pliki do folderu tymczasowego.")


def create_zip(version):
    """Tworzy archiwum ZIP z aktualizacją."""
    os.makedirs(DIST_DIR, exist_ok=True)
    zip_path = os.path.join(DIST_DIR, f"update_{version}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(BUILD_DIR):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, BUILD_DIR)
                zipf.write(abs_path, rel_path)
    print(f"📦 Utworzono ZIP: {zip_path}")
    return zip_path


def sign_zip(zip_path):
    """Podpisuje ZIP przy użyciu klucza prywatnego."""
    with open(PRIVATE_KEY_PATH, "rb") as key_file:
        private_key = serialization.load_pem_private_key(key_file.read(), password=None)

    zip_data = open(zip_path, "rb").read()
    signature = private_key.sign(zip_data, padding.PKCS1v15(), hashes.SHA256())

    sig_path = zip_path.replace(".zip", ".sig")
    with open(sig_path, "wb") as f:
        f.write(signature)
    print(f"🔏 Podpisano ZIP → {sig_path}")
    return sig_path


def verify_signature(zip_path, sig_path):
    """Weryfikuje podpis ZIP."""
    with open(PUBLIC_KEY_PATH, "rb") as key_file:
        public_key = serialization.load_pem_public_key(key_file.read())

    zip_data = open(zip_path, "rb").read()
    signature = open(sig_path, "rb").read()
    try:
        public_key.verify(signature, zip_data, padding.PKCS1v15(), hashes.SHA256())
        print("✅ Weryfikacja podpisu OK.")
    except Exception as e:
        print(f"❌ Weryfikacja podpisu NIEUDANA: {e}")


def create_manifest(version, zip_path, sig_path):
    """Tworzy plik update.json."""
    zip_name = os.path.basename(zip_path)
    sig_name = os.path.basename(sig_path)
    manifest = {
        "version": version,
        "download_url": f"{RELEASE_BASE_URL}/v{version}/{zip_name}",
        "sig_url": f"{RELEASE_BASE_URL}/v{version}/{sig_name}"
    }
    with open(UPDATE_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)
    print(f"🧾 Zapisano update.json → {UPDATE_JSON}")


def open_dist_folder():
    """Otwiera folder dist w Eksploratorze."""
    try:
        subprocess.Popen(f'explorer "{DIST_DIR}"')
    except Exception:
        pass


def main():
    version = read_version()
    print(f"== Build CodePass v{version} ==")

    build_exe()
    prepare_build_folder(version)
    zip_path = create_zip(version)
    sig_path = sign_zip(zip_path)
    verify_signature(zip_path, sig_path)
    create_manifest(version, zip_path, sig_path)

    print("🎉 GOTOWE! Wszystkie pliki znajdują się w folderze dist/")
    open_dist_folder()


if __name__ == "__main__":
    main()
