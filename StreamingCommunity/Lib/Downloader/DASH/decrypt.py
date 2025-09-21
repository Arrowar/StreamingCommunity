# 25.07.25

import os
import subprocess
import logging


# External libraries
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.os import get_mp4decrypt_path

# Variable
console = Console()


def decrypt_with_mp4decrypt(encrypted_path, kid, key, output_path=None, cleanup=True):
    """
    Decrypt an mp4/m4s file using mp4decrypt.

    Args:
        encrypted_path (str): Path to encrypted file.
        kid (str): Hexadecimal KID.
        key (str): Hexadecimal key.
        output_path (str): Output decrypted file path (optional).
        cleanup (bool): If True, remove temporary files after decryption.

    Returns:
        str: Path to decrypted file, or None if error.
    """

    # Check if input file exists
    if not os.path.isfile(encrypted_path):
        console.print(f"[bold red] Encrypted file not found: {encrypted_path}[/bold red]")
        return None

    # Check if kid and key are valid hex
    try:
        bytes.fromhex(kid)
        bytes.fromhex(key)
    except Exception:
        console.print("[bold red] Invalid KID or KEY (not hex).[/bold red]")
        return None

    if not output_path:
        output_path = os.path.splitext(encrypted_path)[0] + "_decrypted.mp4"

    key_format = f"{kid.lower()}:{key.lower()}"
    cmd = [get_mp4decrypt_path(), "--key", key_format, encrypted_path, output_path]
    logging.info(f"Running command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except Exception as e:
        console.print(f"[bold red] mp4decrypt execution failed: {e}[/bold red]")
        return None

    if result.returncode == 0 and os.path.exists(output_path):

        # Cleanup temporary files if requested
        if cleanup:
            if os.path.exists(encrypted_path):
                os.remove(encrypted_path)

            temp_dec = os.path.splitext(encrypted_path)[0] + "_decrypted.mp4"

            # Do not delete the final output!
            if temp_dec != output_path and os.path.exists(temp_dec):
                os.remove(temp_dec)

        # Check if output file is not empty
        if os.path.getsize(output_path) == 0:
            console.print(f"[bold red] Decrypted file is empty: {output_path}[/bold red]")
            return None

        return output_path

    else:
        console.print(f"[bold red] mp4decrypt failed:[/bold red] {result.stderr}")
        return None