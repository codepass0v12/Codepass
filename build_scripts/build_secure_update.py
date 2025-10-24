import os
import sys
import json
import zipfile
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# crypto
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


# ========================================
#  ŚCIEŻKI / KONFIG
# ========================================

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_DIR  = SCRIPT_DIR.parent

SRC_DIR      = PROJECT_DIR / "src"
ASSETS_DIR   = PROJECT_DIR / "assets"
KEYS_DIR     = PROJECT_DIR / "Keys"
DIST_DIR     = PROJECT_DIR / "dist"

MAIN_PY      = SRC_DIR / "main.py"
ICON_ICO     = ASSETS_DIR / "codepass.ico"

PRIVATE_KEY  = KEYS_DIR / "private_key.pem"
PUBLIC_KEY   = KEYS_DIR / "public_key.pem"

# wersja – preferuj root/version.txt, fallback: src/version.txt
VERSION_TXT_ROOT = PROJECT_DIR / "version.txt"
VERSION_TXT_SRC  = SRC_DIR / "version.txt"

APP_NAME     = "CodePass"
EXE_NAME     = "CodePass.exe"
RAW_BASE     = "https://raw.githubusercontent.com/codepass0v12/Codepass/main/dist"


# ========================================
#  UTILS
# ========================================

from typing import List, Optional  # dodaj na górze pliku, jeśli jeszcze nie ma

def run(cmd: List[str], check: bool = True, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:

    """Uruchamia proces i ładnie drukuje komendę + obsługuje błędy."""
    print("▶", " ".join(f'"{c}"' if " " in c else c for c in cmd))
    return subprocess.run(cmd, check=check, cwd=str(cwd) if cwd else None)

def ensure_paths():
    missing = []
    if not SRC_DIR.exists():      missing.append(str(SRC_DIR))
    if not MAIN_PY.exists():      missing.append(str(MAIN_PY))
    if not ASSETS_DIR.exists():   print("ℹ️  Ostrzeżenie: brak folderu assets (ikona opcjonalna).")
    if not KEYS_DIR.exists():     missing.append(str(KEYS_DIR))
    if not PRIVATE_KEY.exists():  missing.append(str(PRIVATE_KEY))
    if not PUBLIC_KEY.exists():   missing.append(str(PUBLIC_KEY))
    if missing:
        raise FileNotFoundError("Brakuje wymaganych ścieżek/plików:\n- " + "\n- ".join(missing))
    DIST_DIR.mkdir(parents=True, exist_ok=True)

def get_version() -> str:
    """Czyta wersję (root/version.txt lub src/version.txt), jeśli brak – tworzy '1.0.0' w root."""
    if VERSION_TXT_ROOT.exists():
        return VERSION_TXT_ROOT.read_text(encoding="utf-8").strip()
    if VERSION_TXT_SRC.exists():
        return VERSION_TXT_SRC.read_text(encoding="utf-8").strip()
    VERSION_TXT_ROOT.write_text("1.0.0", encoding="utf-8")
    return "1.0.0"

def set_version(ver: str) -> None:
    """Ustawia wersję spójnie (root + src jeśli istnieje)."""
    VERSION_TXT_ROOT.write_text(ver, encoding="utf-8")
    if VERSION_TXT_SRC.parent.exists():
        VERSION_TXT_SRC.write_text(ver, encoding="utf-8")

def check_tools():
    # Python/nuitka
    try:
        run([sys.executable, "-m", "nuitka", "--version"], check=True)
    except Exception as e:
        raise RuntimeError(
            "Nuitka nie jest dostępna w tym interpreterze.\n"
            "Zainstaluj w aktywnym .venv:  pip install nuitka pillow zstandard ordered-set\n"
            f"Szczegóły: {e}"
        )

    # git
    try:
        run(["git", "--version"], check=True)
    except Exception as e:
        print("⚠️  Ostrzeżenie: git nie jest dostępny w PATH (pomijam automatyczny push).", e)

    # gh (opcjonalne)
    try:
        run(["gh", "--version"], check=True)
    except Exception:
        print("ℹ️  gh (GitHub CLI) nie wykryty – publikacja Release będzie pominięta (opcjonalna).")


# ========================================
#  BUILD EXE (Nuitka)
# ========================================

def build_exe(version: str) -> Path:
    """Kompiluje CodePass.exe do dist/ za pomocą Nuitka."""
    ensure_paths()
    check_tools()

    out_exe = DIST_DIR / EXE_NAME
    print(f"🔨 Kompilacja {APP_NAME} v{version} przez Nuitka...")

    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--windows-console-mode=disable",
        "--enable-plugin=tk-inter",
        f'--include-data-file={PUBLIC_KEY}={PUBLIC_KEY.name}',
        f'--include-data-dir={ASSETS_DIR}=assets',
        f'--output-filename={EXE_NAME}',
        f'--output-dir={DIST_DIR}',
        str(MAIN_PY)
    ]

    # Ikona – tylko jeśli istnieje
    if ICON_ICO.exists():
        cmd.insert(-1, f'--windows-icon-from-ico={ICON_ICO}')
    else:
        print("ℹ️  Brak ikony assets/codepass.ico – pominę.")

    run(cmd, check=True, cwd=PROJECT_DIR)
    if not out_exe.exists():
        raise RuntimeError("Kompilacja powiodła się, ale nie znaleziono wynikowego EXE.")
    print(f"✅ Utworzono {out_exe}")
    return out_exe


# ========================================
#  PAKOWANIE + PODPIS
# ========================================

