import os, sys, json, requests, zipfile, subprocess, tempfile, base64
from tkinter import messagebox
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
PUBLIC_KEY_PEM=b"""-----BEGIN PUBLIC KEY----- MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAs3zRigkJ22weSHhiI+qkk5pirPfGuuDrokQtxJSol7EKFcHUn5dkuhxa8PNVKpyiw5xZ5pSrFr/zQOlSlgmVogRLKO1KODzBYyRt24h7+46Ee/ngwrSAe6e14JZVLg5JMpu9nuBs+63vC0HqCijryi7WhRQg89mtW7v1JiS2zdtuilIbhX8IE9/QFpPLI92guCwEmgdDBkt8/MrIP4CcIG8HYdhWd3i9fk/SAFqmLwVi/Mngv8LFT1tAfQOb1E/IFgaton7SqIX7xJs8brzaZQEqTZG3EQOjzSpwr6C79wfSfW2UY+uUIprrAUKd4UALPFOSFmBZyoMWvnHj1RKpCJ4SiSWsn1C822pl9HagExfwch3st+/A5VXPvP02K1Eq5N++KzI9rYAB4ARsrQbdbZMo7YJxjJN67OkNugHHHHuNgP/RlTG8lqQCEnO1A5PgRwdDW1ymgHrw2mZSZE2F2hsCCBbFUN2n/RfGSNOLKqTDpWT2/CqAiJwEfAArwwwRhcH74Pi6dM8ohwWlkMbSO1tl4fGYNhiLZ0BZkJIsJyV7ulFyrRb8FaVZEGqeiPxRka1IsiEHoKuSqHdEPnDVRh4JjXlJKN/D3ksNmFNWWEaaajxAUHZUvZbxud8fjbXKpezYlPvccvboyFr7ecY+EHCGxjhG7qbUrvYhLdeQi8ECAwEAAQ== -----END PUBLIC KEY-----"""
def verify_zip_signature(zip_bytes:bytes,signature_b64:str)->bool:
    try:
        public_key=serialization.load_pem_public_key(PUBLIC_KEY_PEM)
        signature=base64.b64decode(signature_b64)
        public_key.verify(signature,zip_bytes,padding.PKCS1v15(),hashes.SHA256())
        print("✅ Weryfikacja podpisu ZIP OK.")
        return True
    except Exception as e:
        print(f"❌ Weryfikacja podpisu nie powiodła się: {e}")
        return False
def get_local_version():
    try:
        with open("version.txt","r",encoding="utf-8") as f:return f.read().strip()
    except FileNotFoundError:
        return "0.0"
def check_for_updates(current_version:str,manifest_url:str):
    try:
        response=requests.get(manifest_url,timeout=10)
        response.raise_for_status()
        manifest=response.json()
    except Exception as e:
        print(f"[Błąd aktualizacji] Nie udało się pobrać manifestu: {e}")
        return None
    latest_version=manifest.get("version","0.0")
    print(f"[Aktualizacja] Lokalna: {current_version}, najnowsza: {latest_version}")
    if latest_version==current_version:
        print("[Aktualizacja] Brak nowych wersji.")
        return None
    return manifest
def perform_update_flow(manifest:dict):
    version=manifest.get("version","Nieznana")
    download_url=manifest.get("download_url")
    sig_url=manifest.get("sig_url")
    if not download_url:
        messagebox.showerror("Błąd","Nie znaleziono linku do aktualizacji w manifest.json.")
        return
    try:
        print(f"[Aktualizacja] Pobieranie wersji {version} z {download_url}...")
        zip_data=requests.get(download_url,timeout=30).content
        if sig_url:
            print("[Aktualizacja] Sprawdzanie podpisu...")
            sig_data=requests.get(sig_url,timeout=10).content
            sig_b64=base64.b64encode(sig_data).decode()
            if not verify_zip_signature(zip_data,sig_b64):
                messagebox.showerror("Błąd","Niepoprawny podpis aktualizacji. Anulowano.")
                return
        app_dir=os.path.dirname(os.path.abspath(sys.argv[0]))
        tmp_dir=os.path.join(app_dir,"_update_tmp")
        os.makedirs(tmp_dir,exist_ok=True)
        zip_path=os.path.join(tmp_dir,f"update_{version}.zip")
        with open(zip_path,"wb") as f:f.write(zip_data)
        with zipfile.ZipFile(zip_path,"r") as zip_ref:zip_ref.extractall(tmp_dir)
        os.remove(zip_path)
        for root_dir,_,files in os.walk(tmp_dir):
            for file in files:
                src=os.path.join(root_dir,file)
                rel_path=os.path.relpath(src,tmp_dir)
                dst=os.path.join(app_dir,rel_path)
                os.makedirs(os.path.dirname(dst),exist_ok=True)
                try:os.replace(src,dst)
                except PermissionError:print(f"⚠️ Nie można zastąpić pliku: {dst}")
        try:
            for root_dir,dirs,files in os.walk(tmp_dir,topdown=False):
                for name in files:os.remove(os.path.join(root_dir,name))
                for name in dirs:os.rmdir(os.path.join(root_dir,name))
            os.rmdir(tmp_dir)
        except Exception:pass
        with open(os.path.join(app_dir,"version.txt"),"w",encoding="utf-8") as vf:vf.write(version)
        messagebox.showinfo("Aktualizacja",f"Pomyślnie zaktualizowano do wersji {version}!")
        exe_path=os.path.join(app_dir,os.path.basename(sys.argv[0]))
        print(f"[Restart] Uruchamianie ponownie: {exe_path}")
        subprocess.Popen([exe_path])
        os._exit(0)
    except Exception as e:
        messagebox.showerror("Błąd aktualizacji",f"Nie udało się przeprowadzić aktualizacji:\n{e}")
        print(f"[Błąd aktualizacji] {e}")
