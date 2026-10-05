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


ZONE_COSTS: dict[ZoneType, int] = {
    ZoneType.NORMAL: 1,
    ZoneType.PRIORITY: 1,
    ZoneType.RESTRICTED: 2,
}


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
        color: str | None = None,
    ) -> None:
        self.name: str = name
        self.x: int = x
        self.y: int = y
        self.zone_type: ZoneType = zone_type
        self.max_drones: int | None = max_drones
        self.is_start: bool = is_start
        self.is_end: bool = is_end
        self.color: str | None = color
        self.drones: list[Drone] = []

    def can_accept_drone(self, reserved: int = 0) -> bool:
        """Devuelve True si la zona puede aceptar un dron más.

        Una zona BLOCKED nunca acepta drones, así que responde False siempre.
        Como `add_drone` es la única vía de entrada a una zona, esto garantiza
        estructuralmente que ningún dron entre ni permanezca en una bloqueada.

        `reserved` es la variación de ocupación ya comprometida para el mismo
        turno: puede ser negativo cuando se han decidido más salidas que
        entradas. Así quien pregunta no tiene que conocer los movimientos ya
        decididos por otros drones, solo su efecto neto sobre la zona.
        """
        if self.zone_type is ZoneType.BLOCKED:
            return False
        if self.is_start or self.is_end or self.max_drones is None:
            return True
        return len(self.drones) + reserved < self.max_drones

    def zone_cost(self) -> int:
        """Coste en turnos de entrar en `zone`."""
        try:
            return ZONE_COSTS[self.zone_type]
        except KeyError:
            raise ValueError(f"Zone: {self.name} cannot be entered") from None

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

    def __init__(self, a: Zone, b: Zone, max_link_capacity: int) -> None:
        self.a: Zone = a
        self.b: Zone = b
        self.max_link_capacity: int = max_link_capacity
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

    def have_capacity(self, reserved: int = 0) -> bool:
        """Devuelve True si la conexion puede aceptar un dron más.

        `drones` es la lista de drones que ocupan fisicamente la conexion y
        `reserved` son los que ya se han comprometido a usarla en el mismo
        periodo, aunque todavia no figuren en la lista. La simulacion lleva la
        cuenta de `reserved` con sus reservas por turno: por eso el valor por
        defecto es 0 y el resto del codigo puede seguir llamando sin
        argumentos.
        """
        return len(self.drones) + reserved < self.max_link_capacity

    def add_drone(self, drone: Drone) -> None:
        """Añade un dron a la conexion."""
        if not self.have_capacity():
            raise ValueError(
                f"Connection {self.label} cannot accept the drone."
            )
        self.drones.append(drone)

    def remove_drone(self, drone: Drone) -> None:
        """Elimina un dron de la zona."""
        self.drones.remove(drone)

    @property
    def label(self) -> str:
        """Etiqueta de la conexion: "A-B" con los nombres de las zonas."""
        return f"{self.a.name}-{self.b.name}"


class Drone:
    """Un dron que sabe donde esta, hacia donde va y como llega.

    Ademas de la posicion actual y el destino final, guarda la ruta que
    tiene que recorrer y el estado de transito: entrar en una zona RESTRICTED
    ocupa la conexion dos turnos, asi que hay un estado intermedio en el que
    el dron ya no esta en ninguna zona pero todavia no ha aterrizado.

    Invariante de ruta: `route[route_index]` es siempre la zona en la que
    esta el dron, y `route[route_index + 1]` es la zona que espera a
    continuación. Si `transit` no es None, es la conexion que va de una a
    la otra. `route_index` solo avanza al aterrizar, nunca al empezar a
    cruzar una RESTRICTED.
    """

    def __init__(
        self,
        name: str,
        position: Zone,
        target: Zone,
        route: list[Zone] | None = None,
    ) -> None:
        self.name: str = name
        self.position: Zone = position
        self.target: Zone = target

        # Transito: None salvo que este cruzando una zona RESTRICTED.
        self.transit: Connection | None = None
        self.transit_turns_left: int = 0

        # Ruta propia: copia explicita para que cada dron tenga la suya.
        self.route: list[Zone] = [] if route is None else list(route)
        self.route_index: int = 0

    def next_step(self) -> Zone | None:
        """Zona siguiente en la ruta, o None si ya no queda ninguna.

        None significa que el dron ha llegado a `target`.
        """
        if self.route_index + 1 >= len(self.route):
            return None
        return self.route[self.route_index + 1]

    def detach(self) -> None:
        """Quita el dron de su zona actual sin tocar ningun destino.

        El invariante de ocupacion es: un dron esta en `zone.drones` si y
        solo si `drone.position is zone`. `detach` rompe la mitad izquierda a
        proposito para permitir el "vaciar todos, luego llenar todos" de la
        simulacion: varios drones pueden intercambiarse la misma zona en un
        mismo turno sin que ninguna se quede fuera.

        `position` NO cambia. Sigue apuntando a la zona de la que el dron
        acaba de salir, que es la que espera en `route_index` hasta que
        `attach` la sincronice con el aterrizaje.
        """
        if self not in self.position.drones:
            raise ValueError(
                f"Drone {self.name} is not in {self.position.name}: "
                f"the occupancy invariant was already broken."
            )
        self.position.remove_drone(self)

    def attach(self, zone: Zone) -> None:
        """Aterriza el dron en `zone` y sincroniza `position`.

        La capacidad la valida `zone.add_drone`: si la zona esta llena lanza
        `ValueError` y el dron se queda donde estaba. No valida las reglas
        del mapa (conexion existente, zona bloqueada, capacidad del enlace):
        de eso se encarga `Simulation`.
        """
        zone.add_drone(self)
        self.position = zone

    def move_to(self, zone: Zone) -> None:
        """Mueve el dron a `zone` manteniendo el invariante de ocupación.

        El invariante es: un dron está en `zone.drones` si y solo si
        `drone.position is zone`. Nadie más debe mutar `position`.

        Es un atajo de `detach()` seguido de `attach()`. El orden de las dos
        operaciones si importa: `detach` valida el invariante de partida y
        `attach` la capacidad del destino, de forma que un fallo deja al dron
        sin estar en ninguna zona en lugar de estar en dos.

        Quien necesite vaciar una zona antes de llenarla, como hace la
        simulacion, debe llamar a `detach` y `attach` por separado en vez de
        usar este metodo.

        No valida las reglas del mapa (conexión existente, zona bloqueada,
        capacidad del enlace): de eso se encarga `Graph.can_move`. Lanza
        `ValueError` si el invariante ya estaba roto antes de la llamada.
        """
        self.detach()
        self.attach(zone)


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
        """Es legal este movimiento? Drone - Target

        Pregunta pura: no cambia nada, para que el scheduler pueda consultar
        muchas opciones sin comprometerse con ninguna. La regla de BLOCKED no
        se comprueba aquí sino en `Zone.can_accept_drone`, de donde se hereda.
        """
        conn = self.find_connection(drone.position, target)
        return (
            conn is not None
            and conn.have_capacity()
            and target.can_accept_drone()
        )

    def move_drone(self, drone: Drone, target: Zone) -> bool:
        """Punto de entrada para mover un dron. Valida y ejecuta.

        Devuelve False sin tocar nada si el movimiento no es legal: es un
        resultado normal de la simulación, no un error.
        """
        if not self.can_move(drone, target):
            return False
        drone.move_to(target)
        return True

    def find_connection(self, a: Zone, b: Zone) -> Connection | None:
        """Devuelve la conexión entre `a` y `b`, o None si no están unidas."""
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
