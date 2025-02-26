# 03.04.24

import sys
import time
import logging
import importlib.util


# External library
from rich.console import Console


# Check if Cryptodome module is installed
console = Console()
crypto_spec = importlib.util.find_spec("Cryptodome")
crypto_installed = crypto_spec is not None

if not crypto_installed:
    console.log("[red]pycryptodomex non è installato. Per favore installalo. Leggi readme.md [Requirement].")
    sys.exit(0)

logging.info("[cyan]Decrypy use: Cryptodomex")
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import unpad



class M3U8_Decryption:
    """
    Class for decrypting M3U8 playlist content using AES with pycryptodomex.
    """
    def __init__(self, key: bytes, iv: bytes, method: str) -> None:
        """
        Initialize the M3U8_Decryption object.

        Parameters:
            key (bytes): The encryption key.
            iv (bytes): The initialization vector (IV).
            method (str): The encryption method.
        """
        self.key = key
        self.iv = iv
        if "0x" in str(iv):
            self.iv = bytes.fromhex(iv.replace("0x", ""))
        self.method = method

        # Pre-create the cipher based on the encryption method
        if self.method == "AES":
            self.cipher = AES.new(self.key, AES.MODE_ECB)
        elif self.method == "AES-128":
            self.cipher = AES.new(self.key[:16], AES.MODE_CBC, iv=self.iv)
        elif self.method == "AES-128-CTR":
            self.cipher = AES.new(self.key[:16], AES.MODE_CTR, nonce=self.iv)
        else:
            raise ValueError("Invalid or unsupported method")

    def decrypt(self, ciphertext: bytes) -> bytes:
        """
        Decrypt the ciphertext using the specified encryption method.

        Parameters:
            ciphertext (bytes): The encrypted content to decrypt.

        Returns:
            bytes: The decrypted content.
        """
        #start = time.perf_counter_ns()

        if self.method in {"AES", "AES-128"}:
            decrypted_data = self.cipher.decrypt(ciphertext)
            decrypted_content = unpad(decrypted_data, AES.block_size)
        elif self.method == "AES-128-CTR":
            decrypted_content = self.cipher.decrypt(ciphertext)
        else:
            raise ValueError("Invalid or unsupported method")

        """
        end = time.perf_counter_ns()

        # Calculate the elapsed time with high precision
        elapsed_nanoseconds = end - start
        elapsed_milliseconds = elapsed_nanoseconds / 1_000_000
        elapsed_seconds = elapsed_nanoseconds / 1_000_000_000

        # Log performance metrics
        logging.info("[Crypto Decryption Performance]")
        logging.info(f"Method: {self.method}")
        logging.info(f"Decryption Time: {elapsed_milliseconds:.4f} ms ({elapsed_seconds:.6f} s)")
        logging.info(f"Decrypted Content Length: {len(decrypted_content)} bytes")
        """
        return decrypted_content