"""
Motor de simulacion: mueve los drones turno a turno hasta el destino.

El turno se resuelve en dos fases que nunca se mezclan:

1. Declarar. Cada dron dice que intends hacer este turno sin tocar nada.
   Quien decide ya sabe lo que han decidido los drones de menor identificador
   (se recorren en orden D1, D2, ...), y por eso puede ir apuntando las
   plazas que se van a quedar libres y las que se van a ocupar.
2. Resolver. Se aplican las intenciones en un orden estricto: primero se
   vacian todas las zonas de los que se mueven, luego aterrizan los que
   venían en transito, luego entran los que empiezan a cruzar una zona
   RESTRICTED y por ultimo se mueven los demas. Vaciar antes de llenar es
   lo que permite que dos drones se intercambien la plaza de una zona con
   capacidad 1 dentro del mismo turno.

Los Capacity se cuentan con dos mecanismos distintos, segun lo que haya que
expresar:

- Las conexiones se cuentan con reservas por turno (`link_reservations`).
  Es la unica forma de decir "este dron ocupa el enlace ahora y tambien el
  turno que viene", que es lo que pasa al cruzar una zona RESTRICTED.
- Las zonas no necesitan reservas propias: su ocupacion efectiva es la que
  tienen menos los que se van y mas los que ya han sido aceptados para
  entrar. Para eso estan `will_leave` y `will_enter`, y los drones que
  estaban en transito y aterrizan este turno, que hay que contar por
  separado porque todavia no figuran en ninguna zona.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.models import Connection, Drone, Graph, Zone, ZoneType
from src.pathfinding import PathFinder

IntentKind = Literal["arrive", "deliver", "wait", "move"]

UNKNOWN_DRONE_ORDER = 10**12


class SimulationError(Exception):
    """Error irrecuperable de simulacion: no hay ruta o no hay progreso."""


@dataclass(slots=True)
class TurnResult:
    """Lo que ha pasado en un turno: que turno es y que eventos hubo."""

    turn: int
    tokens: list[str]


@dataclass(slots=True)
class Intent:
    """Lo que un dron ha declarado que hara este turno.

    `to` y `conn` solo tienen sentido para kind="move": son la zona de
    destino y la conexion que lleva hasta ella.
    """

    kind: IntentKind
    drone: Drone
    to: Zone | None = None
    conn: Connection | None = None


class Simulation:
    """Una partida: drones que viajan del start al end respetando el mapa."""

    MAX_TURNS_WITHOUT_PROGRESS: int = 2

    def __init__(self, graph: Graph) -> None:
        self.graph: Graph = graph
        self.pathfinder: PathFinder = PathFinder(graph)

        start: Zone | None = None
        end: Zone | None = None
        for zone in graph.zones.values():
            if zone.is_start:
                start = zone
            if zone.is_end:
                end = zone
        if start is None:
            raise SimulationError("no start hub found")
        if end is None:
            raise SimulationError("no end hub found")
        if not start.can_accept_drone():
            raise SimulationError(
                f"start hub {start.name!r} cannot hold drones"
            )
        self.start_zone: Zone = start
        self.end_zone: Zone = end

        routes = self.pathfinder.alternative_routes(start, end)
        if not routes:
            raise SimulationError(
                f"no route from {start.name!r} to {end.name!r}"
            )

        self.drones: list[Drone] = []
        for i in range(1, graph.nb_drones + 1):
            drone = Drone(
                name=f"D{i}",
                position=start,
                target=end,
                route=routes[(i - 1) % len(routes)],
            )
            start.add_drone(drone)
            self.drones.append(drone)

        self.turn: int = 0
        self.turns_without_progress: int = 0
        self.link_reservations: dict[tuple[int, Connection], int] = {}

    def is_finished(self) -> bool:
        """Ya no queda ningun dron por entregar?"""
        return not self.drones

    def delivered(self) -> list[Drone]:
        """Drones que ya han llegado al end hub."""
        return list(self.end_zone.drones)

    @staticmethod
    def drone_num(drone: Drone) -> int:
        """Numero del dron para desempatar por orden: D1 antes que D10."""
        digits = drone.name[1:] if drone.name.startswith("D") else ""
        if not digits.isdigit():
            return UNKNOWN_DRONE_ORDER
        return int(digits)

    def ordered_drones(self) -> list[Drone]:
        """Drones activos en el orden en que compiten por una plaza."""
        return sorted(self.drones, key=self.drone_num)

    def reserve_link(self, conn: Connection, turn: int) -> None:
        """Anota que `conn` ya tiene un dron comprometido para `turn`."""
        key = (turn, conn)
        self.link_reservations[key] = self.link_reservations.get(key, 0) + 1

    def purge_reservations(self) -> None:
        """Olvida las reservas de turnos ya jugados.

        Nunca toca las del turno actual ni las del siguiente: esas son las
        que siguen en juego, incluida la que un dron en transito se guardo
        para poder aterrizar.
        """
        self.link_reservations = {
            key: count
            for key, count in self.link_reservations.items()
            if key[0] >= self.turn
        }

    def link_is_free(self, conn: Connection, turn: int) -> bool:
        """¿Queda hueco en `conn` para el dron que se committea a `turn`?"""
        return conn.have_capacity(self.link_reservations.get((turn, conn), 0))

    def zone_is_free(
        self,
        zone: Zone,
        arriving: dict[str, int],
        will_leave: dict[str, int],
        will_enter: dict[str, int],
    ) -> bool:
        """¿Queda hueco en `zone` contando lo ya comprometido?

        Los tres diccionarios son la foto de este turno: quien aterriza,
        quien se va y quien acaba de ser aceptado. Se suman porque la zona
        que llega un dron en transito este turno ya cuenta como ocupada.
        """
        reserved = (
            arriving.get(zone.name, 0)
            + will_enter.get(zone.name, 0)
            - will_leave.get(zone.name, 0)
        )
        return zone.can_accept_drone(reserved=reserved)

    def can_start_move(
        self,
        dest: Zone,
        conn: Connection,
        arriving: dict[str, int],
        will_leave: dict[str, int],
        will_enter: dict[str, int],
    ) -> bool:
        """¿Puede este dron moverse ahora a `dest` por `conn`?

        Es la regla completa del turno, no solo una pregunta estructural como
        `Graph.can_move`: mira la conexion, y si `dest` es RESTRICTED tambien
        el turno siguiente, porque cruzarla ocupa el enlace dos turnos.
        """
        if not self.link_is_free(conn, self.turn):
            return False
        if dest.zone_type is ZoneType.RESTRICTED:
            if not self.link_is_free(conn, self.turn + 1):
                return False
        return self.zone_is_free(dest, arriving, will_leave, will_enter)

    def decide(
        self,
        drone: Drone,
        arriving: dict[str, int],
        will_leave: dict[str, int],
        will_enter: dict[str, int],
    ) -> Intent:
        """Decide que hace `drone` este turno y lo compromete si puede.

        El scheduler es estatico: la ruta no se recalcula nunca y un dron que
        no cabe espera. Quien esta en transito no consulta nada, porque el
        hueco que necesita ya era suyo desde el turno en que empezo a cruzar.
        """
        if drone.transit is not None:
            return Intent("arrive", drone)

        following = drone.next_step()
        if following is None:
            return Intent("deliver", drone)

        conn = self.graph.find_connection(drone.position, following)
        if conn is None:
            return Intent("wait", drone)

        if not self.can_start_move(
            following, conn, arriving, will_leave, will_enter
        ):
            return Intent("wait", drone)

        self.reserve_link(conn, self.turn)
        if following.zone_type is ZoneType.RESTRICTED:
            self.reserve_link(conn, self.turn + 1)
        origin = drone.position.name
        will_leave[origin] = will_leave.get(origin, 0) + 1
        will_enter[following.name] = will_enter.get(following.name, 0) + 1
        return Intent("move", drone, to=following, conn=conn)

    def collect_intents(self) -> list[Intent]:
        """Fase 1: pregunta a cada dron que va a hacer, sin mover nada.

        Los drones que aterrizan se cuentan primero porque su aterrizaje no
        es negociable: su plaza en la zona de destino esta comprometida
        desde el turno en que empezaron a cruzar y hay que respectarla para
        que nadie mas se la adjudique.
        """
        ordered = self.ordered_drones()
        arriving: dict[str, int] = {}
        for drone in ordered:
            if drone.transit is None:
                continue
            dest = drone.route[drone.route_index + 1]
            arriving[dest.name] = arriving.get(dest.name, 0) + 1

        will_leave: dict[str, int] = {}
        will_enter: dict[str, int] = {}
        return [
            self.decide(drone, arriving, will_leave, will_enter)
            for drone in ordered
        ]

    def resolve(self, intents: list[Intent]) -> list[str]:
        """Fase 2: aplica las intenciones y devuelve los eventos del turno.

        El orden de los cuatro pasos es obligatorio y va de mas general a mas
        concreto: vaciar, aterrizar, entrar en transito y por ultimo mover.

        El dron que llega al end hub se retira de `self.drones` en el mismo
        turno en que aterriza. Si se hiciera al principio del turno siguiente,
        `step` jugaria un turno entero sin nada que hacer solo para poder
        detectarlo, y ese turno vacio es el ultimo que se contaria.

        El ultimo bucle, el de las entregas, queda como red de seguridad:
        solo queda vivo cuando start y end son la misma zona, caso en el que
        el dron nunca se mueve porque ya esta en su destino.
        """
        movers = self.ordered_intents(intents, "move")
        arrivals = self.ordered_intents(intents, "arrive")
        deliveries = self.ordered_intents(intents, "deliver")
        tokens: list[str] = []

        for intent in movers:
            intent.drone.detach()

        for intent in arrivals:
            drone = intent.drone
            dest = drone.route[drone.route_index + 1]
            drone.attach(dest)
            drone.transit = None
            drone.transit_turns_left = 0
            drone.route_index += 1
            tokens.append(f"{drone.name}-{dest.name}")
            if dest is self.end_zone:
                self.drones.remove(drone)

        for intent in movers:
            restricted_dest = intent.to
            restricted_conn = intent.conn
            if restricted_dest is None or restricted_conn is None:
                continue
            if restricted_dest.zone_type is not ZoneType.RESTRICTED:
                continue
            intent.drone.transit = restricted_conn
            intent.drone.transit_turns_left = 1
            tokens.append(f"{intent.drone.name}-{restricted_conn.label}")

        for intent in movers:
            plain_dest = intent.to
            if plain_dest is None:
                continue
            if plain_dest.zone_type is ZoneType.RESTRICTED:
                continue
            intent.drone.attach(plain_dest)
            intent.drone.route_index += 1
            tokens.append(f"{intent.drone.name}-{plain_dest.name}")
            if plain_dest is self.end_zone:
                self.drones.remove(intent.drone)

        for intent in deliveries:
            self.drones.remove(intent.drone)

        return tokens

    def ordered_intents(
        self, intents: list[Intent], kind: IntentKind
    ) -> list[Intent]:
        """Las intenciones de un tipo, en orden de identificador de dron."""
        return sorted(
            (intent for intent in intents if intent.kind == kind),
            key=lambda intent: self.drone_num(intent.drone),
        )

    def step(self) -> TurnResult | None:
        """Juega un turno entero, o None si ya no queda nada que hacer.

        El reloj avanza al principio y todo lo que ocurre en el turno usa ese
        mismo valor, asi que las reservas se miran contra el.
        """
        if self.is_finished():
            return None

        self.turn += 1
        self.purge_reservations()
        tokens = self.resolve(self.collect_intents())

        if tokens:
            self.turns_without_progress = 0
        else:
            self.turns_without_progress += 1
            if self.turns_without_progress > self.MAX_TURNS_WITHOUT_PROGRESS:
                raise SimulationError(
                    "no progress during "
                    f"{self.turns_without_progress} turns"
                )

        return TurnResult(turn=self.turn, tokens=tokens)
