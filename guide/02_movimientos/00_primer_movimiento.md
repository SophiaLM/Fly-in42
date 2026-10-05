# 04. Primer movimiento: mover un dron de "a" a "b"

Con el parser terminado ya tienes un `Graph` validado. Esta parte es el primer
paso hacia `simulation.py`: **mover un solo dron entre dos zonas conectadas**,
respetando las reglas de ocupación (`VII.2`/`VII.3` del subject). Todavía **no**
es el motor de simulación completo (eso viene después) — es la pieza mínima que
ese motor va a reutilizar turno a turno.

Esta es la parte donde los modelos dejan de ser "de fachada" (ver disclaimer de
`02_basic_models.md`): `Zone`, `Connection` y `Drone` ganan sus primeros
**métodos de comportamiento**.

---

## 1. Qué comportamiento se añade a cada clase

ZONE:
can_accept_drone() -> bool
` Decide: ¿Hay hueco? (len(self.drones) < max_drones, o sin límite si is_start/is_end/max_drones is None) `

add_drone(drone) / remove_drone(drone)
` Decide: Mete/saca el dron de self.drones `

CONNECTION:
other_zone(zone) -> Zone
` Decide: Dado un extremo, devuelve el otro (evita if conn.a == z: ... else: ... repetido) `

have_capacity() -> bool
` Decide: ¿La conexión tiene capacidad libre? (contador de tránsitos activos vs max_link_capacity) `

add_drone(drone) / remove_drone(drone)
` Decide: Mete/saca el dron de connection.drones mientras está en tránsito `

GRAPH:
find_connection(a: Zone, b: Zone) -> Connection | None
` Decide: ¿Están a y b unidas por una conexión? (método, no función suelta) `

DRONE:
move_to(zone: Zone) -> None
` Decide: Actualiza self.position; no valida reglas — eso es responsabilidad de quien orquesta el movimiento `

> [Nota]: para que `have_capacity()` pueda contar cuántos drones están atravesando la
> conexión ahora mismo, `Connection` también necesita su propia lista igual que `Zone`.
> Esa lista la puebla `Simulation` durante el **tránsito**: cuando un dron sale de
> `zone_a` y todavía no ha aparecido en `zone_b`, está en `connection.drones`. Por eso
> `Connection` necesita `add_drone`/`remove_drone` simétricos a los de `Zone` — y por eso
> `move_drone` **no** los toca: en este paso el dron pasa de golpe de una zona a otra
> y no se registra tránsito. El tránsito de 2 turnos de `restricted` es la fase de
> `simulation.py`, no de este paso.

> Regla de diseño: las clases exponen **si algo es posible**
> (`can_accept_drone`, `have_capacity`) y **cómo ejecutarlo** (`add_drone`,
> `remove_drone`, `move_to`), pero la decisión de *cuándo* moverse (turnos,
> scheduling) no vive aquí — eso es `simulation.py`, no `models.py`.

## 2. Reglas que este paso debe respetar (del subject, VII.2/VII.3)

> **`blocked` nunca se entra**  
➔ Implementación: Verificar zone_type != ZoneType.BLOCKED antes de nada

> **Zona llena → no se puede entrar**  
➔ Implementación: zone.can_accept_drone()

> **Conexión inexistente entre `a` y `b`**  
➔ Implementación: graph.find_connection(a, b) — método de `Graph`, no función suelta

> **`max_link_capacity`**  
➔ Implementación: connection.have_capacity()

> **`start`/`end` sin límite de capacidad**  
➔ Implementación: max_drones se ignora ahí (ya lo hace el parser; aquí solo respétalo)

> **Coste según `zone_type`**  
➔ Implementación: normal/priority = 1 turno, restricted = 2 (manejo multi-turno en simulation.py)

## 3. La función orquestadora: `move_drone`

Vive en `models.py` — no , porque decide *ejecutar* un paso ya decidido.

