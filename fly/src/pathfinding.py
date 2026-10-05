"""
Rutas de coste minimo entre zonas del mapa (Dijkstra)
Dado un start y un end, ¿por qué zonas paso y cuánto me cuesta?
"""
import heapq
from typing import TypeAlias
from src.models import Graph, Zone, ZoneType

Cost: TypeAlias = tuple[int, int]
EdgeKey: TypeAlias = tuple[str, str]
Forbidden: TypeAlias = frozenset[EdgeKey]

MAX_ROUNDS = 4
MAX_CANDIDATES = 12


def edge_key(a: Zone, b: Zone) -> EdgeKey:
    """Identificador de un enlace, igual en los dos sentidos.

    Los nombres de zona no pueden llevar guion, asi que el par de nombres
    ya identifica el enlace sin llegar a las conexiones. Ponerlo en orden
    hace que recorrer `a-b` o `b-a` caiga en la misma clave.
    """
    return (a.name, b.name) if a.name < b.name else (b.name, a.name)


class PathFinder:
    """Calcula rutas de coste mínimo sobre un grafo estático.

    Guarda las rutas ya calculadas: como el grafo no cambia, la misma
    pregunta (start, end) siempre tiene la misma respuesta.
    """
    def __init__(self, graph: Graph) -> None:
        self.graph: Graph = graph
        self._cache: dict[tuple[str, str, Forbidden], list[Zone] | None] = {}

    @staticmethod
    def _step_cost(zone: Zone) -> Cost:
        """Coste de entrar en `zone`, sus turnos y preferencias."""
        preference = -1 if zone.zone_type is ZoneType.PRIORITY else 0
        return (zone.zone_cost(), preference)

    @staticmethod
    def _build_route(
        prev: dict[str, Zone], start: Zone, end: Zone
    ) -> list[Zone]:
        """Reconstruye la ruta siguiendo `prev` desde `end` hacia `start`."""
        route = [end]
        while route[-1].name != start.name:
            route.append(prev[route[-1].name])
        route.reverse()
        return route

    @staticmethod
    def _turn_cost(route: list[Zone]) -> int:
        """Turnos que cuesta recorrer `route` entera."""
        return sum(zone.zone_cost() for zone in route)

    def _dijkstra(
        self, start: Zone, end: Zone, forbidden: Forbidden
    ) -> list[Zone] | None:
        """Busqueda de Dijkstra sin cache. Devuelve la ruta o None."""
        dist: dict[str, Cost] = {start.name: (0, 0)}
        prev: dict[str, Zone] = {}
        visited: set[str] = set()
        heap: list[tuple[Cost, str]] = [((0, 0), start.name)]

        while heap:
            cost, name = heapq.heappop(heap)
            if name in visited:
                continue
            visited.add(name)
            if name == end.name:
                break
            zone = self.graph.zones[name]
            for neighbor in self.graph.neighbors(zone):
                if neighbor.name in visited:
                    continue
                if edge_key(zone, neighbor) in forbidden:
                    continue
                turns, preference = cost
                step_turns, step_preference = self._step_cost(neighbor)
                new_cost = (turns + step_turns, preference + step_preference)
                known = dist.get(neighbor.name)
                if known is None or new_cost < known:
                    dist[neighbor.name] = new_cost
                    prev[neighbor.name] = zone
                    heapq.heappush(heap, (new_cost, neighbor.name))
        if end.name not in visited:
            return None
        return self._build_route(prev, start, end)

    def shortest_path(
        self,
        start: Zone,
        end: Zone,
        forbidden: Forbidden = frozenset(),
    ) -> list[Zone] | None:
        """Devuelve la ruta de coste mínimo entre start y end.
        Prefiere las zonas con mas zonas priority
        Las aristas de `forbidden` se tratan como si no existieran.
        Si no hay ruta, devuelve None.
        si hay ruta, devuelve una copia de la lista de zonas
        """
        key = (start.name, end.name, forbidden)
        if key not in self._cache:
            self._cache[key] = self._dijkstra(start, end, forbidden)
        route = self._cache[key]
        return None if route is None else list(route)

    def alternative_routes(
        self, start: Zone, end: Zone
    ) -> list[list[Zone]]:
        """Rutas de coste mínimo, distintas entre sí, para repartir la flota.

        Empieza por la ruta óptima y después busca alternativas quitando una
        arista cada vez: al quitar `a-b` la búsqueda tiene que hallar otra
        manera de pasar, y así salen rutas nuevas sin bucles y sin meter un
        algoritmo de k caminos más complejo.

        Al final se queda solo con las que cuestan lo mismo que la mejor.
        Repartir la flota entre rutas más largas no reparte: solo alarga el
        viaje de los drones que las cogen.
        """
        best = self.shortest_path(start, end)
        if best is None:
            return []

        candidates: list[list[Zone]] = [best]
        forbidden: set[EdgeKey] = set()
        for _ in range(MAX_ROUNDS):
            discovered = 0
            for route in list(candidates):
                for zone, neighbor in zip(route, route[1:]):
                    key = edge_key(zone, neighbor)
                    if key in forbidden:
                        continue
                    forbidden.add(key)
                    alternative = self._dijkstra(
                        start, end, frozenset(forbidden)
                    )
                    fresh = alternative not in candidates
                    if alternative is not None and fresh:
                        candidates.append(alternative)
                        discovered += 1
                    forbidden.discard(key)
            if not discovered or len(candidates) >= MAX_CANDIDATES:
                break

        cheapest = min(self._turn_cost(route) for route in candidates)
        return [
            list(route)
            for route in candidates
            if self._turn_cost(route) == cheapest
        ]
