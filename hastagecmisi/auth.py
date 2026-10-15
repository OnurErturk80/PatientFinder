"""PIN koruması (telefon/LAN erişimi için zorunlu). Yalnızca standart kütüphane.

PIN scrypt ile saklanır, deneme sayısı sınırlıdır, oturum boşta kalınca kapanır.
Not: LAN'da bağlantı düz HTTP'dir; yalnızca güvenilir ev/iş ağında kullanın.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time

IDLE_SECONDS = 15 * 60
MAX_FAILS = 5
LOCK_SECONDS = 5 * 60


def _hash(pin: str, salt: bytes) -> str:
    return hashlib.scrypt(pin.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32).hex()


def set_pin(path: str, pin: str) -> None:
    if len(pin) < 6:
        raise ValueError("PIN en az 6 karakter olmalı.")
    salt = secrets.token_bytes(16)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"salt": salt.hex(), "hash": _hash(pin, salt)}, f)


def has_pin(path: str) -> bool:
    return os.path.exists(path)


class Auth:
    def __init__(self, pin_path: str, clock=time.time):
        self.pin_path, self.clock = pin_path, clock
        self.sessions: dict[str, float] = {}
        self.fails: dict[str, list] = {}  # ip -> [sayı, kilit_bitişi]

    def locked(self, ip: str) -> bool:
        f = self.fails.get(ip)
        return bool(f and f[1] > self.clock())

    def login(self, ip: str, pin: str) -> str | None:
        """Başarılıysa oturum belirteci, değilse None."""
        if self.locked(ip):
            return None
        with open(self.pin_path) as f:
            d = json.load(f)
        if hmac.compare_digest(_hash(pin, bytes.fromhex(d["salt"])), d["hash"]):
            self.fails.pop(ip, None)
            tok = secrets.token_urlsafe(32)
            self.sessions[tok] = self.clock() + IDLE_SECONDS
            return tok
        f = self.fails.setdefault(ip, [0, 0])
        f[0] += 1
        if f[0] >= MAX_FAILS:
            f[0], f[1] = 0, self.clock() + LOCK_SECONDS
        return None

    def valid(self, token: str | None) -> bool:
        exp = self.sessions.get(token or "")
        if not exp or exp < self.clock():
            self.sessions.pop(token or "", None)
            return False
        self.sessions[token] = self.clock() + IDLE_SECONDS  # boşta kalma süresini yenile
        return True
