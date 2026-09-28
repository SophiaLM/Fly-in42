"""
Modelo de datos de Fly-in:
Defino las clases (objetos) que usaremos para representar
el grafo y sus elementos: zonas, conexiones y drones.
"""

from __future__ import annotations

from enum import Enum


class ZoneType(Enum):
    """Tipo de zona: determina el coste de atravesarla en el pathfinding."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class Zone:
    """Una zona del mapa: un nodo del grafo."""

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone_type: ZoneType,
        max_drones: int | None,
        is_start: bool = False,
        is_end: bool = False,
    ) -> None:
        self.name: str = name
        self.x: int = x
        self.y: int = y
        self.zone_type: ZoneType = zone_type
        self.max_drones: int | None = max_drones
        self.is_start: bool = is_start
        self.is_end: bool = is_end
        self.drones: list[Drone] = []

    def can_accept_drone(self) -> bool:
        """Devuelve True si la zona puede aceptar un dron más."""
        if self.is_start or self.is_end or self.max_drones is None:
            return True
        return len(self.drones) < self.max_drones

    def add_drone(self, drone: Drone) -> None:
        """Añade un dron a la zona."""
        if not self.can_accept_drone():
            raise ValueError(f"Zone {self.name} cannot accept the drone.")
        self.drones.append(drone)

    def remove_drone(self, drone: Drone) -> None:
        """Elimina un dron de la zona."""
        self.drones.remove(drone)


class Connection:
    """Una conexion bidireccional entre dos zonas: una arista del grafo."""

    def __init__(
        self, a: Zone, b: Zone, max_link_capacity: int | None
    ) -> None:
        self.a: Zone = a
        self.b: Zone = b
        self.max_link_capacity: int | None = max_link_capacity
        self.drones: list[Drone] = []

    def other_zone(self, zone: Zone) -> Zone:
        """Devuelve la zona opuesta a la que se pasa como argumento."""
        if zone == self.a:
            return self.b
        elif zone == self.b:
            return self.a
        else:
            raise ValueError(
                f"Zone {zone.name} is not connected to this connection."
            )

    def have_capacity(self) -> bool:
        """Devuelve True si la conexion puede aceptar un dron más."""
        if self.max_link_capacity is None:
            return True
        return len(self.drones) < self.max_link_capacity


class Drone:
    """Un dron que sabe donde esta y hacia donde va."""
    def __init__(self, name: str, position: Zone, target: Zone) -> None:
        self.name: str = name
        self.position: Zone = position
        self.target: Zone = target

    def move_to(self, zone: Zone) -> None:
        self.position = zone


class Graph:
    """El grafo completo del mapa: zonas indexadas por nombre y conexiones."""

    def __init__(
        self,
        zones: dict[str, Zone],
        connections: list[Connection],
        nb_drones: int,
    ) -> None:
        self.zones: dict[str, Zone] = zones
        self.connections: list[Connection] = connections
        self.nb_drones: int = nb_drones
        self._adjacency: dict[str, list[Zone]] = {name: [] for name in zones}
        for conn in connections:
            self._adjacency[conn.a.name].append(conn.b)
            self._adjacency[conn.b.name].append(conn.a)

    def can_move(self, drone: Drone, target: Zone) -> bool:
        """Es legal este movimiento? Drone - Target"""
        conn = self.find_connection(drone.position, target)
        return (
            conn is not None
            and conn.have_capacity()
            and target.can_accept_drone()
        )

    def move_drone(self, drone: Drone, target: Zone) -> bool:
        """Punto de entrada para mover un dron. Valida y ejecuta"""
        if not self.can_move(drone, target):
            return False
        drone.move_to(target)
        return True

    def find_connection(self, a: Zone, b: Zone) -> Connection | None:
        for conn in self.connections:
            if (conn.a == a and conn.b == b) or (conn.a == b and conn.b == a):
                return conn
        return None

    def neighbors(self, zone: Zone) -> list[Zone]:
        """Zonas alcanzables desde `zone` en un paso, sin pasar por BLOCKED."""
        return [
            other
            for other in self._adjacency[zone.name]
            if other.zone_type is not ZoneType.BLOCKED
        ]
