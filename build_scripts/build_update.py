import os
import json
import zipfile
import subprocess
from datetime import datetime

# ===================== 🔧 KONFIGURACJA =====================
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "src")
DIST_DIR = os.path.join(ROOT, "dist")
VERSION_FILE = os.path.join(ROOT, "version")
UPDATE_JSON = os.path.join(ROOT, "update.json")
REPO_NAME = "codepass0v12/Codepass"   # <-- zmień jeśli inne repo
# ============================================================

def read_version():
    """Odczytuje numer wersji z pliku version"""
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0"

def bump_version(version):
    """Zwiększa numer wersji (x.y -> x.(y+1))"""
    try:
        major, minor = version.split(".")
        return f"{major}.{int(minor)+1}"
    except:
        return "1.0"

def create_zip(version):
    """Tworzy paczkę update.zip z folderu src"""
    os.makedirs(DIST_DIR, exist_ok=True)
    zip_path = os.path.join(DIST_DIR, "update.zip")
    print("📦 Tworzenie paczki aktualizacji:", zip_path)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(SRC_DIR):
            for file in files:
                if file.endswith(".pyc") or "__pycache__" in root:
                    continue
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, SRC_DIR)
                zipf.write(filepath, arcname)
        # Dodaj plik version
        zipf.write(VERSION_FILE, "version.txt")

    print("✅ ZIP utworzony:", zip_path)
    return zip_path

def update_manifest(version, zip_url):
    """Aktualizuje plik update.json"""
    manifest = {
        "version": version,
        "download_url": zip_url
    }
    with open(UPDATE_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print("📝 Zaktualizowano update.json")

def git_push(version):
    """Tworzy commit, tag i wrzuca na GitHub"""
    print("🚀 Wysyłanie zmian na GitHub...")
    subprocess.run(["git", "add", "."], cwd=ROOT)
    subprocess.run(["git", "commit", "-m", f"🔄 Build {version}"], cwd=ROOT)
    subprocess.run(["git", "push"], cwd=ROOT)

    tag_name = f"v{version}"
    subprocess.run(["git", "tag", tag_name], cwd=ROOT)
    subprocess.run(["git", "push", "origin", tag_name], cwd=ROOT)
    print(f"🏷️ Utworzono tag {tag_name} i wysłano na GitHub.")

def create_release(version):
    """Tworzy GitHub Release z użyciem gh CLI"""
    print("📦 Tworzenie GitHub Release...")
    subprocess.run([
        "gh", "release", "create", f"v{version}",
        "dist/update.zip",
        "--title", f"CodePass {version}",
        "--notes", f"Automatyczna aktualizacja z {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
    ], cwd=ROOT)
    print("✅ Release utworzony na GitHubie!")

def main():
    print("=== 🧱 CodePass Build System (bez podpisu) ===")
    current_version = read_version()
    new_version = bump_version(current_version)
    print(f"📄 Aktualna wersja: {current_version} → Nowa wersja: {new_version}")

    # Aktualizuj plik version
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(new_version)

    # Tworzenie ZIP
    zip_path = create_zip(new_version)

    # Przygotowanie linku (GitHub Release)
    zip_url = f"https://github.com/{REPO_NAME}/releases/download/v{new_version}/update.zip"

    # Aktualizacja update.json
    update_manifest(new_version, zip_url)

    # Commit, push, tag
    git_push(new_version)

    # Release na GitHub
    create_release(new_version)

    print("\n🎉 Build zakończony sukcesem!")
    print(f"📁 Wersja {new_version} opublikowana z ZIP-em i update.json 🚀")

if __name__ == "__main__":
    main()
