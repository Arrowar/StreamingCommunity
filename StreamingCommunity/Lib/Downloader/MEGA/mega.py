# 25-06-2020 By @rodwyer "https://pypi.org/project/mega.py/"

import os
import math
import re
import random
import binascii
import sys
import time
from pathlib import Path


# External libraries
import httpx
from tqdm import tqdm
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Util import Counter
from rich.console import Console


# Internal utilities
from .errors import RequestError
from .crypto import (
    a32_to_base64, encrypt_key, base64_url_encode,
    base64_to_a32, base64_url_decode,
    decrypt_attr, a32_to_str, get_chunks, str_to_a32,
    decrypt_key, mpi_to_int, make_id,
    modular_inverse
)

from StreamingCommunity.Util.color import Colors
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.os import internet_manager, os_manager
from StreamingCommunity.Util.headers import get_userAgent
from ...FFmpeg import print_duration_table


# Config
EXTENSION_OUTPUT = config_manager.get("M3U8_CONVERSION", "extension")


# Variable
console = Console()


class Mega_Downloader:
    def __init__(self, options=None):
        self.schema = 'https'
        self.domain = 'mega.co.nz'
        self.timeout = 160
        self.sid = None
        self.sequence_num = random.randint(0, 0xFFFFFFFF)
        self.request_id = make_id(10)
        self._trash_folder_node_id = None
        self.options = options or {}

    def login(self):
        self.login_anonymous()
        self._trash_folder_node_id = self.get_node_by_type(4)[0]
        return self

    def login_anonymous(self):
        master_key = [random.randint(0, 0xFFFFFFFF)] * 4
        password_key = [random.randint(0, 0xFFFFFFFF)] * 4
        session_self_challenge = [random.randint(0, 0xFFFFFFFF)] * 4

        user = self._api_request({
            'a': 'up',
            'k': a32_to_base64(encrypt_key(master_key, password_key)),
            'ts': base64_url_encode(
                a32_to_str(session_self_challenge) +
                a32_to_str(encrypt_key(session_self_challenge, master_key))
            )
        })

        resp = self._api_request({'a': 'us', 'user': user})
        if isinstance(resp, int):
            raise RequestError(resp)
        self._login_process(resp, password_key)

    def _login_process(self, resp, password):
        encrypted_master_key = base64_to_a32(resp['k'])
        self.master_key = decrypt_key(encrypted_master_key, password)
        
        if 'tsid' in resp:
            tsid = base64_url_decode(resp['tsid'])
            key_encrypted = a32_to_str(
                encrypt_key(str_to_a32(tsid[:16]), self.master_key)
            )

            if key_encrypted == tsid[-16:]:
                self.sid = resp['tsid']

        elif 'csid' in resp:
            encrypted_rsa_private_key = base64_to_a32(resp['privk'])
            rsa_private_key = decrypt_key(encrypted_rsa_private_key, self.master_key)

            private_key = a32_to_str(rsa_private_key)
            rsa_private_key = [0, 0, 0, 0]
            
            for i in range(4):
                bitlength = (private_key[0] * 256) + private_key[1]
                bytelength = math.ceil(bitlength / 8) + 2
                rsa_private_key[i] = mpi_to_int(private_key[:bytelength])
                private_key = private_key[bytelength:]

            first_factor_p = rsa_private_key[0]
            second_factor_q = rsa_private_key[1]
            private_exponent_d = rsa_private_key[2]
            rsa_modulus_n = first_factor_p * second_factor_q
            phi = (first_factor_p - 1) * (second_factor_q - 1)
            public_exponent_e = modular_inverse(private_exponent_d, phi)

            rsa_components = (
                rsa_modulus_n,
                public_exponent_e,
                private_exponent_d,
                first_factor_p,
                second_factor_q,
            )
            rsa_decrypter = RSA.construct(rsa_components)
            encrypted_sid = mpi_to_int(base64_url_decode(resp['csid']))
            sid = '%x' % rsa_decrypter._decrypt(encrypted_sid)
            sid = binascii.unhexlify('0' + sid if len(sid) % 2 else sid)
            self.sid = base64_url_encode(sid[:43])

    def _api_request(self, data):
        params = {'id': self.sequence_num}
        self.sequence_num += 1

        if self.sid:
            params['sid'] = self.sid

        if not isinstance(data, list):
            data = [data]

        url = f'{self.schema}://g.api.{self.domain}/cs'
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, params=params, json=data)
            json_resp = response.json()
        
        int_resp = None
        try:
            if isinstance(json_resp, list):
                int_resp = json_resp[0] if isinstance(json_resp[0], int) else None
            elif isinstance(json_resp, int):
                int_resp = json_resp
        except IndexError:
            pass
        
        if int_resp is not None:
            if int_resp == 0:
                return int_resp
            if int_resp == -3:
                raise RuntimeError('Request failed, retrying')
            raise RequestError(int_resp)
        
        return json_resp[0]

    def _parse_url(self, url):
        """Parse file id and key from url."""
        if '/file/' in url:
            url = url.replace(' ', '')
            file_id = re.findall(r'\W\w{8}\W', url)[0][1:-1]
            id_index = re.search(file_id, url).end()
            key = url[id_index + 1:]
            return f'{file_id}!{key}'
        
        elif '!' in url:
            match = re.findall(r'/#!(.*)', url)
            return match[0]
        
        else:
            raise RequestError('Url key missing')

    def get_node_by_type(self, node_type):
        """Get node by type (2=root, 3=inbox, 4=trash)"""
        files = self._api_request({'a': 'f', 'c': 1, 'r': 1})
        for file in files['f']:
            if file['t'] == node_type:
                return (file['h'], file)
            
        return None

    def download_url(self, url, dest_path=None):
        """Download a file by its public url"""
        path_obj = Path(dest_path)
        folder = str(path_obj.parent)
        name = path_obj.name.replace(EXTENSION_OUTPUT, f".{EXTENSION_OUTPUT}")
        os_manager.create_path(folder)

        path = self._parse_url(url).split('!')
        file_id = path[0]
        file_key = path[1]
        
        return self._download_file(
            file_handle=file_id,
            file_key=file_key,
            dest_path=os.path.join(folder, name)
        )

    def _download_file(self, file_handle, file_key, dest_path=None):
        file_key = base64_to_a32(file_key)
        file_data = self._api_request({
            'a': 'g',
            'g': 1,
            'p': file_handle
        })

        k = (file_key[0] ^ file_key[4], file_key[1] ^ file_key[5],
             file_key[2] ^ file_key[6], file_key[3] ^ file_key[7])
        iv = file_key[4:6] + (0, 0)
        meta_mac = file_key[6:8]

        if 'g' not in file_data:
            raise RequestError('File not accessible anymore')
        
        file_url = file_data['g']
        file_size = file_data['s']
        attribs = base64_url_decode(file_data['at'])
        attribs = decrypt_attr(attribs, k)

        file_name = os_manager.get_sanitize_file(attribs['n'])
        output_path = Path(dest_path) if dest_path else Path(file_name)
        os_manager.create_path(output_path.parent)

        k_str = a32_to_str(k)
        counter = Counter.new(
            128,
            initial_value=((iv[0] << 32) + iv[1]) << 64
        )
        aes = AES.new(k_str, AES.MODE_CTR, counter=counter)

        mac_str = '\0' * 16
        mac_encryptor = AES.new(k_str, AES.MODE_CBC, mac_str.encode("utf8"))
        iv_str = a32_to_str([iv[0], iv[1], iv[0], iv[1]])

        start_time = time.time()
        downloaded = 0

        console.print("[cyan]You can safely stop the download with [bold]Ctrl+c[bold] [cyan]")
        with open(output_path, 'wb') as output_file:
            with httpx.Client(timeout=None, headers={'User-Agent': get_userAgent()}) as client:
                with client.stream('GET', file_url, headers={'User-Agent': get_userAgent()}) as response:
                    response.raise_for_status()
                    
                    progress_bar = tqdm(
                        total=file_size,
                        ascii='░▒█',
                        bar_format=f"{Colors.YELLOW}MEGA{Colors.CYAN} Downloading{Colors.WHITE}: "
                                   f"{Colors.MAGENTA}{{bar:40}} "
                                   f"{Colors.LIGHT_GREEN}{{n_fmt}}{Colors.WHITE}/{Colors.CYAN}{{total_fmt}}"
                                   f" {Colors.DARK_GRAY}[{Colors.YELLOW}{{elapsed}}{Colors.WHITE} < {Colors.CYAN}{{remaining}}{Colors.DARK_GRAY}]"
                                   f"{Colors.WHITE}{{postfix}} ",
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024,
                        mininterval=0.05,
                        file=sys.stdout
                    )
                    
                    with progress_bar:
                        chunks_data = list(get_chunks(file_size))
                        stream_iter = response.iter_bytes(chunk_size=8192)
                        
                        for chunk_start, chunk_size in chunks_data:
                            chunk = b''
                            remaining = chunk_size
                            
                            while remaining > 0:
                                try:
                                    data = next(stream_iter)
                                    to_read = min(len(data), remaining)
                                    chunk += data[:to_read]
                                    remaining -= to_read
                                except StopIteration:
                                    break
                            
                            chunk = aes.decrypt(chunk)
                            output_file.write(chunk)
                            
                            downloaded += len(chunk)
                            progress_bar.update(len(chunk))
                            
                            # Update postfix with speed
                            elapsed = time.time() - start_time
                            if elapsed > 0:
                                speed = downloaded / elapsed
                                speed_str = internet_manager.format_transfer_speed(speed)
                                postfix_str = f"{Colors.LIGHT_MAGENTA}@ {Colors.LIGHT_CYAN}{speed_str}"
                                progress_bar.set_postfix_str(postfix_str)

                            encryptor = AES.new(k_str, AES.MODE_CBC, iv_str)
                            for i in range(0, len(chunk) - 16, 16):
                                block = chunk[i:i + 16]
                                encryptor.encrypt(block)

                            if file_size > 16:
                                i += 16
                            else:
                                i = 0

                            block = chunk[i:i + 16]
                            if len(block) % 16:
                                block += b'\0' * (16 - (len(block) % 16))
                            mac_str = mac_encryptor.encrypt(encryptor.encrypt(block))

        file_mac = str_to_a32(mac_str)
        if (file_mac[0] ^ file_mac[1], file_mac[2] ^ file_mac[3]) != meta_mac:
            if output_path.exists():
                output_path.unlink()
            raise ValueError('Mismatched mac')
        
        # Display file information
        file_size = internet_manager.format_file_size(os.path.getsize(output_path))
        duration = print_duration_table(output_path, description=False, return_string=True) 
        console.print(f"[yellow]Output[white]: [red]{os.path.abspath(output_path)} \n"
            f"  [cyan]with size[white]: [red]{file_size} \n"
            f"      [cyan]and duration[white]: [red]{duration}")