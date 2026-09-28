# 02. Modelos actuales

El estado **actual** de `fly/src/models.py`: las 4 clases del dominio del proyecto
(`Zone`, `Connection`, `Drone`, `Graph`) y el enum `ZoneType`. Son el "vocabulario"
objeto a objeto que usa el resto del programa — el parser los construye, el
pathfinding los recorre, la simulación los mueve.

Estos modelos son un punto de partida: **se modificarán en el futuro** (ver
disclaimer al final).

---

## 1. `ZoneType` — los cuatro tipos de zona

`fly/src/models.py:12`

```python
class ZoneType(Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"
```

- Un `Enum`: el parser valida el string `zone=` contra `enum.value` y el resto del
  programa usa `ZoneType.RESTRICTED` etc., no strings sueltos.
- Determina **cuánto cuesta atravesar la zona** en el pathfinding: `normal`/`priority`
  = 1 turno, `restricted` = 2, `blocked` = intransitable.

## 2. `Zone` — un nodo del grafo

`fly/src/models.py:21`

```python
class Zone:
    def __init__(self, name, x, y, zone_type, max_drones, is_start=False, is_end=False):
        # self.name, self.x, self.y
        # self.zone_type, self.max_drones
        # self.is_start, self.is_end
        # self.drones: list[Drone] = []
```

| Atributo | Tipo | Qué representa |
|---|---|---|
| `name` | `str` | Identificador único (prohibidos `-` y espacios) |
| `x`, `y` | `int` | Coordenadas (pueden ser negativas) |
| `zone_type` | `ZoneType` | El coste de atravesarla |
| `max_drones` | `int \| None` | Límite de capacidad; `None` = sin límite (siempre `None` en start/end) |
| `is_start` / `is_end` | `bool` | Es el hub de salida / de llegada |
| `drones` | `list[Drone]` | ¿Qué drones están dentro? (lo usa la simulación) |

Una `Zone` es **el nodo del grafo**: sabe dónde está, cómo cuesta pasarla y quién
está dentro de ella.

## 3. `Connection` — una arista del grafo

`fly/src/models.py:44`

```python
class Connection:
    def __init__(self, a: Zone, b: Zone, max_link_capacity: int | None):
        # self.a, self.b, self.max_link_capacity
```

- **Bidireccional**: si `a` se conecta con `b`, se viaja en ambos sentidos (el
  parser normaliza `a-b` y `b-a` como la misma conexión).
- `max_link_capacity = None` significa sin límite.
- Es la **arista**: enlaza dos objetos `Zone` de verdad (no nombres), así que el
  grafo nunca puede apuntar a una zona que no existe.

## 4. `Drone` — el agente de la simulación

`fly/src/models.py:55`

```python
class Drone:
    def __init__(self, name: str, position: Zone, target: Zone):
        # self.name, self.position, self.target
```

- "Un dron que sabe dónde está y hacia dónde va" (`position`, `target`).
- `nb_drones` del mapa determina cuántos se crean. `name` suele ser `D1`, `D2`, ...

## 5. `Graph` — el mapa completo

`fly/src/models.py:64`

```python
class Graph:
    def __init__(self, zones: dict[str, Zone], connections: list[Connection], nb_drones: int):
        # self.zones, self.connections, self.nb_drones
```

| Atributo | Estructura | Por qué esa estructura |
|---|---|---|
| `zones` | `dict[str, Zone]` | Acceso por nombre en O(1); el nombre es la clave natural |
| `connections` | `list[Connection]` | Lista plana de aristas |
| `nb_drones` | `int` | Cuántos drones creará la simulación |

> **Regla rápida**: `Graph` = el mapa de ciudades. `zones` son los pueblos (nodos),
> `connections` las carreteras (aristas). "Nodo/arista" es el vocabulario genérico;
> "zona/conexión" es cómo Fly-in los llama.

## 6. Disclaimer — por qué se modificarán en el futuro

Estos modelos son **deliberadamente simples** (solo datos, sin métodos de
comportamiento) porque el parser se escribió primero. Se espera que evolucionen:

- `Graph` no tiene todavía `add_zone()` ni `add_connection()`: hoy el parser los
  construye con `__init__` recibiendo estructuras ya listas, pero el diseño ideal
  de la guía (`guide/01_map_parser.md`) los añade vía métodos para que el propio
  `Graph` detecte nombres duplicados. Esa lógica migrará del parser al modelo.
- **OOP "de fachada" es un anti-patrón que suspende la revisión**: clases que son
  solo `dict`s con nombre y atributos mutados desde fuera. La señal de OOP sana será
  que las clases expongan **comportamiento del dominio** (`zone.can_accept_drone()`,
  `connection.have_capacity()`, `graph.neighbors(zone)`, `drone.move_to(zone)`) —
  eso aún no existe y es lo que vendrá.

No trates estos modelos como definitivos: son la base de datos sobre la que el
parser ya construye el `Graph`, pero crecerán métodos a medida que se desarrolle el
pathfinding y la simulación.