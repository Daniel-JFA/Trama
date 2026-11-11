"""
test_crypto.py — Pruebas unitarias para cifrado y descifrado de tokens con Fernet.
"""

import os
import pytest
from app.crypto import encrypt_token, decrypt_token, generate_token_key


def test_roundtrip_encryption_with_explicit_key():
    key = generate_token_key()
    token = "secret_oauth_access_token_xyz_12345"

    cipher = encrypt_token(token, key=key)
    assert cipher != token
    assert isinstance(cipher, str)

    plain = decrypt_token(cipher, key=key)
    assert plain == token


def test_roundtrip_encryption_with_env_key(monkeypatch):
    key = generate_token_key()
    monkeypatch.setenv("TRAMA_TOKEN_KEY", key)

    token = "ya29.a0AfH6SMD...sample_refresh_token"
    cipher = encrypt_token(token)
    assert cipher != token

    plain = decrypt_token(cipher)
    assert plain == token


def test_missing_key_raises_value_error(monkeypatch):
    monkeypatch.delenv("TRAMA_TOKEN_KEY", raising=False)

    with pytest.raises(ValueError) as exc_info:
        encrypt_token("any_token")
    assert "Clave de cifrado no configurada" in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        decrypt_token("any_cipher")
    assert "Clave de cifrado no configurada" in str(exc_info.value)


def test_invalid_key_raises_value_error():
    with pytest.raises(ValueError) as exc_info:
        encrypt_token("any_token", key="invalid-not-base64-key")
    assert "Clave de cifrado inválida" in str(exc_info.value)


def test_decrypt_with_wrong_key():
    key1 = generate_token_key()
    key2 = generate_token_key()

    cipher = encrypt_token("my_token", key=key1)

    with pytest.raises(ValueError) as exc_info:
        decrypt_token(cipher, key=key2)
    assert "No se pudo descifrar el token" in str(exc_info.value)


def test_empty_token_returns_empty_string():
    key = generate_token_key()
    assert encrypt_token("", key=key) == ""
    assert decrypt_token("", key=key) == ""
