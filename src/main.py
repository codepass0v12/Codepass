import os
import sys
import tkinter as tk
from tkinter import messagebox

try:
    from updater import get_local_version, check_for_updates, perform_update_flow
except ImportError as e:
    messagebox.showerror("Błąd krytyczny", f"Brak modułu updater:\n{e}")
    sys.exit(1)

try:
    from gui import CodePassGUI
except ImportError as e:
    messagebox.showerror("Błąd krytyczny", f"Brak modułu GUI:\n{e}")
    sys.exit(1)

# 🔹 Adres manifestu z GitHuba
MANIFEST_URL = "https://raw.githubusercontent.com/codepass0v12/Codepass/main/update.json"


def main():
    # 🔸 Odczyt lokalnej wersji
    app_version = get_local_version()
    print(f"🚀 Uruchamianie CodePass v{app_version}...")

    # 🔸 Główne okno
    root = tk.Tk()
    root.withdraw()

    # 🔸 Sprawdzenie aktualizacji
    try:
        manifest = check_for_updates(app_version, MANIFEST_URL)
        if manifest:
            new_version = manifest.get("version", "?")
            if messagebox.askyesno("Aktualizacja dostępna", f"Dostępna nowa wersja: {new_version}\nCzy chcesz zaktualizować teraz?"):
                perform_update_flow(manifest)
                return
            else:
                print("⏭️ Użytkownik pominął aktualizację.")
    except Exception as e:
        print(f"[Błąd aktualizacji] {e}")
        messagebox.showwarning("Aktualizacja", f"Nie udało się sprawdzić aktualizacji:\n{e}")

    # 🔸 Uruchomienie GUI
    root.deiconify()
    app = CodePassGUI(root, app_version)
    root.state("zoomed")
    root.mainloop()


if __name__ == "__main__":
    main()
