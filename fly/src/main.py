"""Punto de entrada: parsa un mapa y muestra su resumen."""

from __future__ import annotations

import sys

from src.parser import parse_map_file
from src.parser.exceptions import MapParseError


def main() -> int:
    """Ejecuta el parser sobre un fichero de mapa y reporta el resultado."""
    if len(sys.argv) != 2:
        print("usage: python -m src.main <map_file>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        graph = parse_map_file(path)
    except MapParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        f"{path}: {graph.nb_drones} drones, "
        f"{len(graph.zones)} zones, {len(graph.connections)} connections"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
