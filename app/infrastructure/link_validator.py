from __future__ import annotations

import time

import httpx

from app.domain.models import LinkCheck, utcnow
from app.domain.rules import is_link_valid


class HttpxLinkValidator:
    def __init__(self, max_ms: int = 5000) -> None:
        self.max_ms = max_ms

    def validar(self, link: str) -> LinkCheck:
        inicio = time.perf_counter()
        status_code = 0
        try:
            resposta = httpx.get(
                link,
                timeout=self.max_ms / 1000,
                follow_redirects=True,
            )
            status_code = resposta.status_code
        except httpx.HTTPError:
            status_code = 0

        elapsed_ms = int((time.perf_counter() - inicio) * 1000)
        return LinkCheck(
            status_code=status_code,
            elapsed_ms=elapsed_ms,
            valido=is_link_valid(status_code, elapsed_ms, self.max_ms),
            validado_em=utcnow(),
        )
