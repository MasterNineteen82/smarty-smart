def load_key():
    try:
        with open(".encryption_key", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        # Generate and save new key
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        with open(".encryption_key", "w") as f:
            f.write(key)
        return key