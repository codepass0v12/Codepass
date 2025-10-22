import os
import sys
import tkinter as tk
from tkinter import messagebox

# ✅ Upewniamy się, że folder z plikami (gui, updater itd.) jest w ścieżce Pythona
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 🔧 Import modułów aplikacji
from gui import CodePassGUI
from updater import check_for_updates


# 🔢 Numer aktualnej wersji programu
APP_VERSION = "1.30"

# 🌐 Link do manifestu aktualizacji (update.json)
# 👇 wklej tu swój link z Google Drive (lub później z GitHuba)
MANIFEST_URL = "https://raw.githubusercontent.com/codepass0v12/Codepass/main/update.json"


def main():
    print("Uruchamianie CodePass...")

    # 🧱 Tworzymy główne okno tkinter, ale ukrywamy je zanim się pojawi (żeby nie było pióra)
    root = tk.Tk()
    root.withdraw()  # ⛔️ Ukrywa białe domyślne okno

    # 🧩 Sprawdzenie aktualizacji
    try:
        check_for_updates()  # <-- nowa funkcja obsługuje cały proces
    except Exception as e:
        print(f"[Błąd aktualizacji] {e}")
        messagebox.showwarning("Aktualizacja", f"Nie udało się sprawdzić aktualizacji:\n{e}")

    # 🎨 Uruchamiamy główny interfejs

    # 🎨 Uruchamiamy główny interfejs
    app = CodePassGUI(root)
    root.deiconify()  # ✅ Pokazujemy już przygotowane okno GUI
    print("Aplikacja uruchomiona. Oczekiwanie na interakcję użytkownika...")
    root.mainloop()


if __name__ == "__main__":
    main()
