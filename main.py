import tkinter as tk
from tkinter import messagebox
from gui import CodePassGUI
from updater import check_for_updates, perform_update_flow, get_local_version


APP_VERSION = get_local_version()
MANIFEST_URL = "https://raw.githubusercontent.com/codepass0v12/Codepass/main/update.json"


def main():
    # 🔄 sprawdzanie aktualizacji przy starcie
    try:
        manifest = check_for_updates(APP_VERSION, MANIFEST_URL)
        if manifest:
            perform_update_flow(manifest)
    except Exception as e:
        print(f"[Aktualizacja] Błąd sprawdzania aktualizacji: {e}")

    # 🖥️ GUI
    root = tk.Tk()
    app = CodePassGUI(root, APP_VERSION)

    # Pełny ekran, ale da się minimalizować
    root.state("zoomed")
    root.minsize(900, 600)

    root.mainloop()


if __name__ == "__main__":
    main()
