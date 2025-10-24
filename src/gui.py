import os
import sys
import random
import string
import tempfile
import subprocess
from typing import Optional
import tkinter as tk
from tkinter import messagebox

import security
from updater import check_for_updates, perform_update_flow, get_local_version

# =========================================================
# Konfiguracja i ścieżki (spójne w trybie EXE i z Pythona)
# =========================================================

APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
MANIFEST_URL = "https://raw.githubusercontent.com/codepass0v12/Codepass/main/dist/update.json"

PIN_FILE = os.path.join(APP_DIR, "user_pin.txt")
PASSWORD_FILE = os.path.join(APP_DIR, "Hasła.enc")
PASSWORD_FILE_SECURE = os.path.join(APP_DIR, "Hasła_secure.enc")


# =========================================================
# Windows Hello — dyskretnie, bez popupów
# =========================================================

def windows_authenticate_hello(status_label: Optional[tk.Label] = None) -> bool:

    """
    Próbuje zweryfikować użytkownika przez Windows Hello w osobnym procesie.
    Zwraca True/False i (jeśli podano) aktualizuje status_label subtelnym komunikatem.
    Nie rzuca popupów, żeby UX był gładki.
    """
    hello_script = r'''
import asyncio
import winrt.windows.security.credentials.ui as ui

async def verify():
    availability = await ui.UserConsentVerifier.check_availability_async()
    if availability != ui.UserConsentVerifierAvailability.AVAILABLE:
        print("HELLO:NO")
        return
    result = await ui.UserConsentVerifier.request_verification_async("Potwierdź tożsamość w CodePass")
    if result == ui.UserConsentVerificationResult.VERIFIED:
        print("HELLO:OK")
    else:
        print("HELLO:FAIL")

asyncio.run(verify())
'''
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode="w", encoding="utf-8")
    tmp.write(hello_script)
    tmp.close()

    try:
        proc = subprocess.run([sys.executable, tmp.name],
                              capture_output=True, text=True, timeout=60)
        out = (proc.stdout or "").strip()
    except Exception:
        out = "HELLO:ERR"

    # Sprzątanie best-effort
    try:
        os.remove(tmp.name)
    except Exception:
        pass

    if out == "HELLO:OK":
        if status_label:
            status_label.config(text="Tożsamość potwierdzona Windows Hello.", fg="#00FFAA")
        return True

    if status_label:
        mapping = {
            "HELLO:NO":  "⚠️ Windows Hello niedostępny.",
            "HELLO:FAIL":"⚠️ Weryfikacja Windows Hello anulowana.",
            "HELLO:ERR": "⚠️ Błąd Windows Hello."
        }
        status_label.config(text=mapping.get(out, "⚠️ Weryfikacja Windows Hello nie powiodła się."), fg="#FF5555")

    return False


# =========================================================
# Własny, ciemny dialog do wprowadzania PIN (bez dingów)
# =========================================================

def ask_pin(parent: tk.Tk, title: str, prompt: str) -> str:
    """
    Minimalny, własny dialog w ciemnym motywie CodePass (bez natywnych dźwięków).
    Zwraca wpisany PIN (string) lub "".
    """
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.configure(bg="#202225")
    dlg.resizable(False, False)
    dlg.attributes("-topmost", True)
    # wyśrodkuj nieduże okno
    dlg.geometry("340x170+200+200")

    tk.Label(dlg, text=prompt, bg="#202225", fg="white",
             font=("Segoe UI", 11)).pack(pady=(22, 10))

    var = tk.StringVar()
    entry = tk.Entry(dlg, textvariable=var, font=("Segoe UI", 13),
                     width=16, bg="#2F3136", fg="#00FFAA", show="*", justify="center",
                     relief="flat", insertbackground="white")
    entry.pack(pady=6)
    entry.focus_set()

    btn_row = tk.Frame(dlg, bg="#202225")
    btn_row.pack(pady=10)

    def _ok():
        dlg.destroy()

    def _cancel():
        var.set("")
        dlg.destroy()

    tk.Button(btn_row, text="OK", command=_ok,
              bg="#5865F2", fg="white", font=("Segoe UI", 11),
              relief="flat", padx=18, pady=4, activebackground="#4752C4").pack(side="left", padx=6)
    tk.Button(btn_row, text="Anuluj", command=_cancel,
              bg="#2F3136", fg="white", font=("Segoe UI", 11),
              relief="flat", padx=14, pady=4, activebackground="#40444B").pack(side="left", padx=6)

    # modal
    dlg.grab_set()
    dlg.wait_window()
    return var.get().strip()


