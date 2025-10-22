import tkinter as tk
from tkinter import messagebox
import random
import string
import os
import subprocess
from updater import check_for_updates


FILENAME = "Hasła.txt"
VERSION_TXT_DEFAULT = "1.0.0"
MANIFEST_URL = "https://raw.githubusercontent.com/codepass0v12/Codepass/main/update.json"



def get_local_version():
    try:
        with open("version.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return VERSION_TXT_DEFAULT


class CodePassGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CodePass 1.30")
        self.root.geometry("700x640")
        self.root.configure(bg="#101319")
        self.root.resizable(False, False)

        # zmienne
        self.length_var = tk.StringVar(value="12")
        self.upper_var = tk.BooleanVar(value=True)
        self.special_var = tk.BooleanVar(value=True)
        self.password_var = tk.StringVar()
        self.domain_var = tk.StringVar()
        self.login_var = tk.StringVar()

        self.FONT_MAIN = ("Segoe UI", 12)
        self.FONT_BTN = ("Segoe UI Semibold", 11)
        self.FONT_TITLE = ("Segoe UI Semibold", 22, "bold")

        self.build_ui()

    def rounded_entry(self, parent, textvariable=None, width=25):
        """Tworzy pole z zaokrągloną ramką"""
        frame = tk.Frame(parent, bg="#101319", highlightbackground="#3a3f4b",
                         highlightcolor="#3a3f4b", highlightthickness=1, bd=0)
        entry = tk.Entry(frame, textvariable=textvariable, width=width,
                         bg="#0d1117", fg="#ffffff", relief="flat",
                         justify="center", font=self.FONT_MAIN)
        entry.pack(ipady=6)
        frame.pack(pady=4)
        return entry

    def build_ui(self):
        # Nagłówek
        tk.Label(self.root, text="🔐 CodePass", font=self.FONT_TITLE,
                 fg="#38bdf8", bg="#101319").pack(pady=(30, 8))
        tk.Label(self.root, text="Nowoczesny generator bezpiecznych haseł",
                 fg="#b0b8c3", bg="#101319", font=("Segoe UI", 11)).pack(pady=(0, 25))

        # Ustawienia
        settings = tk.Frame(self.root, bg="#181c25")
        settings.pack(padx=30, pady=10, fill="x")

        tk.Label(settings, text="Długość hasła:", font=self.FONT_MAIN,
                 fg="#e5e7eb", bg="#181c25").grid(row=0, column=0, padx=15, pady=12, sticky="w")

        self.length_entry = tk.Entry(settings, textvariable=self.length_var, width=6, justify="center",
                                     bg="#0d1117", fg="#ffffff", relief="flat", font=self.FONT_MAIN)
        self.length_entry.grid(row=0, column=1, padx=8)

        tk.Checkbutton(settings, text="Duże litery", variable=self.upper_var,
                       bg="#181c25", fg="#e5e7eb", selectcolor="#181c25",
                       font=self.FONT_MAIN).grid(row=1, column=0, padx=15, pady=8, sticky="w")
        tk.Checkbutton(settings, text="Znaki specjalne", variable=self.special_var,
                       bg="#181c25", fg="#e5e7eb", selectcolor="#181c25",
                       font=self.FONT_MAIN).grid(row=1, column=1, padx=8, pady=8, sticky="w")

        # Generowanie
        tk.Button(self.root, text="🔁 GENERUJ HASŁO", command=self.generate_password,
                  bg="#2563eb", fg="white", relief="flat",
                  activebackground="#3b82f6", activeforeground="white",
                  font=self.FONT_BTN, padx=20, pady=8, width=22).pack(pady=20)

        # Hasło z przyciskiem kopiowania
        pw_frame = tk.Frame(self.root, bg="#101319")
        pw_frame.pack(pady=10)

        self.password_entry = tk.Entry(pw_frame, textvariable=self.password_var, width=36,
                                       font=("Consolas", 13), justify="center",
                                       bg="#0d1117", fg="#00eaff", relief="flat")
        self.password_entry.pack(side="left", ipady=6, padx=(0, 8))

        tk.Button(pw_frame, text="📋", bg="#272b33", fg="#e5e7eb",
                  font=("Segoe UI", 11), relief="flat", padx=8, command=self.copy_password).pack(side="left")

        # Domena / login
        form = tk.Frame(self.root, bg="#101319")
        form.pack(pady=(20, 10))

        tk.Label(form, text="Domena / serwis:", bg="#101319", fg="#e5e7eb", font=self.FONT_MAIN).pack()
        self.rounded_entry(form, self.domain_var)

        tk.Label(form, text="Login:", bg="#101319", fg="#e5e7eb", font=self.FONT_MAIN).pack(pady=(10, 0))
        self.rounded_entry(form, self.login_var)

        # Zapis / aktualizacja
        tk.Button(self.root, text="💾 ZAPISZ HASŁO", bg="#16a34a", fg="white",
                  activebackground="#22c55e", relief="flat",
                  font=self.FONT_BTN, padx=20, pady=8, width=22,
                  command=self.save_password).pack(pady=(25, 10))

        tk.Button(self.root, text="🔄 SPRAWDŹ AKTUALIZACJE", bg="#f97316", fg="white",
                  activebackground="#fb923c", relief="flat",
                  font=self.FONT_BTN, padx=20, pady=8, width=22,
                  command=self.check_update_now).pack(pady=(5, 15))

        tk.Label(self.root, text=f"Wersja: {get_local_version()}",
                 bg="#101319", fg="#6b7280", font=("Segoe UI", 10)).pack(side="bottom", pady=10)

    # === Logika ===
    def generate_password(self):
        try:
            length = int(self.length_var.get())
            if length < 7:
                messagebox.showinfo("Info", "Minimalna długość to 7.")
                length = 7
        except ValueError:
            messagebox.showerror("Błąd", "Podaj poprawną długość (liczba).")
            return

        chars = string.ascii_lowercase + string.digits
        if self.upper_var.get():
            chars += string.ascii_uppercase
        if self.special_var.get():
            chars += string.punctuation

        password = "".join(random.choices(chars, k=length))
        self.password_var.set(password)

    def copy_password(self):
        pw = self.password_var.get().strip()
        if not pw:
            messagebox.showwarning("Kopiowanie", "Brak hasła do skopiowania.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(pw)
        messagebox.showinfo("Kopiowanie", "Hasło zostało skopiowane do schowka.")

    def save_password(self):
        pw = self.password_var.get().strip()
        domain = self.domain_var.get().strip()
        login = self.login_var.get().strip()

        if not pw:
            messagebox.showerror("Błąd", "Najpierw wygeneruj hasło.")
            return
        if not domain or not login:
            messagebox.showerror("Błąd", "Podaj domenę i login.")
            return

        lines = []
        if os.path.exists(FILENAME):
            with open(FILENAME, "r", encoding="utf-8") as f:
                lines = [ln for ln in f.readlines() if ln.strip()]
        next_nr = len(lines) + 1

        with open(FILENAME, "a", encoding="utf-8") as f:
            f.write(f"{next_nr}. {domain} - {login} - {pw}\n")

        messagebox.showinfo("Zapisano", f"Zapisano pozycję #{next_nr} w {FILENAME}.")
        self.domain_var.set("")
        self.login_var.set("")

        # otwórz plik po zapisaniu
        try:
            os.startfile(FILENAME)
        except Exception:
            subprocess.Popen(["notepad", FILENAME])


def check_update_now(self):
    """Wywołuje ręczne sprawdzenie aktualizacji"""
    try:
        check_for_updates()  # nowa wersja updatera robi wszystko sama
    except Exception as e:
        messagebox.showerror("Błąd aktualizacji", f"Nie udało się sprawdzić aktualizacji:\n{e}")
