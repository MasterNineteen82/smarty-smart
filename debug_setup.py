import sys
import os
import subprocess

print("=== Smart Card Manager Debug ===")
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Python path: {sys.path}")

required_packages = {
    "pyscard": "smartcard",  # The actual import name might be different
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "werkzeug": "werkzeug",
    "cryptography": "cryptography",
    "pyopenssl": "OpenSSL",  # Actual import name is OpenSSL
    "python-dateutil": "dateutil"  # Actual import name is dateutil
}

print("\nChecking required packages:")
for package_name, import_name in required_packages.items():
    try:
        __import__(import_name)
        print(f"✓ {package_name} is installed (imported {import_name})")
    except ImportError as e:
        print(f"✗ {package_name} is NOT imported correctly: {e}")

print("\nChecking PC/SC Service:")
try:
    if os.name == 'nt':  # Windows
        result = subprocess.run(['sc', 'query', 'SCardSvr'], 
                               capture_output=True, 
                               text=True)
        if "RUNNING" in result.stdout:
            print("✓ PC/SC Service is running")
        else:
            print("✗ PC/SC Service is NOT running")
except Exception as e:
    print(f"Error checking service: {e}")

print("\nPlease share this output to help diagnose the issue.")
input("Press Enter to exit...")