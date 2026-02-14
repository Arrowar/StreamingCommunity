# 19.05.25

import os
import re
import subprocess
import shutil
import logging


# External import 
from rich.console import Console
try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import unpad
except:
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import unpad
    except: 
        logging.warning("PyCryptodome not found, HLS segment decryption will not work. Install with 'pip install pycryptodome' for AES-128-CBC support.")


# Internal import
from StreamingCommunity.setup import get_bento4_decrypt_path, get_mp4dump_path, get_shaka_packager_path


# Variable
logger = logging.getLogger(__name__)
console = Console()


class Decryptor:
    def __init__(self, preference: str = "bento4"):
        self.preference = preference.lower()
        self.mp4decrypt_path = get_bento4_decrypt_path()
        self.mp4dump_path = get_mp4dump_path()
        self.shaka_packager_path = get_shaka_packager_path()
    
    def detect_encryption(self, file_path):
        """Detect encryption scheme using mp4dump. Returns 'ctr', 'cbc', or None if not encrypted."""
        logger.info(f"Detecting encryption: {os.path.basename(file_path)}")
        
        try:
            cmd = [self.mp4dump_path, file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return None
            
            output = result.stdout
            
            if '[tenc]' not in output:
                logger.info("File not encrypted")
                return None
            
            scheme_match = re.search(r'scheme_type\s*=\s*(\w+)', output, re.IGNORECASE)
            if scheme_match:
                scheme = scheme_match.group(1).lower()
                logger.info(f"Encryption scheme: {scheme}")
                if scheme in ['cenc', 'cens']:
                    return 'ctr'
                elif scheme in ['cbcs', 'cbc1']:
                    return 'cbc'
            
            return 'ctr'
            
        except Exception as e:
            logger.warning(f"Encryption detection failed: {e}")
            return None
    
    def decrypt(self, encrypted_path, keys, output_path, stream_type: str = "video"):
        """Decrypt a file using the preferred method. Returns True on success."""
        try:
            encryption = self.detect_encryption(encrypted_path)
            if encryption is None:
                shutil.copy(encrypted_path, output_path)
                console.print("[dim]Not encrypted, copied")
                return True
            
            console.print(f"[dim]Decrypting ({encryption.upper()}) with {self.preference}...")
            if isinstance(keys, str):
                keys = [keys]

            if self.preference == "shaka" and self.shaka_packager_path:
                return self._decrypt_shaka(encrypted_path, keys, output_path, stream_type)
            else:
                return self._decrypt_bento4(encrypted_path, keys, output_path)
                
        except Exception as e:
            console.print(f"[red]Decryption error: {e}.")
            return False

    def _decrypt_bento4(self, encrypted_path, keys, output_path):
        """Decrypt a file using Bento4. Returns True on success."""
        cmd = [self.mp4decrypt_path]
        for single_key in keys:
            if ":" in single_key:
                kid, key_val = single_key.split(":", 1)
                cmd.extend(["--key", f"{kid.lower()}:{key_val.lower()}"])
            else:
                cmd.extend(["--key", single_key.lower()])

        cmd.extend([encrypted_path, output_path])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
        else:
            console.print(f"[red]Bento4 Decryption failed: {result.stderr.strip()}.")
            return False

    def _decrypt_shaka(self, encrypted_path, keys, output_path, stream_type):
        """Decrypt a file using Shaka Packager. Returns True on success."""
        cmd = [self.shaka_packager_path]
        
        # Build stream specifier
        stream_spec = f"input='{encrypted_path}',stream={stream_type},output='{output_path}'"
        cmd.append(stream_spec)
        cmd.append("--enable_fixed_key_decryption")
        
        keys_arg = []
        for single_key in keys:
            if ":" in single_key:
                kid, key_val = single_key.split(":", 1)
                keys_arg.append(f"key_id={kid.lower()}:key={key_val.lower()}")
            else:
                keys_arg.append(f"key={single_key.lower()}")
        
        if keys_arg:
            cmd.extend(["--keys", ",".join(keys_arg)])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
        else:
            if "stream=" in stream_spec:
                logger.debug("Shaka decryption failed with stream type, retrying without it...")
                cmd_retry = [self.shaka_packager_path, f"input='{encrypted_path}',output='{output_path}'", "--enable_fixed_key_decryption"]
                if keys_arg: 
                    cmd_retry.extend(["--keys", ",".join(keys_arg)])
                
                result_retry = subprocess.run(cmd_retry, capture_output=True, text=True, timeout=300)
                if result_retry.returncode == 0 and os.path.exists(output_path):
                    return True

            console.print(f"[red]Shaka Decryption failed: {result.stderr.strip()}.")
            return False
    
    def decrypt_hls_segment(self, encrypted_path, key_data, iv, output_path):
        """Decrypt an HLS segment using AES-128-CBC. Returns True on success."""
        logger.info(f"Decrypting HLS segment: {os.path.basename(encrypted_path)}")
        
        try:
            with open(encrypted_path, 'rb') as f:
                encrypted_data = f.read()
            
            iv_bytes = bytes.fromhex(iv)
            cipher = AES.new(key_data, AES.MODE_CBC, iv_bytes)
            decrypted_data = cipher.decrypt(encrypted_data)
            decrypted_data = unpad(decrypted_data, AES.block_size)
            
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            return True
                
        except Exception as e:
            logger.exception(f"HLS segment decryption error: {e}")
            return False