# =========================================================
# Klasa głównego GUI
# =========================================================

class CodePassGUI:
    def __init__(self, root: tk.Tk, version: str):
        self.root = root
        self.version = version

        # Okno
        root.title("🔐 CodePass — Generator i Menedżer Haseł")
        root.state("zoomed")
        root.configure(bg="#202225")

        # Szyfrowanie
        try:
            self.fernet = security.load_or_create_fernet()
        except Exception as e:
            self.fernet = None
            messagebox.showerror("Błąd bezpieczeństwa",
                                 f"Nie udało się przygotować szyfrowania:\n{e}")

        # Zmienne UI
        self.uppercase_var = tk.BooleanVar(value=True)
        self.special_var = tk.BooleanVar(value=True)
        self.secure_var = tk.BooleanVar(value=False)  # tryb „Większe bezpieczeństwo”
        self.pin_visible = False

        # Nagłówek
        tk.Label(root, text="🔐 CodePass — Generator i Menedżer Haseł",
                 font=("Segoe UI Semibold", 24), bg="#202225", fg="#FFFFFF").pack(pady=24)

        # Wiersz Domena/Login
        row1 = tk.Frame(root, bg="#202225")
        row1.pack(pady=6)

        tk.Label(row1, text="Domena / Serwis:", font=("Segoe UI", 13),
                 bg="#202225", fg="white").grid(row=0, column=0, padx=8, sticky="e")
        self.domain_entry = tk.Entry(row1, font=("Segoe UI", 13),
                                     width=28, bg="#2F3136", fg="white", relief="flat",
                                     insertbackground="white")
        self.domain_entry.grid(row=0, column=1, padx=8)

        tk.Label(row1, text="Login / E-mail:", font=("Segoe UI", 13),
                 bg="#202225", fg="white").grid(row=0, column=2, padx=8, sticky="e")
        self.login_entry = tk.Entry(row1, font=("Segoe UI", 13),
                                    width=28, bg="#2F3136", fg="white", relief="flat",
                                    insertbackground="white")
        self.login_entry.grid(row=0, column=3, padx=8)

        # Wiersz: długość i opcje znaków
        row2 = tk.Frame(root, bg="#202225")
        row2.pack(pady=6)

        tk.Label(row2, text="Długość hasła:", font=("Segoe UI", 13),
                 bg="#202225", fg="white").grid(row=0, column=0, padx=8, sticky="e")
        self.length_entry = tk.Entry(row2, font=("Segoe UI", 13),
                                     width=6, bg="#2F3136", fg="white", relief="flat",
                                     insertbackground="white")
        self.length_entry.insert(0, "12")
        self.length_entry.grid(row=0, column=1, padx=8, sticky="w")

        tk.Checkbutton(row2, text="Duże litery", variable=self.uppercase_var,
                       font=("Segoe UI", 12), bg="#202225", fg="white",
                       selectcolor="#2F3136", activebackground="#202225").grid(row=0, column=2, padx=12)
        tk.Checkbutton(row2, text="Znaki specjalne", variable=self.special_var,
                       font=("Segoe UI", 12), bg="#202225", fg="white",
                       selectcolor="#2F3136", activebackground="#202225").grid(row=0, column=3, padx=12)

        # Wiersz: bezpieczeństwo (PIN/Hello)
        sec_row = tk.Frame(root, bg="#202225")
        sec_row.pack(pady=6)

        tk.Checkbutton(
            sec_row,
            text="Większe bezpieczeństwo (PIN lub Windows Hello przy zapisie)",
            variable=self.secure_var,
            font=("Segoe UI", 12), bg="#202225", fg="#00FFAA",
            selectcolor="#2F3136", activebackground="#202225"
        ).pack(side="left", padx=8)

        self.pin_entry = tk.Entry(sec_row, font=("Segoe UI", 12),
                                  width=10, bg="#2F3136", fg="#00FFAA",
                                  show="*", relief="flat", justify="center",
                                  insertbackground="white")
        self.pin_entry.pack(side="left", padx=6)

        self.eye_button = tk.Button(
            sec_row, text="👁", font=("Segoe UI", 11, "bold"),
            bg="#2F3136", fg="#00FFAA", relief="flat",
            activebackground="#40444B",
            command=self.toggle_pin_visibility
        )
        self.eye_button.pack(side="left", padx=4)

        self.reset_pin_button = tk.Button(
            sec_row, text="🔑 Resetuj PIN",
            font=("Segoe UI", 10), bg="#2F3136", fg="#00FFAA",
            relief="flat", activebackground="#40444B",
            command=self.reset_pin
        )
        self.reset_pin_button.pack(side="left", padx=6)

        # Delikatny label statusu Hello/PIN (bez popupów)
        self.status_label = tk.Label(root, text="", font=("Segoe UI", 10),
                                     bg="#202225", fg="#FF5555")
        self.status_label.pack(pady=(0, 6))

        # Przyciski główne
        btns = tk.Frame(root, bg="#202225")
        btns.pack(pady=12)

        tk.Button(btns, text="🎲 Generuj hasło", command=self.generate_password,
                  font=("Segoe UI", 14, "bold"), bg="#5865F2", fg="white",
                  activebackground="#4752C4", relief="flat", padx=24, pady=10)\
            .grid(row=0, column=0, padx=8)

        tk.Button(btns, text="📋 Kopiuj", command=self.copy_password,
                  font=("Segoe UI", 13), bg="#2F3136", fg="white",
                  activebackground="#40444B", relief="flat", padx=18, pady=8)\
            .grid(row=0, column=1, padx=8)

        tk.Button(btns, text="💾 Zapisz wpis", command=self.save_password_secure,
                  font=("Segoe UI", 13), bg="#2F3136", fg="white",
                  activebackground="#40444B", relief="flat", padx=18, pady=8)\
            .grid(row=0, column=2, padx=8)

        tk.Button(btns, text="📄 Pokaż zapisane", command=self.show_saved_entries,
                  font=("Segoe UI", 13), bg="#2F3136", fg="white",
                  activebackground="#40444B", relief="flat", padx=18, pady=8)\
            .grid(row=0, column=3, padx=8)

        tk.Button(btns, text="🔄 Sprawdź aktualizacje", command=self.manual_update_check,
                  font=("Segoe UI", 13, "bold"), bg="#5865F2", fg="white",
                  activebackground="#4752C4", relief="flat", padx=18, pady=8)\
            .grid(row=0, column=4, padx=8)

        # Pole hasła (wynik generatora)
        self.password_entry = tk.Entry(root, font=("Segoe UI", 16),
                                       justify="center", width=48,
                                       bg="#2F3136", fg="#00FFAA", relief="flat",
                                       insertbackground="white")
        self.password_entry.pack(pady=8)

        # Wersja
        self.version_label = tk.Label(root, text=f"Wersja {self.version}",
                                      font=("Segoe UI", 12), bg="#202225", fg="#AAAAAA")
        self.version_label.pack(side="bottom", pady=10)

    # -----------------------------------------------------
    # Akcje / logika
    # -----------------------------------------------------

    def toggle_pin_visibility(self):
        self.pin_visible = not self.pin_visible
        self.pin_entry.config(show="" if self.pin_visible else "*")
        self.eye_button.config(text="🙈" if self.pin_visible else "👁")

    def reset_pin(self):
        """Reset PIN — bez popupów, czyści plik i pole, pokazuje status."""
        try:
            if os.path.exists(PIN_FILE):
                os.remove(PIN_FILE)
        except Exception:
            pass
        self.pin_entry.delete(0, tk.END)
        self.status_label.config(text="PIN został zresetowany. Ustawisz nowy przy następnym zapisie w trybie bezpiecznym.",
                                 fg="#00FFAA")

    def _ensure_secure_auth(self) -> bool:
        """
        Spełnienie wymogów trybu bezpiecznego:
        - jeśli PIN nie istnieje → eleganckie 2× okienko PIN (ustawienie + potwierdzenie);
        - jeśli PIN istnieje → akceptuj poprawny PIN Z POLA lub (alternatywnie) Windows Hello.
        Bez natywnych beepów. Subtelny status w labelu.
        """
        # Pierwsze ustawienie PIN (2×)
        if not os.path.exists(PIN_FILE):
            pin1 = ask_pin(self.root, "Nowy PIN", "Utwórz nowy PIN:")
            pin2 = ask_pin(self.root, "Potwierdź PIN", "Wpisz ponownie PIN:")
            if not pin1 or not pin2 or pin1 != pin2:
                self.status_label.config(text="PIN nie został ustawiony (różne wpisy lub anulowano).", fg="#FF5555")
                return False
            try:
                with open(PIN_FILE, "w") as f:
                    f.write(pin1)
            except Exception:
                self.status_label.config(text="Błąd zapisu PIN.", fg="#FF5555")
                return False
            self.status_label.config(text="PIN został zapisany.", fg="#00FFAA")
            return True

        # PIN istnieje → próbuj PIN z pola
        try:
            with open(PIN_FILE, "r") as f:
                saved_pin = f.read().strip()
        except Exception:
            self.status_label.config(text="Błąd odczytu PIN.", fg="#FF5555")
            return False

        typed = self.pin_entry.get().strip()
        if typed and typed == saved_pin:
            self.status_label.config(text="PIN poprawny.", fg="#00FFAA")
            return True

        # Alternatywa: Hello
        if windows_authenticate_hello(self.status_label):
            return True

        self.status_label.config(text="Niepoprawny PIN lub brak weryfikacji Hello.", fg="#FF5555")
        return False

    def generate_password(self):
        try:
            length = int(self.length_entry.get())
        except Exception:
            messagebox.showerror("Błąd", "Podaj poprawną długość (liczbę).")
            return
        if length < 5:
            messagebox.showwarning("Uwaga", "Minimalna długość hasła to 5 znaków.")
            length = 5

        alphabet = string.ascii_lowercase + string.digits
        if self.uppercase_var.get():
            alphabet += string.ascii_uppercase
        if self.special_var.get():
            alphabet += string.punctuation

        pwd = "".join(random.choices(alphabet, k=length))
        self.password_entry.delete(0, tk.END)
        self.password_entry.insert(0, pwd)

    def copy_password(self):
        pwd = self.password_entry.get()
        if not pwd:
            messagebox.showwarning("Brak hasła", "Najpierw wygeneruj hasło.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(pwd)
        messagebox.showinfo("Skopiowano", "Hasło skopiowano do schowka.")

    def save_password_secure(self):
        """
        Zapis:
        - gdy checkbox „Większe bezpieczeństwo” jest WYŁĄCZONY → zwykły zapis bez żadnych potwierdzeń do Hasła.enc,
        - gdy WŁĄCZONY → wymaga spełnienia _ensure_secure_auth() i zapisuje do Hasła_secure.enc.
        """
        if self.fernet is None:
            messagebox.showerror("Błąd", "Szyfrowanie niedostępne.")
            return

        domain = self.domain_entry.get().strip()
        login = self.login_entry.get().strip()
        pwd = self.password_entry.get().strip()
        if not (domain and login and pwd):
            messagebox.showwarning("Błąd", "Uzupełnij wszystkie pola przed zapisem.")
            return

        if not self.secure_var.get():
            # Zwykły tryb — żadnych wymagań
            target_file = PASSWORD_FILE
        else:
            # Tryb bezpieczny — wymagaj PIN **lub** Hello
            if not self._ensure_secure_auth():
                return
            target_file = PASSWORD_FILE_SECURE

        try:
            entries = security.read_entries(self.fernet, target_file)
            next_nr = len(entries) + 1
            line = f"{next_nr}. {domain} - {login} - {pwd}"
            security.append_entry(self.fernet, target_file, line)
            messagebox.showinfo("Zapisano",
                                f"Dodano wpis nr {next_nr} ({os.path.basename(target_file)})")
        except Exception as e:
            messagebox.showerror("Błąd zapisu", f"Nie udało się zapisać wpisu:\n{e}")

    def show_saved_entries(self):
        # Wyświetl plik zgodny z aktualnym trybem UI
        target_file = PASSWORD_FILE_SECURE if self.secure_var.get() else PASSWORD_FILE
        try:
            entries = security.read_entries(self.fernet, target_file)
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się odczytać wpisów:\n{e}")
            return

        win = tk.Toplevel(self.root)
        win.title("Zapisane wpisy")
        win.geometry("760x460")
        win.configure(bg="#202225")

        text = tk.Text(win, bg="#2F3136", fg="white", insertbackground="white",
                       font=("Consolas", 12))
        text.pack(fill="both", expand=True, padx=10, pady=10)

        text.insert("1.0", "\n".join(entries) + ("\n" if entries else "(brak wpisów)"))

    def manual_update_check(self):
        current = get_local_version()
        manifest = check_for_updates(current, MANIFEST_URL)
        if manifest:
            ver = manifest.get("version", "?")
            if messagebox.askyesno("Aktualizacja", f"Dostępna wersja {ver}. Zaktualizować teraz?"):
                perform_update_flow(manifest)
                self.version = get_local_version()
                self.version_label.config(text=f"Wersja {self.version}")
        else:
            messagebox.showinfo("Aktualizacje", "Masz najnowszą wersję.")
