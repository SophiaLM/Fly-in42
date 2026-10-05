"""
Presentacion de la simulacion: como se escribe y colorea una linea de turno.

Un turno produce una lista de eventos crudos ("D1-Alfa", "D2-Alfa-Beta").
Aqui se ordenan y se convierten en la linea que se imprime por pantalla.
"""

from __future__ import annotations

import os
import sys
import zlib
from typing import TextIO

RESET = "\033[0m"

UNKNOWN_DRONE_ORDER = 10**12

NAMED_COLORS: dict[str, int] = {
    "aqua": 80, "beige": 223, "black": 235, "blue": 111, "brown": 180,
    "crimson": 168, "cyan": 80, "darkred": 88, "fuchsia": 176, "gold": 222,
    "gray": 245, "green": 114, "grey": 245, "indigo": 57, "ivory": 230,
    "khaki": 143, "lavender": 183, "lime": 154, "magenta": 176,
    "maroon": 131, "navy": 25, "olive": 100, "orange": 215, "pink": 218,
    "purple": 141, "red": 203, "salmon": 209, "silver": 250, "teal": 44,
    "violet": 177, "white": 255, "yellow": 221,
}

FALLBACK_OFFSET = 16
FALLBACK_SPAN = 216


def ansi_code(color: str | None) -> str | None:
    """Codigo ANSI 256 para un nombre de color libre del mapa.

    El mapa puede declarar cualquier palabra como color, asi que las
    conocidas van a su codigo y el resto cae en un color fijo derivado del
    nombre. Se usa crc32 y no hash porque el hash de los strings cambia en
    cada proceso: el mismo mapa daria colores distintos en cada ejecucion.
    """
    if not color:
        return None
    name = color.strip().lower()
    code = NAMED_COLORS.get(name)
    if code is None:
        code = FALLBACK_OFFSET + zlib.crc32(name.encode()) % FALLBACK_SPAN
    return f"\033[38;5;{code}m"


def colors_enabled(stream: TextIO | None = None) -> bool:
    """Tiene sentido colorear esta salida?

    No si NO_COLOR esta puesto, que manda sobre cualquier otra cosa, ni si
    la salida no va a una terminal: al redirigir a un fichero los codigos de
    escape se cuelan en el texto y rompen cualquier comparacion.
    """
    if os.environ.get("NO_COLOR"):
        return False
    target = sys.stdout if stream is None else stream
    return target.isatty()


def colorize(token: str, color: str | None = None) -> str:
    """Envuelve `token` en el color que pide el mapa, si se puede.

    El subject no obliga a colorear nada, asi que sin `color` el token se
    devuelve tal cual, y tampoco se colorea si la salida no admite color.
    """
    if color is None or not colors_enabled():
        return token
    code = ansi_code(color)
    return token if code is None else f"{code}{token}{RESET}"


def token_order(token: str) -> int:
    """Clave para ordenar tokens por numero de dron: D2 antes que D10.

    Los nombres de zona no pueden llevar guion, asi que el destino empieza
    justo detras del primer guion y el numero de dron es lo que hay antes.
    Se aceptan las dos formas (`D1-Alfa` y `1-Alfa`). Un token sin numero se
    va al final en lugar de romper la comparacion.
    """
    head, _, rest = token.partition("-")
    digits = rest if head.isdigit() else head[1:]
    if not digits.isdigit():
        return UNKNOWN_DRONE_ORDER
    return int(digits)


def destination_of(token: str) -> str:
    """Zona de destino de un token.

    `D1-Alfa` quiere llegar a `Alfa`. `D1-Alfa-Beta` es un dron cruzando el
    enlace Alfa-Beta, y lo que busca es llegar a `Beta`.
    """
    _, _, rest = token.partition("-")
    return rest.rsplit("-", 1)[-1] if rest else token


def format_turn(
    tokens: list[str],
    zone_colors: dict[str, str | None] | None = None,
) -> str:
    """Convierte los eventos de un turno en la linea que se imprime.

    Cada destino se pinta con el color que el mapa declara para esa zona. Un
    turno sin eventos no imprime linea ninguna. Los repetidos se colapsan,
    porque la salida depende de los drones y no de como se recorrieran, y el
    resto se ordena por numero de dron.
    """
    if not tokens:
        return ""
    ordered = sorted(set(tokens), key=token_order)
    if not zone_colors:
        return " ".join(ordered)
    parts = [
        f"{head}-{colorize(dest, zone_colors.get(destination_of(token)))}"
        if dest else token
        for token in ordered
        for head, _, dest in [token.partition("-")]
    ]
    return " ".join(parts)
