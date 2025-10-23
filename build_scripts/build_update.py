import os
import sys
import time
import shutil
import zipfile
import subprocess
import json
from datetime import datetime
from typing import Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# ======================================
# 📁 USTAWIENIA ŚCIEŻEK
# ======================================

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR     = os.path.join(PROJECT_DIR, "src")
BUILD_DIR   = os.path.join(PROJECT_DIR, "build")
DIST_DIR    = os.path.join(PROJECT_DIR, "dist")
ASSETS_DIR  = os.path.join(PROJECT_DIR, "assets")

PRIVATE_KEY_PATH = os.path.join(PROJECT_DIR, "private_key.pem")
PUBLIC_KEY_PATH  = os.path.join(PROJECT_DIR, "public_key.pem")
VERSION_PATH     = os.path.join(PROJECT_DIR, "version.txt")

UPDATE_BASE_URL = "https://raw.githubusercontent.com/codepass0v12/Codepass/main/dist"
GITHUB_REPO     = "codepass0v12/Codepass"

# ======================================
# 🔧 FUNKCJE POMOCNICZE
# ======================================

def ensure_dirs():
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)

def read_version() -> str:
    """Czyta aktualną wersję lub tworzy plik jeśli go nie ma."""
    if not os.path.exists(VERSION_PATH):
        with open(VERSION_PATH, "w", encoding="utf-8") as f:
            f.write("1.0.0")
        print("ℹ️  Utworzono version.txt z wersją 1.0.0")
    with open(VERSION_PATH, "r", encoding="utf-8") as f:
        return f.read().strip()

def bump_version() -> str:
    """Zwiększa numer wersji o +0.0.1"""
    ver = read_version()
    major, minor, patch = map(int, ver.split("."))
    patch += 1
    new_ver = f"{major}.{minor}.{patch}"
    with open(VERSION_PATH, "w", encoding="utf-8") as f:
        f.write(new_ver)
    print(f"⬆️  Wersja: {ver} → {new_ver}")
    return new_ver

def run(cmd: list, cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    """Uruchamia polecenie i zwraca wynik."""
    print("▶", " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)

# ======================================
# 🧱 BUDOWANIE EXE
# ======================================

def ensure_pyinstaller():
    """Instaluje PyInstaller jeśli brak."""
    res = run([sys.executable, "-m", "pip", "show", "pyinstaller"])
    if res.returncode != 0:
        print("ℹ️  Instaluję PyInstaller...")
        install = run([sys.executable, "-m", "pip", "install", "-U", "pyinstaller"])
        if install.returncode != 0:
            print(install.stderr)
            raise RuntimeError("Nie udało się zainstalować PyInstaller.")

def wait_for_exe(exe_path: str, timeout: int = 180, stable_checks: int = 3):
    """Czeka aż EXE się pojawi i ustabilizuje rozmiar."""
    print(f"⏳ Oczekiwanie na {exe_path} (do {timeout}s)...")
    last_size = -1
    stable = 0
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(exe_path):
            try:
                size = os.path.getsize(exe_path)
                if size == last_size:
                    stable += 1
                    if stable >= stable_checks:
                        print("✅ EXE gotowe.")
                        return
                else:
                    stable = 0
                    last_size = size
            except Exception:
                pass
        time.sleep(1)
    raise TimeoutError(f"Nie udało się zbudować {exe_path} w czasie {timeout}s")

def build_exe() -> str:
    """Buduje CodePass.exe i czeka aż będzie gotowy."""
    ensure_pyinstaller()

    src_path = os.path.join(SRC_DIR, "main.py")
    icon_path = os.path.join(ASSETS_DIR, "logo.ico")
    exe_path = os.path.join(DIST_DIR, "CodePass.exe")

    if not os.path.exists(src_path):
        raise FileNotFoundError(f"❌ Brak pliku źródłowego: {src_path}")

    if os.path.exists(exe_path):
        try:
            os.remove(exe_path)
        except Exception:
            pass

    print("== 🔨 Budowanie CodePass.exe ==")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        "--clean",
        "--name", "CodePass",
        "--hidden-import=winrt.windows.security.credentials.ui",
        "--hidden-import=winrt.windows.foundation",
        "--hidden-import=winrt.windows.security.credentials"
    ]
    if os.path.exists(icon_path):
        cmd += ["--icon", icon_path]
    cmd += [src_path]

    result = run(cmd, cwd=PROJECT_DIR)
    if result.returncode != 0:
        print("❌ Błąd PyInstaller:")
        print(result.stderr)
        raise RuntimeError("Kompilacja nie powiodła się.")

    wait_for_exe(exe_path)
    print(f"✅ Utworzono {exe_path}")
    return exe_path

# ======================================
# 📦 PACZKOWANIE I PODPIS
# ======================================

def prepare_build_folder(version: str):
    """Czyści folder build/ i kopiuje pliki źródłowe."""
    print(f"== 📦 Przygotowywanie build ({version}) ==")

    # 🛑 Ochrona przed przypadkowym usunięciem src/
    if os.path.abspath(BUILD_DIR) == os.path.abspath(SRC_DIR):
        raise RuntimeError("BŁĄD: BUILD_DIR wskazuje na SRC_DIR!")

    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR, exist_ok=True)

    for name in os.listdir(SRC_DIR):
        src = os.path.join(SRC_DIR, name)
        dst = os.path.join(BUILD_DIR, name)
        if os.path.isfile(src):
            shutil.copy2(src, dst)

    shutil.copy2(VERSION_PATH, BUILD_DIR)
    print("📁 build/ gotowy.")

