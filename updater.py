import os
import sys
import json
import requests
import shutil
from tkinter import messagebox

APP_NAME = "CodePass.exe"
VERSION_FILE = "version.txt"
MANIFEST_URL = "https://raw.githubusercontent.com/codepass0v12/Codepass/main/update.json"


def get_local_version():
    """Odczytuje lokalną wersję aplikacji z pliku version.txt"""
    if not os.path.exists(VERSION_FILE):
        return "0.0"
    with open(VERSION_FILE, "r") as f:
        return f.read().strip()


def check_for_updates():
    """Sprawdza dostępność aktualizacji na podstawie pliku update.json z GitHuba"""
    try:
        response = requests.get(MANIFEST_URL, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        manifest = response.json()
    except Exception as e:
        messagebox.showerror("Błąd", f"Nie udało się pobrać informacji o aktualizacji:\n{e}")
        return

    local_version = get_local_version()
    remote_version = manifest.get("version", "0.0")
    download_url = manifest.get("download_url")

    print(f"[Aktualizacja] Wersja lokalna: {local_version}")
    print(f"[Aktualizacja] Wersja zdalna: {remote_version}")

    if remote_version > local_version:
        ask = messagebox.askyesno(
            "Nowa wersja dostępna",
            f"Dostępna nowa wersja: {remote_version}\nCzy chcesz pobrać i zainstalować?"
        )
        if ask:
            download_and_replace(download_url, remote_version)
    else:
        messagebox.showinfo("Aktualizacja", "Aplikacja jest aktualna.")


def download_and_replace(download_url, new_version):
    """Pobiera nową wersję aplikacji i podmienia plik EXE"""
    temp_file = "update_temp.exe"

    try:
        messagebox.showinfo("Aktualizacja", "Pobieranie nowej wersji...")

        response = requests.get(
            download_url,
            stream=True,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()

        with open(temp_file, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)

        app_path = os.path.join(os.getcwd(), APP_NAME)
        backup_path = app_path + ".bak"

        # Nadpisanie starego pliku
        if os.path.exists(app_path):
            shutil.move(app_path, backup_path)

        shutil.move(temp_file, app_path)

        # Aktualizacja wersji
        with open(VERSION_FILE, "w") as vf:
            vf.write(new_version)

        messagebox.showinfo("Aktualizacja", f"Aplikacja została zaktualizowana do wersji {new_version}.")

        # Uruchom nową wersję
        os.startfile(app_path)
        sys.exit(0)

    except Exception as e:
        messagebox.showerror("Błąd aktualizacji", f"Wystąpił problem podczas aktualizacji:\n{e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)
