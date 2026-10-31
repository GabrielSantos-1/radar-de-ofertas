from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.models import Canal, EnvioResultado, SendStatus


@dataclass
class FakePublicador:
    """Records what would be sent, so the MVP can be exercised without real channels."""

    enviados: list[tuple[str, str]] = field(default_factory=list)
    falhar_sempre: bool = False

    def publicar(self, canal: Canal, mensagem: str) -> EnvioResultado:
        if self.falhar_sempre or "falha" in canal.identificador_externo.lower():
            return EnvioResultado(
                status=SendStatus.FALHA,
                erro="Falha simulada no envio para o canal.",
            )
        self.enviados.append((canal.id, mensagem))
        return EnvioResultado(status=SendStatus.OK)
