import os, sys, json, requests, zipfile, subprocess
from tkinter import messagebox

def get_local_version():
    try:
        with open("version.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0"

def check_for_updates(current_version: str, manifest_url: str):
    try:
        response = requests.get(manifest_url, timeout=10)
        response.raise_for_status()
        manifest = response.json()
    except Exception as e:
        print(f"[Błąd sprawdzania aktualizacji] {e}")
        return None

    latest_version = manifest.get("version", "0.0")
    print(f"Aktualna wersja: {current_version}, dostępna: {latest_version}")

    if latest_version == current_version:
        print("Aplikacja jest aktualna.")
        return None
    return manifest

def perform_update_flow(manifest: dict):
    version = manifest.get("version", "Nieznana")
    download_url = manifest.get("download_url")

    if not download_url:
        messagebox.showerror("Błąd", "Brak linku do aktualizacji w update.json.")
        return

    try:
        print(f"[Aktualizacja] Pobieranie wersji {version}...")
        zip_data = requests.get(download_url, timeout=30).content

        app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        tmp_dir = os.path.join(app_dir, "_update_tmp")
        os.makedirs(tmp_dir, exist_ok=True)

        zip_path = os.path.join(tmp_dir, "update.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_data)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(tmp_dir)
        os.remove(zip_path)

        for root_dir, _, files in os.walk(tmp_dir):
            for file in files:
                src = os.path.join(root_dir, file)
                rel_path = os.path.relpath(src, tmp_dir)
                dst = os.path.join(app_dir, rel_path)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                os.replace(src, dst)

        for root_dir, dirs, files in os.walk(tmp_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root_dir, name))
            for name in dirs:
                os.rmdir(os.path.join(root_dir, name))
        os.rmdir(tmp_dir)

        with open(os.path.join(app_dir, "version.txt"), "w", encoding="utf-8") as vf:
            vf.write(version)

        messagebox.showinfo("Aktualizacja", f"Zaktualizowano do wersji {version}!")

        exe_path = os.path.join(app_dir, os.path.basename(sys.argv[0]))
        subprocess.Popen([exe_path])
        os._exit(0)

    except Exception as e:
        messagebox.showerror("Błąd aktualizacji", f"Nie udało się zainstalować aktualizacji:\n{e}")
        print(f"[Błąd aktualizacji] {e}")