def create_zip(version: str, exe_path: Path) -> Path:
    """Tworzy dist/update_<ver>.zip z CodePass.exe + version.txt."""
    ensure_paths()
    zip_path = DIST_DIR / f"update_{version}.zip"
    print("📦 Tworzenie paczki aktualizacji...")

    # zawsze zaktualizuj version.txt przed spakowaniem
    set_version(version)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(exe_path, exe_path.name)
        # dołączamy version.txt, by updater mógł go nadpisać lokalnie
        z.write(VERSION_TXT_ROOT, "version.txt")

    print(f"✅ Paczka: {zip_path}")
    return zip_path

def sign_and_verify(zip_path: Path) -> Path:
    """Podpisuje ZIP prywatnym kluczem i natychmiast weryfikuje podpis kluczem publicznym."""
    ensure_paths()
    sig_path = zip_path.with_suffix(".sig")
    print("🔏 Podpisywanie aktualizacji...")

    private_key = serialization.load_pem_private_key(
        PRIVATE_KEY.read_bytes(),
        password=None,
    )
    data = zip_path.read_bytes()
    signature = private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())
    sig_path.write_bytes(signature)
    print(f"✅ Podpis zapisany: {sig_path}")

    # Weryfikacja
    print("🔍 Weryfikacja podpisu...")
    public_key = serialization.load_pem_public_key(PUBLIC_KEY.read_bytes())
    public_key.verify(signature, data, padding.PKCS1v15(), hashes.SHA256())
    print("✅ Podpis poprawny.")
    return sig_path


# ========================================
#  MANIFEST
# ========================================

def write_update_json(version: str, zip_path: Path, sig_path: Path, exe_path: Path) -> Path:
    """Zapisuje dist/update.json z linkami RAW do GitHuba."""
    update_json = {
        "version": version,
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "download_url": f"{RAW_BASE}/{zip_path.name}",
        "sig_url": f"{RAW_BASE}/{sig_path.name}",
        "exe_url": f"{RAW_BASE}/{exe_path.name}"
    }
    out = DIST_DIR / "update.json"
    out.write_text(json.dumps(update_json, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"📝 Zapisano manifest: {out}")
    return out


# ========================================
#  GIT / GH (opcjonalnie)
# ========================================

def git_force_push(version: str):
    """Wypycha zmiany na GitHuba z nadpisaniem zdalnej gałęzi main (UWAGA: --force)."""
    print("📤 Wysyłka do GitHuba (force push)...")
    try:
        run(["git", "fetch", "--all"], check=True, cwd=PROJECT_DIR)
        # Bez reset --hard, żeby NIE pobierać starych plików i NIE nadpisywać lokalnych
        run(["git", "add", "-A"], check=True, cwd=PROJECT_DIR)
        run(["git", "commit", "-m", f"build: CodePass v{version}"], check=False, cwd=PROJECT_DIR)
        run(["git", "push", "origin", "main", "--force"], check=True, cwd=PROJECT_DIR)
        run(["git", "tag", "-f", f"v{version}"], check=True, cwd=PROJECT_DIR)
        run(["git", "push", "--tags", "--force"], check=True, cwd=PROJECT_DIR)
        print("✅ Repozytorium zaktualizowane.")
    except Exception as e:
        print(f"⚠️  Nie udało się wypchnąć zmian na GitHuba: {e}")

def gh_release(version: str, assets: list[Path]):
    """Tworzy/aktualizuje Release na GitHubie (wymaga gh)."""
    try:
        run(["gh", "--version"], check=True)
    except Exception:
        print("ℹ️  gh nie jest dostępny – pomijam Release.")
        return

    tag = f"v{version}"
    title = f"{APP_NAME} {version}"

    # spróbuj usunąć istniejący release (bez błędu przy braku)
    subprocess.run(["gh", "release", "delete", tag, "-y"], cwd=str(PROJECT_DIR))

    # utwórz nowy release
    run(["gh", "release", "create", tag, "-t", title, "-n", f"Wydanie {title}"], check=True, cwd=PROJECT_DIR)

    # dołącz assets
    for a in assets:
        if a.exists():
            run(["gh", "release", "upload", tag, str(a)], check=True, cwd=PROJECT_DIR)
    print("✅ Release opublikowany.")


# ========================================
#  MAIN
# ========================================

def main():
    print("=== 🧱 CodePass Builder (Nuitka + ZIP + SIG + JSON) ===")
    ensure_paths()

    current_ver = get_version()
    print(f"📦 Aktualna wersja: {current_ver}")
    new_ver = input("🔹 Podaj nową wersję (ENTER = bez zmian): ").strip() or current_ver

    # ustaw wersję spójnie
    set_version(new_ver)

    # build exe
    exe_path = build_exe(new_ver)

    # zip + sign + verify + manifest
    zip_path = create_zip(new_ver, exe_path)
    sig_path = sign_and_verify(zip_path)
    manifest = write_update_json(new_ver, zip_path, sig_path, exe_path)

    # opcjonalny push
    do_push = input("🚀 Wysłać na GitHub (force)? [t/n]: ").strip().lower()
    if do_push == "t":
        git_force_push(new_ver)

        do_rel = input("🏷️  Utworzyć Release na GitHubie (gh)? [t/n]: ").strip().lower()
        if do_rel == "t":
            gh_release(new_ver, [exe_path, zip_path, sig_path, manifest])

    print(f"🎉 GOTOWE! v{new_ver}")
    print(f"   EXE: {exe_path}")
    print(f"   ZIP: {zip_path}")
    print(f"   SIG: {sig_path}")
    print(f"   JSON: {manifest}")


if __name__ == "__main__":
    main()
