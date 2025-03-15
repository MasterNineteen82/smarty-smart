import sys
print(sys.executable)
print(sys.path)
import pyscard
from pyscard.smartcard.System import readers
print(f"pyscard version: {pyscard.__version__}")
print(f"Readers: {readers()}")