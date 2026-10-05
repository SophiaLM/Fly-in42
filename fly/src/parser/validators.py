"""Validación de valores sueltos: tipo de zona y enteros positivos."""

from __future__ import annotations

from ..models import ZoneType
from .exceptions import MapParseError


def parse_zone_type(raw: str | None, line_no: int) -> ZoneType:
    """Mapea el metadato zone= al enumerado ZoneType (NORMAL si falta)."""
    if raw is None:
        return ZoneType.NORMAL

    raw_lower = raw.lower()

    for zone in ZoneType:
        if zone.value == raw_lower:
            return zone

    raise MapParseError(
        f"Line {line_no}: zone='{raw}' is not valid. "
        f"Allowed values: {', '.join(z.value for z in ZoneType)}."
    )


def parse_color(raw: str | None, line_no: int) -> str | None:
    """Valida el metadato color= y lo devuelve tal cual (None si falta).

    El subject (VI) acepta cualquier palabra como color, sin lista fija,
    así que no se comprueba contra ninguna paleta. Solo se rechaza el valor
    vacío (`color=`), que no es una palabra válida.
    """
    if raw is None:
        return None
    if not raw:
        raise MapParseError(f"Line {line_no}: 'color' cannot be empty")
    return raw


def parse_positive_int(raw: str, field_name: str, line_no: int) -> int:
    """Convierte cadena en entero positivo con campo y línea en el error."""
    try:
        value = int(raw)
    except ValueError:
        raise MapParseError(
            f"Line {line_no}: '{field_name}' must be a positive integer"
        )

    if value <= 0:
        raise MapParseError(
            f"Line {line_no}: '{field_name}' must be a positive integer"
        )
    return value


def parse_int_field(raw: str, field_name: str, line_no: int) -> int:
    """Convierte a entero sin exigir positividad (para coordenadas x, y)."""
    try:
        return int(raw)
    except ValueError:
        raise MapParseError(
            f"Line {line_no}: '{field_name}' must be an integer"
        ) from None
