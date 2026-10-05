"""Construcción del grafo: zonas, conexiones y orquestador parse_map_file."""

from __future__ import annotations

from ..models import Connection, Graph, Zone
from .exceptions import MapParseError
from .io import read_lines, strip_noise
from .metadata import classify_line, parse_metadata, split_metadata_block
from .validators import parse_int_field, parse_positive_int, parse_zone_type
from .validators import parse_color


def parse_zone_line(
    body: str,
    meta: dict[str, str],
    is_start: bool,
    is_end: bool,
    line_no: int,
) -> Zone:
    """Ensambla las propiedades de una zona e instancia el objeto Zone."""
    tokens = body.split()
    if len(tokens) != 3:
        raise MapParseError(
            f"Line {line_no}: expected '<name> <x> <y>', got {body!r}"
        )
    name, x_raw, y_raw = tokens

    if "-" in name:
        raise MapParseError(
            f"Line {line_no}: zone name cannot contain '-': {name!r}"
        )

    x = parse_int_field(x_raw, "x", line_no)
    y = parse_int_field(y_raw, "y", line_no)
    zone_type = parse_zone_type(meta.get("zone"), line_no)
    color = parse_color(meta.get("color"), line_no)

    max_drones: int | None = None
    if not (is_start or is_end):
        # El subject (VI) fija max_drones=1 por defecto, asi que solo None
        # cuando no hay metadata sigue significando "sin limite" para un Zone
        # construido a mano. En start_hub/end_hub la capacidad se ignora: se
        # acepta el metadata pero se descarta, y no es un error de validacion
        # (regla explicita de VII.4).
        max_drones = parse_positive_int(
            meta.get("max_drones", "1"), "max_drones", line_no
        )

    return Zone(
        name=name,
        x=x,
        y=y,
        zone_type=zone_type,
        max_drones=max_drones,
        is_start=is_start,
        is_end=is_end,
        color=color,
    )


def parse_connection_line(
    body: str,
    meta: dict[str, str],
    zones: dict[str, Zone],
    seen: set[tuple[str, str]],
    line_no: int,
) -> Connection:
    """Construye un Connection verificando extremos y evitando duplicados."""
    name_a, sep, name_b = body.partition("-")
    name_a = name_a.strip()
    name_b = name_b.strip()

    if not sep:
        raise MapParseError(
            f"Line {line_no}: expected '<zone>-<zone>', got {body!r}"
        )
    for name in (name_a, name_b):
        if name not in zones:
            raise MapParseError(f"Line {line_no}: unknown zone {name!r}")

    first, second = sorted((name_a, name_b))
    pair = (first, second)
    if pair in seen:
        raise MapParseError(
            f"Line {line_no}: duplicate connection between "
            f"{name_a!r} and {name_b!r}"
        )
    seen.add(pair)

    # El subject (VI) fija max_link_capacity=1 por defecto: una conexion nunca
    # es "sin limite", asi que el tipo es int y no int | None.
    max_link_capacity = parse_positive_int(
        meta.get("max_link_capacity", "1"), "max_link_capacity", line_no
    )

    return Connection(zones[name_a], zones[name_b], max_link_capacity)


def parse_map_file(path: str) -> Graph:
    """Orquestador: lee, limpia y parsea el fichero para construir el Graph.

    Raises:
        MapParseError: si el fichero viola cualquier regla de formato.
    """
    lines = strip_noise(read_lines(path))
    if not lines:
        raise MapParseError("empty map file")

    first_line_no, first_line = lines[0]
    prefix, body = classify_line(first_line)
    if prefix != "nb_drones":
        raise MapParseError(
            f"Line {first_line_no}: expected 'nb_drones:' first"
        )
    nb_drones = parse_positive_int(body, "nb_drones", first_line_no)

    zones: dict[str, Zone] = {}
    connections: list[Connection] = []
    seen_connections: set[tuple[str, str]] = set()
    start_count = 0
    end_count = 0

    for line_no, line in lines[1:]:
        prefix, body = classify_line(line)
        name_part, meta_part = split_metadata_block(body)
        meta = parse_metadata(meta_part)

        if prefix in ("start_hub", "end_hub", "hub"):
            zone = parse_zone_line(
                name_part,
                meta,
                is_start=(prefix == "start_hub"),
                is_end=(prefix == "end_hub"),
                line_no=line_no,
            )
            if zone.name in zones:
                raise MapParseError(
                    f"Line {line_no}: duplicate zone name: {zone.name!r}"
                )
            zones[zone.name] = zone
            start_count += zone.is_start
            end_count += zone.is_end
        elif prefix == "connection":
            connection = parse_connection_line(
                name_part, meta, zones, seen_connections, line_no
            )
            connections.append(connection)
        else:
            raise MapParseError(
                f"Line {line_no}: unknown directive {prefix!r}"
            )

    if start_count != 1:
        raise MapParseError(
            f"expected exactly one start_hub, found {start_count}"
        )
    if end_count != 1:
        raise MapParseError(
            f"expected exactly one end_hub, found {end_count}"
        )

    return Graph(zones, connections, nb_drones)