Y no es una **función libre** con `graph` como primer parámetro: el subject exige
*completamente orientado a objetos*, así que el `Graph` no se pasa de mano en mano
sino que lo posee quien orquesta. `move_drone` es un **método de `Graf`**,
que es la clase que ya posee el grafo y la lista de drones:

```python
class Simulation:
    """El motor turno a turno: posee el grafo y decide quién se mueve y cuándo."""

    def __init__(self, graph: Graph) -> None:
        self.graph: Graph = graph
        self.drones: list[Drone] = [...]

    def move_drone(self, drone: Drone, target: Zone) -> bool:
        """Intenta mover `drone` desde su posición actual a `target`.

        Devuelve True si el movimiento se ejecutó, False si no era válido
        (no conectado, zona bloqueada, sin capacidad).
        """
        connection = self.graph.find_connection(drone.position, target)
        if connection is None:
            return False
        if target.zone_type is ZoneType.BLOCKED:
            return False
        if not target.can_accept_drone():
            return False
        if not connection.have_capacity():
            return False

        drone.position.remove_drone(drone)
        target.add_drone(drone)
        drone.move_to(target)
        return True
```

- `Graph.find_connection(a, b)` (método de `models.py`): recorre
  `graph.connections` buscando la que tenga `{a, b}` como extremos
  (bidireccional, así que compara en ambos sentidos).
- El orden importa: **sales antes de comprobar si cabes** en el destino
  (regla del subject: "Drones moving out of a zone free up capacity for
  that same turn") — por eso `remove_drone` va antes de `add_drone`.

## 4. Caso de uso mínimo

```python
graph = parse_map_file("maps/easy/01_linear_path.txt")
drone = Drone("D1", position=graph.zones["start"], target=graph.zones["goal"])
simulation = Simulation(graph)

ok = simulation.move_drone(drone, graph.zones["waypoint1"])
# ok == True  → drone.position es ahora waypoint1
```

## 5. Tricuñuelas a tener en cuenta

1. **No confundas "conectado" con "adyacente en el sentido correcto".** Las
   conexiones son bidireccionales — `find_connection` debe encontrar tanto
   `a-b` como `b-a` sin duplicar lógica (reutiliza el mismo patrón que ya
   usaste en el parser para normalizar duplicados).
2. **`can_accept_drone()` en `start`/`end` siempre es `True`.** No apliques el
   `len(drones) < max_drones` ahí; usa el flag `is_start`/`is_end` primero.
3. **No implementes todavía el movimiento a 2 turnos de `restricted`.** Este
   paso mueve una zona por llamada; el "el dron queda en tránsito en la
   conexión" es responsabilidad del bucle de turnos en `simulation.py`, no
   de `move_drone`.
4. **`remove_drone`/`add_drone` deben ser simétricos.** Si `move_drone`
   devuelve `False` a mitad de las comprobaciones, el dron no debe haber
   salido de ningún sitio — valida **todo** antes de mutar nada.
5. **Un dron que ya llegó a `end` no debería poder "moverse" de nuevo.**
   Decide ahora si eso es un `assert`, una excepción, o simplemente algo que
   `simulation.py` nunca deja que ocurra (no se vuelve a llamar `move_drone`
   sobre drones ya entregados).

## 6. Qué NO cubre esta parte (viene después)

- Mover **varios** drones en el mismo turno sin que se pisen (eso es
  `simulation.py`, el motor turno a turno).
- El tránsito de 2 turnos por `restricted` (el dron "vive" en la conexión un
  turno antes de aparecer en la zona).
- Elegir **a qué zona** moverse — eso es `pathfinding.py` (Dijkstra, porque
  `restricted` cuesta 2 y BFS no vale, ver `01_conceptos_teoricos.md`).
- Deadlocks y espera estratégica cuando no hay movimiento posible.

Este paso es deliberadamente pequeño: una vez que `move_drone` funciona y
tiene tests, el motor de simulación es "solo" llamarlo muchas veces con la
lógica de turnos y capacidad por encima.
