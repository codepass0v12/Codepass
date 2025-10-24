import os, subprocess, zipfile, json, shutil, base64
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
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")

VERSION_PATH = os.path.join(PROJECT_DIR, "version.txt")
PRIVATE_KEY_PATH = os.path.join(PROJECT_DIR, "private_key.pem")
PUBLIC_KEY_PATH  = os.path.join(PROJECT_DIR, "public_key.pem")

UPDATE_BASE_URL = "https://raw.githubusercontent.com/codepass0v12/Codepass/main/dist"
REPO = "codepass0v12/Codepass"

# ======================================
# FUNKCJE
# ======================================

def ask_version():
    if not os.path.exists(VERSION_PATH):
        open(VERSION_PATH, "w", encoding="utf-8").write("1.0.0")
    cur = open(VERSION_PATH,"r",encoding="utf-8").read().strip()
    print(f"📦 Aktualna wersja: {cur}")
    newv = input("🔹 Podaj nową wersję (ENTER = bez zmian): ").strip()
    if newv:
        open(VERSION_PATH,"w",encoding="utf-8").write(newv)
        print(f"✅ Zmieniono wersję: {cur} → {newv}")
        return newv
    return cur

def build_exe(version: str):
    print(f"🔨 Kompilacja CodePass v{version} przez Nuitka...")
    exe_out = os.path.join(DIST_DIR, "CodePass.exe")
    os.makedirs(DIST_DIR, exist_ok=True)
    cmd = [
        r"C:\Users\Administrator\PyCharmMiscProject\.venv\Scripts\python.exe", "-m", "nuitka",

        "--onefile",
        "--standalone",
        "--remove-output",
        "--windows-console-mode=disable",
        "--enable-plugin=tk-inter",
        "--windows-icon-from-ico=" + os.path.join(ASSETS_DIR, "logo.ico"),
        "--include-data-file=version.txt=version.txt",
        "--include-data-file=" + os.path.join(ASSETS_DIR, "logo.ico") + "=logo.ico",
        "--output-filename=" + exe_out,
        os.path.join(SRC_DIR, "main.py")
    ]
    res = subprocess.run(cmd)
    if res.returncode != 0:
        raise RuntimeError("❌ Błąd kompilacji Nuitka.")
    print("✅ EXE gotowy:", exe_out)
    sleep(1)
    return exe_out

def sign_zip(zip_path: str):
    print("🔏 Podpisywanie ZIP...")
    sig_path = zip_path.replace(".zip", ".sig")
    with open(PRIVATE_KEY_PATH,"rb") as f:
        priv = serialization.load_pem_private_key(f.read(), password=None)
    data = open(zip_path,"rb").read()
    sig = priv.sign(data, padding.PKCS1v15(), hashes.SHA256())
    open(sig_path,"wb").write(sig)
    print("✅ Podpis zapisany:", sig_path)
    return sig_path

def verify_sig(zip_path, sig_path):
    with open(PUBLIC_KEY_PATH,"rb") as f:
        pub = serialization.load_pem_public_key(f.read())
    data = open(zip_path,"rb").read()
    sig  = open(sig_path,"rb").read()
    pub.verify(sig, data, padding.PKCS1v15(), hashes.SHA256())
    print("✅ Weryfikacja podpisu OK.")

def create_zip(version: str, exe_path: str):
    zip_path = os.path.join(DIST_DIR, f"update_{version}.zip")
    ver_path = os.path.join(DIST_DIR, "version.txt")
    shutil.copy2(VERSION_PATH, ver_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(exe_path, "CodePass.exe")
        zipf.write(ver_path, "version.txt")
    print("📦 ZIP utworzony:", zip_path)
    return zip_path

def create_manifest(version: str, zip_path: str, sig_path: str):
    print("📝 Tworzenie update.json...")
    manifest = {
        "version": version,
        "timestamp": datetime.now().isoformat(),
        "download_url": f"{UPDATE_BASE_URL}/{os.path.basename(zip_path)}",
        "sig_url": f"{UPDATE_BASE_URL}/{os.path.basename(sig_path)}"
    }
    path = os.path.join(DIST_DIR, "update.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)
    print("✅ Manifest:", path)
    return path

def git_push_and_release(version: str):
    print("🚀 Wysyłanie na GitHub...")
    cmds = [
        ["git", "add", "."],
        ["git", "commit", "-m", f"build: CodePass v{version}"],
        ["git", "push", "origin", "main"],
        ["git", "tag", f"v{version}"],
        ["git", "push", "origin", f"v{version}"]
    ]
    for cmd in cmds:
        subprocess.run(cmd)
    gh = shutil.which("gh")
    if not gh:
        print("⚠️ gh CLI nie znaleziony — pomijam Release.")
        return
    subprocess.run([
        gh, "release", "create", f"v{version}",
        os.path.join(DIST_DIR, f"update_{version}.zip"),
        os.path.join(DIST_DIR, f"update_{version}.sig"),
        os.path.join(DIST_DIR, "update.json"),
        "--title", f"CodePass v{version}",
        "--notes", "Automatyczny release"
    ])
    print("✅ GitHub Release gotowy.")

def main():
    version = ask_version()
    exe = build_exe(version)
    zipf = create_zip(version, exe)
    sigf = sign_zip(zipf)
    verify_sig(zipf, sigf)
    create_manifest(version, zipf, sigf)
    git_push_and_release(version)
    print("🎉 GOTOWE: CodePass v" + version)
    subprocess.Popen(f'explorer "{DIST_DIR}"')

if __name__ == "__main__":
    main()
