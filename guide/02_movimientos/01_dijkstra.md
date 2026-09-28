# 05. Dijkstra: encontrar el camino más barato

Con `move_drone` ya sabes **ejecutar** un movimiento válido de una zona a otra lo que todavía no tienes es **quién decide a qué zona ir** — eso es `pathfinding.py`. Como ya viste en `01_conceptos_teoricos.md`, `restricted` cuesta 2 turnos y `normal`/`priority` cuestan 1, así que BFS (contar saltos) da resultados incorrectos: hace falta Dijkstra.

Esta parte añade **una función** al proyecto, `shortest_path` en `pathfinding.py`. El
algoritmo coordina el `Graph` completo, no el estado de un solo objeto, así que no es
un método de `Zone`/`Connection`/`Drone`.

**Dónde vive cada cosa** (esto es fijo, no "depende"):

| Símbolo | Ubicación | Por qué ahí |
|---|---|---|
| `Graph.find_connection(a, b)` | `models.py` | Consulta de adyacencia: es conocimiento del grafo, no un algoritmo |
| `Graph.neighbors(zone)` | `models.py` | Ídem — y precalcula la adyacencia (ver §1.1) |
| `Simulation.move_drone(drone, target)` | `simulation.py` | Ejecuta un paso; decide *cuándo*, no *a dónde* |
| `zone_cost(zone)` | `pathfinding.py` | Peso de arista: solo el algoritmo lo usa |
| `shortest_path(graph, start, end)` | `pathfinding.py` | El algoritmo |

> El subject exige *completamente orientado a objetos* (regla 2 de
> `01_conceptos_teoricos.md`). Una función libre que recibe `graph` como primer
> parámetro es OOP de fachada: son datos pasados de un lado a otro. Por eso
> `find_connection` y `neighbors` son **métodos de `Graph`**, no funciones sueltas
> — el grafo es quien sabe a qué se conecta cada zona.

---

## 1. Qué necesita el algoritmo

DIJKSTRA:
`shortest_path(graph, start, end) -> list[Zone] | None`
` Decide: la secuencia de zonas de coste mínimo entre start y end, o None si no hay camino `

Dos piezas auxiliares que Dijkstra usa por dentro:

`zone_cost(zone) -> int`
` Decide: cuánto cuesta ENTRAR en esa zona (no salir de ella) `

`Graph.neighbors(zone) -> list[Zone]`
` Decide: qué zonas son alcanzables desde zone en un paso, ignorando BLOCKED `

> [Nota]: el coste se mide al **entrar** a la zona, no al salir — por eso `zone_cost` recibe el vecino, no la zona actual. `start` nunca "cuesta" nada porque el dron ya está ahí.

### 1.1. `Graph.neighbors()` requiere adyacencia precalculada

`Graph` guarda sus conexiones en `self.connections`, que es una **lista plana**. Si
`neighbors()` la recorre entera para buscar las que tocan `zone`, cada llamada cuesta
O(E) — y Dijkstra la llama una vez por nodo, así que el algoritmo entero sería
**O(V · E)**.

Por eso `Graph` debe construir un índice de adyacencia **en su `__init__`**, una vez,
y `neighbors()` solo lee ese índice:

```
Graph.__init__
  ├── self.adjacency: dict[str, list[Zone]]  # una lista vacía por cada nombre de zona
  └── for conn in connections:               # cada conexión es bidireccional
        adjacency[conn.a.name].append(conn.b)
        adjacency[conn.b.name].append(conn.a)

Graph.neighbors(zone) -> list[Zone]
  └── [other for other in self.adjacency[zone.name] if other.zone_type is not BLOCKED]
```

Con esto `neighbors()` cuesta O(grado de la zona) y la complejidad real es
**O((V + E) log V)** — que es exactamente lo que vas a tener que defender (§7).

> Ojo: `adjacency` es un índice **derivado**, no una fuente de verdad. `self.connections`
> sigue siendo la lista canónica; `adjacency` solo se escribe una vez al construir el
> grafo y nunca se muta después.

## 2. Reglas que este paso debe respetar (del subject, VII.1/VII.3)

> **`blocked` nunca es un vecino válido**
➔ Implementación: `neighbors()` filtra `zone_type is ZoneType.BLOCKED` antes de devolver la lista, ni siquiera entra en la cola de prioridad

> **`neighbors()` filtra SÓLO por `BLOCKED` — nunca por capacidad**
➔ Implementación: la lista de vecinos sale de `self.adjacency` y quita **solo** los
`BLOCKED`. No filtres por `can_accept_drone()` ni por `connection.have_capacity()`.
El grafo es **estático**: la ruta se calcula una vez sobre la topología, y quién está
dentro de una zona o cruzando un enlace en este turno es información de `simulation.py`.
Si metes ocupación dentro de `neighbors()`, `shortest_path` deja de ser una función
pura y su resultado depende del estado de los drones.

