# 19.05.25

import os
import re
import subprocess
import shutil
import logging


# External import 
from rich.console import Console
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
except ImportError:
    try:
        from Cryptodome.Cipher import AES
        from Cryptodome.Util.Padding import unpad
    except ImportError:
        raise ImportError("pycryptodomex or pycrypto is required for AES decryption")
    

# Internal import
from StreamingCommunity.setup import get_bento4_decrypt_path, get_mp4dump_path


# Variable
logger = logging.getLogger(__name__)
console = Console()


class Decryptor:
    def __init__(self):
        self.mp4decrypt_path = get_bento4_decrypt_path()
        self.mp4dump_path = get_mp4dump_path()
    
    def detect_encryption(self, file_path):
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
    
    def decrypt(self, encrypted_path, kid, key, output_path):
        logger.info(f"Decrypting: {os.path.basename(encrypted_path)}")
        
        try:
            encryption = self.detect_encryption(encrypted_path)
            if encryption is None:
                shutil.copy(encrypted_path, output_path)
                console.print("[dim]Not encrypted, copied")
                return True
            
            # FIX: ADD LIST OF KID:KEY
            console.print(f"[dim]Decrypting ({encryption.upper()})...[/dim]")
            kid_clean = kid.lower()
            key_lower = key.lower()
            
            cmd = [self.mp4decrypt_path, "--key", f"{kid_clean}:{key_lower}", encrypted_path, output_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                return True
            else:
                console.print(f"[red]Decryption failed: {result.stderr.strip()}.")
                return False
                
        except Exception as e:
            console.print(f"[red]Decryption error: {e}.")
            return False
    
    def decrypt_hls_segment(self, encrypted_path, key_data, iv, output_path):
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