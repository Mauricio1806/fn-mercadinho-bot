"""
Filtro de logging que masca credenciais em qualquer output.
Instalado no root logger em app.main:startup.

Cobre:
- kwargs de log tipo logger.info("...", extra={"api_key": "xxx"})
- strings formatadas: "api_key=xxx", "token: 'xxx'", "Bearer xxx"
"""

from __future__ import annotations

import logging
import re

_SENSITIVE_KEYS = frozenset(
    {"api_key", "access_token", "refresh_token", "token", "secret",
     "password", "hashed_password", "credentials_master_key", "jwt_secret"}
)

# Regex conservador: captura chave=valor e chave: valor
_PATTERNS = [
    re.compile(
        r'(?i)(api_key|access_token|refresh_token|secret|password|bearer)'
        r'(["\']?\s*[:=]\s*["\']?)([A-Za-z0-9._\-+/=]{6,})'
    ),
]


def _mask_value(v: str) -> str:
    if len(v) <= 4:
        return "***"
    return v[:2] + "***" + v[-2:]


class SecretMaskingFilter(logging.Filter):
    """
    Aplica masking em record.msg + record.args antes do formatter.
    Rejeita silenciosamente qualquer key sensível em record.__dict__.
    """

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        try:
            # Mask attributes injected via extra={}
            for k in list(record.__dict__.keys()):
                if k.lower() in _SENSITIVE_KEYS:
                    val = record.__dict__[k]
                    if isinstance(val, str):
                        record.__dict__[k] = _mask_value(val)

            # Mask no texto renderizado
            if isinstance(record.msg, str):
                msg = record.msg
                for pat in _PATTERNS:
                    msg = pat.sub(lambda m: f"{m.group(1)}{m.group(2)}{_mask_value(m.group(3))}", msg)
                record.msg = msg
        except Exception:
            # Filter NUNCA pode explodir e derrubar log
            pass
        return True


def install_masking_filter() -> None:
    """Instala em todos os handlers do root + uvicorn.access."""
    f = SecretMaskingFilter()
    logging.getLogger().addFilter(f)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi", "sqlalchemy"):
        logging.getLogger(name).addFilter(f)
