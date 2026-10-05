"""Punto de entrada: parsa un mapa, lo simula e imprime los turnos."""

from __future__ import annotations

import sys

from src.parser import parse_map_file
from src.parser.exceptions import MapParseError
from src.simulation import Simulation, SimulationError
from src.visualization import format_turn


def main() -> int:
    """Ejecuta la simulacion sobre un fichero de mapa y reporta el resultado.

    Devuelve 0 si el mapa se pudo parsear y todos los drones llegaron, y 1
    si el mapa es invalido o la simulacion no puede terminar. Los turnos ya
    jugados se quedan impresos aunque la simulacion falle despues.
    """
    if len(sys.argv) != 2:
        print("usage: python -m src.main <map_file>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        graph = parse_map_file(path)
    except MapParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        simulation = Simulation(graph)
    except SimulationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    zone_colors = {zone.name: zone.color for zone in graph.zones.values()}

    try:
        while True:
            result = simulation.step()
            if result is None:
                break
            line = format_turn(result.tokens, zone_colors)
            if line:
                print(line)
    except SimulationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