> **Coste según `zone_type`**
➔ Implementación: `normal`/`priority` = 1, `restricted` = 2 — es la misma tabla de `01_conceptos_teoricos.md` §1, aquí se usa como peso de arista dentro de `zone_cost`

> **`priority` "debe ser preferida" pero cuesta igual que `normal`**
➔ Implementación: con el mismo coste, Dijkstra no puede distinguirlas por sí solo; si quieres que gane en un empate, añade un desempate secundario en la cola (ver Tricuñuela 4) — no lo resuelvas subiendo el coste de `normal`, cambiarías el resultado del pathfinding, no solo el orden

> **Sin librerías de grafos**
➔ Implementación: `heapq` (cola de prioridad de la stdlib) es la única ayuda permitida — la regla pedagógica del proyecto exige que puedas explicar la complejidad tú mismo

> **No hay camino posible**
➔ Implementación: si `end` nunca sale de la cola, `shortest_path` devuelve `None` — nunca lances una excepción por esto, es un resultado válido que `simulation.py` debe poder manejar

## 3. El algoritmo

**`models.py`** — los dos métodos que el algoritmo necesita. `find_connection` ya
existe desde `00_primer_movimiento.md`; `neighbors` y el índice de adyacencia son
nuevos:

```python
class Graph:
    def __init__(
        self,
        zones: dict[str, Zone],
        connections: list[Connection],
        nb_drones: int,
    ) -> None:
        self.zones: dict[str, Zone] = zones
        self.connections: list[Connection] = connections
        self.nb_drones: int = nb_drones
        self.adjacency: dict[str, list[Zone]] = {name: [] for name in zones}
        for conn in connections:
            self.adjacency[conn.a.name].append(conn.b)
            self.adjacency[conn.b.name].append(conn.a)

    def find_connection(self, a: Zone, b: Zone) -> Connection | None:
        """Devuelve la conexión entre `a` y `b`, o None si no están unidas."""

    def neighbors(self, zone: Zone) -> list[Zone]:
        """Zonas alcanzables desde `zone` en un paso, excluyendo BLOCKED."""
```

**`pathfinding.py`** — solo el algoritmo:

```python
import heapq

from src.models import Graph, Zone, ZoneType


def zone_cost(zone: Zone) -> int:
    """Coste en turnos de entrar en `zone`."""


def shortest_path(graph: Graph, start: Zone, end: Zone) -> list[Zone] | None:
    """Dijkstra: ruta de coste mínimo entre `start` y `end`.
    Devuelve la lista de zonas (start incluido) o None si no hay camino.
    """
```

## 4. Caso de uso mínimo

```python
graph = parse_map_file("maps/easy/01_linear_path.txt")

route = shortest_path(graph, graph.zones["start"], graph.zones["goal"])
# route == [start, waypoint1, waypoint2, goal]  (o None si no hay camino)

vecinos = graph.neighbors(graph.zones["start"])
# vecinos == [waypoint1, ...]  (nunca None: si no hay, es [])
```

`route` es justo lo que `simulation.py` va a recorrer llamando a
`Simulation.move_drone` zona por zona, turno a turno.

## 5. Tener en cuenta

1. **`Zone` no es comparable por sí sola.** `heapq` compara tuplas elemento a
   elemento, y si dos entradas tienen la misma distancia, Python ntentaría comparar 
   los `Zone` directamente y fallaría (`TypeError`). Por eso la tupla
   lleva `id(zone)` como desempate — nunca compares objetos de dominio en la
   cola sin un criterio de desempate explícito.
2. **El coste se mira al entrar, no al salir.** Si te equivocas y aplicas
   `zone_cost(current)` en vez de `zone_cost(neighbor)`, `start` sumaría coste
   de más y el resultado sería incorrecto aunque "parezca" funcionar en mapas
   simples.
3. **No reutilices `visited` como si fuera BFS.** Aquí `visited` marca "ya
   procesado con su distancia final conocida" — si lo marcas al *descubrir* el
   nodo (como en BFS) en vez de al *sacarlo* de la cola, puedes quedarte con
   una distancia subóptima.
4. **El empate `priority` vs `normal` no se resuelve solo con el coste.** Si
   el subject te pide defender que `priority` se prefiere, una opción limpia
   es añadir un segundo criterio de orden en la tupla de la cola (por ejemplo,
   `0` si es `PRIORITY` y `1` si no, antes del `id`), para que a igualdad de
   distancia gane la ruta con más zonas `priority`. Documenta la decisión que
   tomes — es defendible de varias formas.
