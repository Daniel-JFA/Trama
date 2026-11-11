"""
crypto.py — Utilidades de cifrado simétrico en reposo para tokens OAuth.
Sprint 5.5 — Seguimiento de Creadores, Crecimiento y Nichos.
"""

import os
from typing import Optional, Union
from cryptography.fernet import Fernet, InvalidToken


def generate_token_key() -> str:
    """Genera una clave válida de 32 bytes en base64 url-safe para Fernet."""
    return Fernet.generate_key().decode("utf-8")


def _get_fernet(key: Optional[Union[str, bytes]] = None) -> Fernet:
    """Obtiene la instancia de Fernet usando la clave proporcionada o TRAMA_TOKEN_KEY."""
    raw_key = key or os.getenv("TRAMA_TOKEN_KEY")
    if not raw_key:
        raise ValueError("Clave de cifrado no configurada: defina TRAMA_TOKEN_KEY o pase 'key'.")

    if isinstance(raw_key, str):
        raw_key = raw_key.strip().encode("utf-8")

    try:
        return Fernet(raw_key)
    except Exception as exc:
        raise ValueError(f"Clave de cifrado inválida para Fernet: {exc}") from exc


def encrypt_token(plain_token: str, key: Optional[Union[str, bytes]] = None) -> str:
    """
    Cifra un token sensible en texto plano y retorna el texto cifrado en base64.
    """
    if not plain_token:
        return ""
    f = _get_fernet(key)
    encrypted_bytes = f.encrypt(plain_token.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_token(cipher_token: str, key: Optional[Union[str, bytes]] = None) -> str:
    """
    Descifra un token cifrado previamente con encrypt_token.
    """
    if not cipher_token:
        return ""
    f = _get_fernet(key)
    try:
        decrypted_bytes = f.decrypt(cipher_token.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("No se pudo descifrar el token: token corrupto o clave incorrecta.") from exc
