from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import os

def generate_keys():
    key_dir = os.path.dirname(os.path.abspath(__file__))
    private_path = os.path.join(os.path.dirname(key_dir), "private_key.pem")
    public_path = os.path.join(os.path.dirname(key_dir), "public_key.pem")

    print("🔐 Generowanie nowych kluczy RSA 4096-bit...")

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )

    # Zapis klucza prywatnego
    with open(private_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Zapis klucza publicznego
    public_key = private_key.public_key()
    with open(public_path, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))

    print(f"✅ Wygenerowano:")
    print(f" - 🔑 {private_path}")
    print(f" - 🔓 {public_path}")

if __name__ == "__main__":
    generate_keys()