5. **Cachear vs recalcular.** Si varios drones comparten `start`/`end`, no
   necesitas correr Dijkstra una vez por dron — puedes calcular la ruta una
   vez y que todos la reutilicen. Ten esto listo para la pregunta del
   subject: *"¿Estás recalculando o cacheando rutas?"*.
6. **Un mapa sin camino es un resultado, no un error.** `shortest_path`
   devolviendo `None` es correcto si `end` está aislado por `blocked` — no lo
   conviertas en `MapParseError` ni en excepción; esa validación ya no es del
   parser, es de la lógica del algoritmo.
7. **Dos contratos distintos, no los mezcles.** `neighbors()` devuelve `[]` cuando
   no hay ningún vecino válido; `shortest_path()` devuelve `None` cuando no hay
   ruta. `None` en `neighbors` te rompe el `for` de Dijkstra con
   `TypeError: 'NoneType' is not iterable`. La razón de la diferencia: para
   "no hay vecinos" la lista vacía **es** un resultado válido del tipo, mientras
   que `None` en `shortest_path` es la señal de que `simulation.py` debe
   abandonar ese dron.

## 6. Qué NO cubre esta parte (viene después)

- Repartir **varios** drones entre rutas distintas para no saturar una misma
  zona/conexión (eso es `simulation.py`, decidiendo *cuándo* cada dron avanza
  por su ruta).
- Recalcular la ruta si `simulation.py` descubre a mitad de camino que una
  zona está llena (routing dinámico/replanificación) — de momento la ruta se
  calcula una vez, sobre el grafo estático.
- Decidir el **tránsito de 2 turnos** por `restricted` (el dron "vive" en la
  conexión un turno antes de aparecer en la zona) — eso también es
  `simulation.py`.

Con `shortest_path` funcionando, `simulation.py` ya no tiene que "pensar" por
dónde va cada dron — solo tiene que decidir *cuándo* cada uno da su siguiente
paso sobre la ruta que ya calculaste, respetando capacidad y evitando
conflictos.

---

## 7. Complejidad y memoria (Explicado sin matemáticas)

El evaluador te preguntará: **"¿Qué tan eficiente es tu algoritmo y cuánta memoria usa?"**  Para responder bien solo necesitas entender la idea clave, sin fórmulas complejas.


### ¿Qué es la complejidad?

La complejidad mide **cuánto aumenta el trabajo cuando el mapa se vuelve más grande**. No se mide en segundos, sino en proporción:
* **$V$ (Vértices):** Cantidad de zonas en el mapa.
* **$E$ (Aristas / Edges):** Cantidad de conexiones entre zonas.


### Complejidad en Tiempo: ¿Por qué es rápido?

Tu algoritmo evita trabajo repetitivo mediante dos optimizaciones clave:

* **Cola de prioridad (`heapq`):** Obtiene la zona más barata de forma casi instantánea, en lugar de comparar todas las opciones disponibles desde cero.
* **Lista de adyacencia (`Graph`):** Prepara un índice con las zonas vecinas una sola vez al inicio. Consultar los vecinos de una zona después es inmediato.

> **Impacto real en el mapa *Challenger* (54 zonas, 70 conexiones):**
> * **Sin optimización:** ~3.800 operaciones.
> * **Con optimización:** ~700 operaciones.
> * **En mapas 10 veces más grandes:** Sin este truco, el programa sería **34 veces más lento**.

---

### Complejidad en Memoria: ¿Cuánto espacio usa?

El consumo de memoria es mínimo y eficiente:

* **Información ligera:** Solo guardas datos básicos por zona y conexión (como *"distancia más barata"* o *"zona de la que vengo"*).
* **Escalabilidad:** Nunca creas tablas gigantes de "todas las zonas contra todas".
* **Resultado:** La memoria crece de forma **proporcional** al tamaño del mapa (lineal), no al cuadrado.

## Complejidad del algoritmo de Dijkstra

- **Complejidad de tiempo:** `O((V + E) log V)`

  - **V:** número de zonas del mapa.
  - **E:** número de conexiones entre zonas.
  - **`V log V`:** coste de insertar y extraer zonas de la cola de prioridad (`heapq`).
  - **`E log V`:** coste de revisar las conexiones y actualizar las distancias cuando se encuentra un camino mejor.
  - **Conclusión:** el algoritmo es muy eficiente porque recorre el mapa sin revisar todas las conexiones repetidamente.

- **Complejidad de memoria:** `O(V + E)`

  - Se almacena el grafo (zonas y conexiones) y las estructuras que usa Dijkstra (distancias, nodos visitados y cola de prioridad).
  - **Conclusión:** la memoria utilizada crece de forma proporcional al tamaño del mapa.