def create_zip(version: str) -> str:
    zip_path = os.path.join(DIST_DIR, f"update_{version}.zip")
    print(f"== 📦 Tworzenie ZIP: {zip_path} ==")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(BUILD_DIR):
            for f in files:
                ap = os.path.join(root, f)
                rp = os.path.relpath(ap, BUILD_DIR)
                zipf.write(ap, rp)
    print("✅ ZIP utworzony.")
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
    print(f"✅ Podpis zapisany jako {sig_path}")
    return sig_path

def verify_signature(zip_path: str, sig_path: str):
    print("🔍 Weryfikacja podpisu...")
    with open(PUBLIC_KEY_PATH, "rb") as key_file:
        public_key = serialization.load_pem_public_key(key_file.read())
    with open(zip_path, "rb") as f:
        data = f.read()
    with open(sig_path, "rb") as f:
        signature = f.read()
    public_key.verify(signature, data, padding.PKCS1v15(), hashes.SHA256())
    print("✅ Podpis poprawny.")

def create_manifest(version: str, zip_path: str, sig_path: str) -> str:
    print("📝 Tworzenie update.json...")
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
    print(f"✅ Zapisano manifest: {manifest_path}")
    return manifest_path

# ======================================
# 🧭 GIT PUSH
# ======================================

def git_push(version: str):
    print("🚀 Wysyłanie na GitHub...")
    cmds = [
        ["git", "add", "."],
        ["git", "commit", "-m", f"build: CodePass v{version}"],
        ["git", "push", "origin", "main"],
        ["git", "tag", f"v{version}"],
        ["git", "push", "--tags"]
    ]
    for cmd in cmds:
        res = run(cmd, cwd=PROJECT_DIR)
        if res.returncode != 0:
            if "nothing to commit" in (res.stdout + res.stderr).lower():
                continue
            print("⚠️ Błąd:", res.stderr or res.stdout)
            break
    print("✅ Wysłano nową wersję.")

# ======================================
# 🚀 GŁÓWNY PROCES
# ======================================

def main():
    ensure_dirs()
    version = bump_version()
    print(f"== Build CodePass v{version} ==")

    build_exe()
    prepare_build_folder(version)
    zip_path = create_zip(version)
    sig_path = sign_zip(zip_path)
    verify_signature(zip_path, sig_path)
    create_manifest(version, zip_path, sig_path)
    git_push(version)

    try:
        subprocess.Popen(['explorer', DIST_DIR])
    except Exception:
        pass

    print("🎉 GOTOWE! Wszystkie pliki znajdują się w:", DIST_DIR)

if __name__ == "__main__":
    main()
