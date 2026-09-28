from src.models import Graph, Zone
# import heapq  # Importa la cola de prioridad para Dijkstra.


def zone_cost(zone: Zone) -> int:
    """Coste en turnos de entrar en `zone`."""


def shortest_path(graph: Graph, start: Zone, end: Zone) -> list[Zone] | None:
    """Dijkstra: ruta de coste mínimo entre `start` y `end`.
    Devuelve la lista de zonas (start incluido) o None si no hay camino.
    """
