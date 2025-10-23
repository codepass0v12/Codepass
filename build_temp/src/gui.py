import os
import random
import string
import tempfile
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox
import tkinter.simpledialog as sd

from updater import check_for_updates, perform_update_flow, get_local_version
import security
import config_manager  # 🔐 nowy moduł do obsługi PIN-u

PASSWORD_FILE = "Hasła.enc"
MANIFEST_URL = "https://raw.githubusercontent.com/codepass0v12/Codepass/main/update.json"


# ==================== 🔐 Weryfikacja Windows Hello lub PIN ====================

def windows_authenticate_hello() -> bool:
    """
    Próbuje uruchomić Windows Hello, a jeśli system go nie obsługuje —
    wyświetla awaryjny ekran z PIN-em lokalnym.
    """
    import tempfile, subprocess, sys, os

    hello_code = r'''
import asyncio
import winrt.windows.security.credentials.ui as ui

async def verify():
    availability = await ui.UserConsentVerifier.check_availability_async()
    if availability != ui.UserConsentVerifierAvailability.AVAILABLE:
        print("NO_HELLO")
        return
    result = await ui.UserConsentVerifier.request_verification_async("Potwierdź tożsamość w CodePass")
    if result == ui.UserConsentVerificationResult.VERIFIED:
        print("OK")
    else:
        print("FAIL")

asyncio.run(verify())
'''

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode="w", encoding="utf-8")
    tmp.write(hello_code)
    tmp.close()

    try:
        proc = subprocess.run([sys.executable, tmp.name], capture_output=True, text=True, timeout=15)
        output = proc.stdout.strip()
        print("[Hello output]", output)

        if "OK" in output:
            return True
        if "NO_HELLO" in output:
            messagebox.showwarning("Windows Hello", "Windows Hello niedostępny — użyj PIN-u awaryjnego.")
    except Exception as e:
        print("[Błąd Hello subprocess]", e)
        messagebox.showerror("Błąd Hello", "Nie można uruchomić Windows Hello. Przejście do trybu awaryjnego.")
    finally:
        try:
            os.remove(tmp.name)
        except Exception:
            pass

    # 🔐 Tryb awaryjny — użycie PIN-u z configu
    cfg = config_manager.load_config()
    user_pin = sd.askstring("PIN awaryjny", "Podaj swój PIN awaryjny:", show="*")

    if not cfg.get("pin"):
        messagebox.showerror("Brak PIN-u", "Nie ustawiono jeszcze PIN-u awaryjnego.")
        return False

    if user_pin == cfg["pin"]:
        return True
    elif user_pin is None:
        messagebox.showwarning("Anulowano", "Nie wprowadzono PIN-u.")
    else:
        messagebox.showerror("Błąd", "Niepoprawny PIN.")
    return False


# ======================== 🌙 Klasa GUI ========================

