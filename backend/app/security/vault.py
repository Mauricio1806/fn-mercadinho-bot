"""
Credential Vault — encapsula criptografia simétrica de credenciais de integração.

Fluxo:
- Master key vem de settings.credentials_master_key (env var CREDENTIALS_MASTER_KEY)
- Fernet (AES-128-CBC + HMAC-SHA256) — reconhecido como padrão pela indústria
- Lazy init: só falha se alguém tentar cifrar/decifrar sem key configurada
- mask(): pra logs, respostas de API, exibição — nunca vaza o valor
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


class VaultNotConfigured(RuntimeError):
    """Master key ausente ou inválida."""


class InvalidCredential(ValueError):
    """Ciphertext corrompido ou master key rotacionada sem re-encrypt."""


class CredentialVault:
    """
    Encapsula cripto simétrica. Uso:
        vault = get_vault()
        cipher = vault.encrypt("bling_access_token_xyz")
        plain = vault.decrypt(cipher)
        masked = CredentialVault.mask(plain)  # "•••• _xyz"
    """

    def __init__(self, master_key: str):
        if not master_key or master_key.strip() == "":
            raise VaultNotConfigured(
                "CREDENTIALS_MASTER_KEY não configurado. "
                "Gere com: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' "
                "e defina como env var no Railway."
            )
        try:
            self._fernet = Fernet(master_key.encode() if isinstance(master_key, str) else master_key)
        except (ValueError, TypeError) as exc:
            raise VaultNotConfigured(
                f"CREDENTIALS_MASTER_KEY inválida ({exc}). "
                "Precisa ser 32-byte urlsafe base64."
            ) from exc

    def encrypt(self, plaintext: str) -> str:
        """Cifra plaintext, retorna string base64 pra guardar em coluna text."""
        if not plaintext:
            return ""
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        """Decifra. Levanta InvalidCredential se corrompido/rotacionado."""
        if not ciphertext:
            return ""
        try:
            return self._fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise InvalidCredential(
                "Credencial corrompida ou criptografada com outra master key."
            ) from exc

    @staticmethod
    def mask(value: str | None, keep: int = 4) -> str:
        """
        Mascara pra exibição segura. Nunca retorna o valor bruto.
        >>> CredentialVault.mask("bling_token_abc123XYZ", keep=4)
        '•••• 3XYZ'
        """
        if not value:
            return "—"
        if len(value) <= keep:
            return "••••"
        return "•••• " + value[-keep:]


_vault: CredentialVault | None = None


def get_vault() -> CredentialVault:
    """Singleton — inicializa na primeira chamada."""
    global _vault
    if _vault is None:
        settings = get_settings()
        _vault = CredentialVault(settings.credentials_master_key)
    return _vault


def reset_vault_for_tests() -> None:
    """Resetar singleton (uso: fixtures de teste)."""
    global _vault
    _vault = None
