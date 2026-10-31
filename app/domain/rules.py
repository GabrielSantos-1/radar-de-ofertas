from app.domain.models import Canal, Oferta, OfferStatus


def normalize_external_id(raw: str) -> str:
    """Reduce an external id to its canonical form.

    Query strings and fragments change on every scrape, so they cannot take part in the
    natural key; otherwise the same product would be collected again and again.
    """
    cleaned = raw.strip().split("?", 1)[0].split("#", 1)[0]
    cleaned = "".join(cleaned.split()).lower()
    return cleaned.rstrip("/")


def build_offer_key(loja_id: str, id_externo_normalizado: str) -> tuple[str, str]:
    return (str(loja_id), id_externo_normalizado)


def is_link_valid(status_code: int, elapsed_ms: int, max_ms: int) -> bool:
    return 200 <= status_code < 400 and 0 <= elapsed_ms <= max_ms


def can_publish(
    oferta: Oferta,
    canal: Canal,
    ja_publicada: bool,
    link_validado: bool,
    *,
    link_invalido: bool = False,
) -> tuple[bool, str]:
    """Decide whether an offer may be sent to a channel, with a user-facing reason."""
    if oferta.status is OfferStatus.DESCARTA:
        return False, "Oferta descartada não pode ser publicada."
    if not canal.ativo:
        return False, "Canal inativo não pode receber publicações."
    if ja_publicada:
        return False, "Oferta já publicada neste canal."
    if link_invalido:
        return False, "Link de afiliado inválido. Gere e valide o link novamente."
    if not link_validado:
        return False, "Link de afiliado ainda não foi validado."
    return True, "Publicação permitida."