class CodePassGUI:
    def __init__(self, root, version: str):
        self.root = root
        self.version = version
        self.root.title("🔐 CodePass — Generator i Menedżer Haseł")
        self.root.state("zoomed")
        self.root.configure(bg="#202225")

        # --- szyfrowanie ---
        try:
            self.fernet = security.load_or_create_fernet()
        except Exception as e:
            messagebox.showerror("Błąd bezpieczeństwa", f"Nie udało się przygotować szyfrowania:\n{e}")
            self.fernet = None

        # --- zmienne ---
        self.uppercase_var = tk.BooleanVar(value=True)
        self.special_var = tk.BooleanVar(value=True)
        self.secure_var = tk.BooleanVar(value=False)

        # --- nagłówek ---
        tk.Label(
            root, text="🔐 CodePass — Generator i Menedżer Haseł",
            font=("Segoe UI Semibold", 24), bg="#202225", fg="#FFFFFF"
        ).pack(pady=24)

        # --- domena/login ---
        row1 = tk.Frame(root, bg="#202225")
        row1.pack(pady=6)

        tk.Label(row1, text="Domena / Serwis:", font=("Segoe UI", 13),
                 bg="#202225", fg="white").grid(row=0, column=0, padx=8, sticky="e")
        self.domain_entry = tk.Entry(row1, font=("Segoe UI", 13),
                                     width=28, bg="#2F3136", fg="white", relief="flat")
        self.domain_entry.grid(row=0, column=1, padx=8)

        tk.Label(row1, text="Login / E-mail:", font=("Segoe UI", 13),
                 bg="#202225", fg="white").grid(row=0, column=2, padx=8, sticky="e")
        self.login_entry = tk.Entry(row1, font=("Segoe UI", 13),
                                    width=28, bg="#2F3136", fg="white", relief="flat")
        self.login_entry.grid(row=0, column=3, padx=8)

        # --- długość + opcje ---
        row2 = tk.Frame(root, bg="#202225")
        row2.pack(pady=6)

        tk.Label(row2, text="Długość hasła:", font=("Segoe UI", 13),
                 bg="#202225", fg="white").grid(row=0, column=0, padx=8, sticky="e")
        self.length_entry = tk.Entry(row2, font=("Segoe UI", 13),
                                     width=6, bg="#2F3136", fg="white", relief="flat")
        self.length_entry.insert(0, "12")
        self.length_entry.grid(row=0, column=1, padx=8, sticky="w")

        tk.Checkbutton(
            row2, text="Duże litery", variable=self.uppercase_var,
            font=("Segoe UI", 12), bg="#202225", fg="white",
            selectcolor="#2F3136", activebackground="#202225"
        ).grid(row=0, column=2, padx=12)

        tk.Checkbutton(
            row2, text="Znaki specjalne", variable=self.special_var,
            font=("Segoe UI", 12), bg="#202225", fg="white",
            selectcolor="#2F3136", activebackground="#202225"
        ).grid(row=0, column=3, padx=12)

        # --- bezpieczeństwo ---
        row3 = tk.Frame(root, bg="#202225")
        row3.pack(pady=6)

        tk.Checkbutton(
            row3,
            text="Większe bezpieczeństwo (wymagaj Windows Hello przy zapisie)",
            variable=self.secure_var,
            font=("Segoe UI", 12), bg="#202225", fg="#00FFAA",
            selectcolor="#2F3136", activebackground="#202225"
        ).grid(row=0, column=0, padx=6, sticky="w")

        # 🔑 nowy przycisk obok checkboxa
        tk.Button(
            row3, text="🔑 Ustaw PIN awaryjny", command=self.set_fallback_pin,
            font=("Segoe UI", 12), bg="#2F3136", fg="white",
            activebackground="#40444B", relief="flat", padx=12, pady=4
        ).grid(row=0, column=1, padx=12)

        # --- przyciski ---
        btns = tk.Frame(root, bg="#202225")
        btns.pack(pady=12)

        tk.Button(
            btns, text="🎲 Generuj hasło", command=self.generate_password,
            font=("Segoe UI", 14, "bold"), bg="#5865F2", fg="white",
            activebackground="#4752C4", relief="flat", padx=24, pady=10
        ).grid(row=0, column=0, padx=8)

        tk.Button(
            btns, text="📋 Kopiuj", command=self.copy_password,
            font=("Segoe UI", 13), bg="#2F3136", fg="white",
            activebackground="#40444B", relief="flat", padx=18, pady=8
        ).grid(row=0, column=1, padx=8)

        tk.Button(
            btns, text="💾 Zapisz wpis", command=self.save_password_secure,
            font=("Segoe UI", 13), bg="#2F3136", fg="white",
            activebackground="#40444B", relief="flat", padx=18, pady=8
        ).grid(row=0, column=2, padx=8)

        tk.Button(
            btns, text="📄 Pokaż zapisane", command=self.show_saved_entries,
            font=("Segoe UI", 13), bg="#2F3136", fg="white",
            activebackground="#40444B", relief="flat", padx=18, pady=8
        ).grid(row=0, column=3, padx=8)

        tk.Button(
            btns, text="🔄 Sprawdź aktualizacje", command=self.manual_update_check,
            font=("Segoe UI", 13, "bold"), bg="#5865F2", fg="white",
            activebackground="#4752C4", relief="flat", padx=18, pady=8
        ).grid(row=0, column=4, padx=8)

        # --- pole hasła ---
        self.password_entry = tk.Entry(
            root, font=("Segoe UI", 16), justify="center", width=48,
            bg="#2F3136", fg="#00FFAA", relief="flat"
        )
        self.password_entry.pack(pady=8)

        # --- wersja ---
        self.version_label = tk.Label(
            root, text=f"Wersja {self.version}",
            font=("Segoe UI", 12), bg="#202225", fg="#AAAAAA"
        )
        self.version_label.pack(side="bottom", pady=10)

    # ======================== Logika GUI ========================

    def generate_password(self):
        try:
            length = int(self.length_entry.get())
            if length < 5:
                messagebox.showwarning("Uwaga", "Minimalna długość hasła to 5 znaków.")
                length = 5
        except ValueError:
            messagebox.showerror("Błąd", "Podaj poprawną długość (liczbę).")
            return

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
        if self.fernet is None:
            messagebox.showerror("Błąd", "Szyfrowanie jest niedostępne. Zapis anulowany.")
            return

        domain = self.domain_entry.get().strip()
        login = self.login_entry.get().strip()
        pwd = self.password_entry.get().strip()

        if not pwd:
            messagebox.showwarning("Brak hasła", "Najpierw wygeneruj hasło.")
            return
        if not domain:
            messagebox.showwarning("Brak domeny", "Podaj domenę/serwis (np. facebook.com).")
            return
        if not login:
            messagebox.showwarning("Brak loginu", "Podaj login lub e-mail.")
            return

        if self.secure_var.get() and not windows_authenticate_hello():
            messagebox.showerror("Bezpieczeństwo", "Weryfikacja nie powiodła się — zapis anulowany.")
            return

        try:
            entries = security.read_entries(self.fernet, PASSWORD_FILE)
            next_nr = len(entries) + 1
            line = f"{next_nr}. {domain} - {login} - {pwd}"
            security.append_entry(self.fernet, PASSWORD_FILE, line)
            messagebox.showinfo("Zapisano", f"Dodano wpis nr {next_nr} do {PASSWORD_FILE}")
        except Exception as e:
            messagebox.showerror("Błąd zapisu", f"Nie udało się zapisać do pliku:\n{e}")

    def show_saved_entries(self):
        if self.fernet is None:
            messagebox.showerror("Błąd", "Szyfrowanie jest niedostępne.")
            return
        entries = security.read_entries(self.fernet, PASSWORD_FILE)
        win = tk.Toplevel(self.root)
        win.title("Zapisane wpisy")
        win.geometry("700x420")
        win.configure(bg="#202225")

        text = tk.Text(win, bg="#2F3136", fg="white", insertbackground="white", font=("Consolas", 12))
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

    def set_fallback_pin(self):
        cfg = config_manager.load_config()
        new_pin = sd.askstring("Ustaw PIN", "Podaj nowy PIN awaryjny:", show="*")
        if not new_pin:
            return
        confirm = sd.askstring("Potwierdź PIN", "Powtórz nowy PIN:", show="*")
        if new_pin != confirm:
            messagebox.showerror("Błąd", "PIN-y się różnią.")
            return
        cfg["pin"] = new_pin
        config_manager.save_config(cfg)
        messagebox.showinfo("Zapisano", "PIN awaryjny został ustawiony.")
