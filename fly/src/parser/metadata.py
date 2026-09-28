"""Parseo de líneas: prefijos y bloque de metadatos opcional."""

from __future__ import annotations

from .exceptions import MapParseError

VALID_PREFIXES = {"nb_drones", "start_hub", "end_hub", "hub", "connection"}


def classify_line(line: str) -> tuple[str, str]:
    """Separa prefijo de línea (hub, connection...) del contenido."""
    if ":" not in line:
        raise MapParseError(f"Missing ':' in line: {line}")
    prefix, _, body = line.partition(":")
    prefix = prefix.strip()
    body = body.strip()

    if prefix not in VALID_PREFIXES:
        raise MapParseError(f"unknown directive: {prefix!r}")

    return prefix, body


def split_metadata_block(body: str) -> tuple[str, str | None]:
    """Separa el cuerpo de la línea de su metadata opcional entre [...]."""
    bracket_start = body.find("[")
    if bracket_start == -1:
        return body.strip(), None

    if not body.rstrip().endswith("]"):
        raise MapParseError(f"metadata block not closed with ']': {body!r}")

    name_part = body[:bracket_start].strip()
    meta = body[bracket_start + 1: body.rfind("]")].strip()
    return name_part, meta


def parse_metadata(meta: str | None) -> dict[str, str]:
    """Convierte 'clave=valor' separados por espacios en un dict[str, str]."""
    if not meta:
        return {}

    result: dict[str, str] = {}
    for token in meta.split():
        if "=" not in token:
            raise MapParseError(f"malformed metadata token: {token!r}")
        key, _, value = token.partition("=")
        if key in result:
            raise MapParseError(f"duplicate metadata key: {key!r}")
        result[key] = value

    return result
