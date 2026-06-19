"""AES-256-GCM PII encryption and HMAC-SHA-256 ticket ID derivation."""

from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.hmac import HMAC

_NONCE_SIZE = 12


def encrypt_pii(plaintext: str, key: bytes) -> bytes:
    nonce = os.urandom(_NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce + ciphertext


def decrypt_pii(ciphertext: bytes, key: bytes) -> str:
    nonce = ciphertext[:_NONCE_SIZE]
    payload = ciphertext[_NONCE_SIZE:]
    plaintext = AESGCM(key).decrypt(nonce, payload, None)
    return plaintext.decode("utf-8")


def derive_ticket_id(profile_uuid: str, pepper: bytes) -> str:
    hmac = HMAC(pepper, SHA256())
    hmac.update(profile_uuid.encode("utf-8"))
    return hmac.finalize().hex()
