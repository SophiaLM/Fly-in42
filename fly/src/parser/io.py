"""E/S/I/O del parser:
lectura del fichero y limpieza de líneas del mapa."""

from __future__ import annotations


def read_lines(path: str) -> list[tuple[int, str]]:
    """Lee el fichero y devuelve (número_de_línea, texto) por línea."""
    result = []

    with open(path, "r", encoding="utf-8") as file:
        num = 1
        for line in file:
            line = line.rstrip("\n")
            result.append((num, line))
            num += 1
    return result


def strip_noise(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Elimina comentarios (#) y líneas vacías conservando la numeración."""
    return [
        (num, line)
        for num, line in lines
        if line.strip() and not line.strip().startswith("#")
    ]
