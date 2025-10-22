import requests
import os
import sys
from tkinter import messagebox


def check_for_updates(current_version: str, manifest_url: str):
    """
    Sprawdza, czy dostępna jest nowsza wersja aplikacji.
    """
    try:
        r = requests.get(manifest_url, timeout=10)
        r.raise_for_status()
        manifest: dict = r.json()
        latest_version = manifest.get("version")

        if latest_version and latest_version != current_version:
            print(f"[Aktualizacja] Znaleziono nową wersję: {latest_version}")
            return manifest

        print("[Aktualizacja] Aplikacja jest aktualna.")
        return None

    except requests.RequestException as e:
        messagebox.showerror("Błąd aktualizacji", f"Nie udało się sprawdzić aktualizacji:\n{e}")
        return None


def perform_update_flow(manifest: dict):
    """
    Pobiera nową wersję aplikacji i zapisuje informację o aktualnej wersji,
    aby uniknąć ponownego pobierania tej samej wersji.
    """
    download_url = manifest.get("download_url")
    version = manifest.get("version")

    if not download_url:
        messagebox.showerror("Błąd", "Nie znaleziono linku do aktualizacji.")
        return

    try:
        response = requests.get(download_url, stream=True)
        response.raise_for_status()

        # Nazwa pobranego pliku
        file_name = f"CodePass_{version}.zip"
        file_path = os.path.join(os.path.dirname(sys.argv[0]), file_name)

        # Pobranie pliku aktualizacji
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # 🔹 Zapis nowej wersji do pliku version.txt
        version_path = os.path.join(os.path.dirname(sys.argv[0]), "version.txt")
        with open(version_path, "w", encoding="utf-8") as vf:
            vf.write(version)

        messagebox.showinfo(
            "Aktualizacja zakończona",
            f"Pobrano nową wersję CodePass {version}!\n\n"
            f"Plik zapisano jako:\n{file_path}\n\n"
            f"Numer wersji został zaktualizowany."
        )

    except Exception as e:
        messagebox.showerror("Błąd aktualizacji", f"Wystąpił problem podczas pobierania:\n{e}")
