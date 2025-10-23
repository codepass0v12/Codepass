import os
import sys
import tkinter as tk
from tkinter import messagebox

from updater import get_local_version, check_for_updates, perform_update_flow
from gui import CodePassGUI

# 🔹 Adres manifestu z GitHuba
MANIFEST_URL = "https://raw.githubusercontent.com/codepass0v12/Codepass/main/update.json"


def main():
    # 🔸 Odczyt lokalnej wersji
    app_version = get_local_version()
    print(f"Uruchamianie CodePass v{app_version}...")

    # 🔸 Tworzenie głównego okna
    root = tk.Tk()
    root.withdraw()  # ukryj białe okno na czas aktualizacji

    # 🔸 Sprawdzenie aktualizacji
    try:
        manifest = check_for_updates(app_version, MANIFEST_URL)
        if manifest:
            perform_update_flow(manifest)
            return  # zakończ — nowa wersja sama się uruchomi
    except Exception as e:
        print(f"[Błąd aktualizacji] {e}")
        messagebox.showwarning("Aktualizacja", f"Nie udało się sprawdzić aktualizacji:\n{e}")

    # 🔸 Pokazanie głównego okna aplikacji
    root.deiconify()
    app = CodePassGUI(root, app_version)
    root.state("zoomed")  # pełny ekran, ale można minimalizować
    root.mainloop()


if __name__ == "__main__":
    main()
