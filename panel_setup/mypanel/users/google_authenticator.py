import base64
import hashlib
import hmac
import struct
import time
import urllib.parse
from typing import Optional

class GoogleAuthenticator:
    def __init__(self, code_length: int = 6):
        self._code_length = code_length

    # === 1. Create Secret (Base32) ===
    def create_secret(self, secret_length: int = 16) -> str:
        valid_chars = self._get_base32_lookup_table()[:-1]  # remove '='
        import random
        return ''.join(random.choice(valid_chars) for _ in range(secret_length))

    # === 2. Generate Code (TOTP) ===
    def get_code(self, secret: str, time_slice: Optional[int] = None) -> str:
        if time_slice is None:
            time_slice = int(time.time() // 30)

        secret_key = self._base32_decode(secret)
        time_bytes = struct.pack(">Q", time_slice)
        hm = hmac.new(secret_key, time_bytes, hashlib.sha1).digest()
        offset = hm[-1] & 0x0F
        value = struct.unpack(">I", hm[offset:offset + 4])[0] & 0x7FFFFFFF
        return str(value % (10 ** self._code_length)).zfill(self._code_length)

    # === 3. Generate Google Chart QR URL ===
    def get_qrcode_google_url(self, provider: str, name: str, secret: str) -> str:
    
        otpauth_url = f"otpauth://totp/{provider}:{name}?secret={secret}&issuer={provider}"
        return otpauth_url


    # === 4. Verify Code (allow time drift) ===
    def verify_code(self, secret: str, code: str, discrepancy: int = 1) -> bool:
        current_slice = int(time.time() // 30)
        for i in range(-discrepancy, discrepancy + 1):
            if self.get_code(secret, current_slice + i) == str(code).zfill(self._code_length):
                return True
        return False

    # === 5. Optional: Change code length ===
    def set_code_length(self, length: int):
        self._code_length = length

    # === Base32 Decode ===
    def _base32_decode(self, secret: str) -> bytes:
        secret = secret.strip().replace(" ", "").upper()
        # Add padding if necessary
        missing_padding = len(secret) % 8
        if missing_padding:
            secret += "=" * (8 - missing_padding)
        return base64.b32decode(secret, casefold=True)

    # === Base32 Encode ===
    def _base32_encode(self, data: bytes) -> str:
        return base64.b32encode(data).decode('utf-8')

    # === Lookup Table (for reference) ===
    def _get_base32_lookup_table(self):
        return [
            'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
            'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P',
            'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X',
            'Y', 'Z', '2', '3', '4', '5', '6', '7', '='
        ]
