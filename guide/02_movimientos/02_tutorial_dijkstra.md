# 06. Tutorial: implementando `pathfinding.py` paso a paso

`01_dijkstra.md` dice **qué** hacer. Este archivo explica **cómo**: la lógica detrás de
cada decisión, los errores que vas a cometer, y los números que tienes que obtener para
saber que funciona.

Nada de aquí sustituye a la guía. Si has las dos, lo que manda es la guía.

---

## 0. Antes de escribir nada: dos bloqueos

### 0.1. `Graph.neighbors()` no funciona todavía

```python
# fly/src/models.py:124
for other in self._adjacency[zone.name]
```

`self._adjacency` no existe en ningún sitio — `Graph.__init__` no lo construye. Pasa
lo que pase:

```
AttributeError: 'Graph' object has no attribute '_adjacency'
```

Sin `neighbors()` no hay Dijkstra que probar. Arreglalo primero siguiendo la §1.1 de
`01_dijkstra.md`: construir `self.adjacency: dict[str, list[Zone]]` en `__init__`, con
las dos direcciones de cada conexión. Ojo al nombre: la guía dice `adjacency`, sin
guion bajo.

### 0.2. Dos imports que hay que activar

```python
# fly/src/pathfinding.py — al principio del fichero
import heapq

from src.models import Graph, Zone, ZoneType
```

`heapq` está comentado y `ZoneType` no está importado. Los dos hacen falta: `ZoneType`
porque `zone_cost` compara contra el enum, `heapq` porque es la cola de prioridad.

---

## 1. `zone_cost(zone) -> int` — la función pequeña

### Qué decide

Cuántos **turnos** cuesta *entrar* en una zona. Solo eso.

| `zone_type` | Turnos |
|---|---|
| `NORMAL` | 1 |
| `PRIORITY` | 1 |
| `RESTRICTED` | 2 |
| `BLOCKED` | — (ver abajo) |

### Pseudocódigo

```
zone_cost(zone):
    si zone.zone_type es NORMAL:   devolver 1
    si zone.zone_type es PRIORITY: devolver 1
    si zone.zone_type es RESTRICTED: devolver 2
    (llegar aquí: la zona es BLOCKED)
```

### Tres cosas que no son obvias

**`ZoneType` es un `Enum`, se compara con `is`.** No compares contra el string:

```python
zone.zone_type is ZoneType.RESTRICTED      # sí
zone.zone_type == "restricted"             # no — es un Enum, no un str
```

**El coste se mira al ENTRAR, no al salir.** Por eso el parámetro es el vecino, no la
zona actual. Si te equivocas y aplicas `zone_cost(current)`, la `start` suma su coste
aunque el dron ya esté ahí — y en los mapas con `restricted` el resultado cambia de
verdad, no solo en los detalles.

**¿Qué haces con un `BLOCKED`?** Esta es una decisión tuya y hay que defenderla. La
respuesta honesta: **`neighbors()` ya los eliminó, así que `zone_cost` nunca recibe
uno**. Puedes devolver `0` documentando ese porqué, devolver un entero grande
("intransitable"), o lanzar `ValueError`. Las tres son defendibles; la que no lo es es
dejarlo sin pensar y que salga un `KeyError` del dict.

---

## 2. Las tres estructuras de `shortest_path`

| Estructura | Tipo | Para qué |
|---|---|---|
| `dist` | `dict[str, int]` | La distancia más barata conocida hasta cada zona |
| `prev` | `dict[str, Zone]` | De qué zona se vino, para reconstruir el camino |
| `heap` | `list[tuple[int, int, str]]` | La cola de prioridad |

**Por qué las claves son `str` y no `Zone`.** `Zone` no define `__eq__` ni `__hash__`,
así que Python usa identidad: dos zonas distintas nunca colisionan y el dict funciona.
Pero `zone.name` es igual de válido, más legible en un traceback, y —lo importante—
te deja tipar el heap con `(int, int, str)` **sin meter objetos de dominio dentro de la
cola**. Eso es lo que hace seguro el `heapq` (§4).

---

## 3. El bucle, paso a paso

```
shortest_path(graph, start, end):

    # — casos límite —
    si start is end:  devolver [start]

    # — inicialización —
    dist    = { start.name: 0 }
    prev    = {}
    visited = conjunto vacío
    heap    = [ (0, 0, start.name) ]

    # — el bucle —
    mientras heap no esté vacío:

        (coste, desempate, nombre) = extraer el mínimo de heap

        si nombre ya está en visited:  continuar
        marcar nombre en visited

        si nombre es end.name:  romper        # respuesta encontrada

        para cada vecino en graph.neighbors(zona actual):
            si vecino ya está en visited:  continuar
            nuevo = coste + zone_cost(vecino)
            conocido = dist.get(vecino.name)
            si conocido no existe o nuevo < conocido:
                dist[vecino.name] = nuevo
                prev[vecino.name] = zona actual
                insertar (nuevo, desempate_del_vecino, vecino.name) en heap

    # — se acabó la cola sin llegar a end —
    si end.name no está en dist:  devolver None

    # — reconstruir el camino —
    ruta = [end]
    mientras ruta[-1].name != start.name:
        ruta.append(prev[ruta[-1].name])
    invertir(ruta)
    devolver ruta
```

### Las cuatro líneas que importan

**`visited` se marca al EXTRAER, no al descubrir.** Es lo que separa Dijkstra de BFS.
Si marcas al descubrir, te quedas con una distancia subóptima y nunca la actualizas.

**`if nombre in visited: continuar` es el "stale check".** El heap puede tener varias
entradas para la misma zona (una vieja y una mejorada). La vieja se descarta aquí. Sin
esto, cada zona se procesa tantas veces como se haya reencolado y el algoritmo pasa de
O((V+E) log V) a O(V·E) — y la complejidad que vas a defender deja de ser verdad.

**`nuevo = coste + zone_cost(vecino)`, no `coste + zone_cost(zone_actual)`.** El peso
de la arista es la zona a la que entras.

**`if end.name not in dist: return None` — nunca una excepción.** Un mapa sin camino es
un resultado válido. Si lanzas, `simulation.py` revienta y el subject te lo cobra.

### Reconstrucción

`prev` guarda la zona **desde la que** llegaste, así que el camino se recorre al revés:
empiezas en `end`, saltas a `prev[end]`, y así hasta llegar a `start`. La condición de
parada es `nombre == start.name` — y por eso el caso `start is end` del principio se
resuelve solo (la lista tiene un elemento y el `while` no entra).

---

## 4. La tupla del heap: el error que casi todos cometen

`heapq` **compara las tuplas elemento a elemento**. Si dos entradas tienen la misma
distancia, Python pasa a comparar el segundo elemento. Si ese segundo elemento es un
`Zone`... no hay `<` entre dos `Zone`.

Lo peligroso es **cuándo** salta:

| Elementos en el heap | Resultado |
|---|---|
| 2 | ✅ Funciona. `heappop` saca la raíz y no necesita comparar |
| 3+ | 💥 `TypeError: '<' not supported between instances of 'Zone' and 'Zone'` |

Es decir: **pasa tu test del mapa lineal de 4 zonas y revienta en el laberinto de 17.**
No lo busques en el mapa fácil.

Tres desempates válidos, de mejor a peor:

| Desempate | Determinista | Notas |
|---|---|---|
| `zone.name` | ✅ sí | Tu opción. `str` se compara bien y es legible |
| contador monotónico | ✅ sí | Un `int` que se incrementa, orden de inserción |
| `id(zone)` | ❌ **no** | Cambia entre ejecuciones. Tests que fallan sin que cambies nada |

La Tricuñuela 4 de la guía propone `id(zone)`. Funciona, pero el determinismo importa:
con `name` los tests son reproducibles.

---

## 5. El desempate `priority` — y por qué el evidente no cumple

La guía dice que `priority` "debe ser preferida" pero cuesta lo mismo que `normal`. La
forma evidente es poner un segundo criterio en la tupla:

```
heap = [ (coste, 0 si es PRIORITY si no 1, nombre) ]
```

**Cuidado: esto NO garantiza lo que crees.** Ese `0`/`1` desempata cuando la distancia
que acabas de extraer es exactamente igual en ese instante. Pero dos rutas con el mismo
coste total pueden pasar por puntos intermedios distintos, y el desempate se aplica en
esos puntos, no al final. El resultado depende del camino, no solo del destino.

| Lo que quieres | Lo que la tupla `(coste, 0/1, nombre)` da |
|---|---|
| A igualdad de **coste final**, gana la ruta con más `priority` | Gana la que tuvo menos `priority` en los puntos donde empató por sorts |

### La forma que sí cumple

Tratar la distancia como un **par ordenado** y hacer Dijkstra sobre pares:

```
coste_de(zone) = (turnos, penalización_por_no Ser priority)
```

`(5, 0)` es mejor que `(4, 3)`: menos turnos siempre gana; a igual turnos, menos
penalizaciones. Eso **sí** da la garantía global.

**El precio**: la distancia deja de ser un `int` y pasa a ser una tupla. La comparación
de la cola sigue funcionando (`tuple < tuple` compara elemento a elemento, y el primer
elemento decide casi siempre), pero `dist` queda tipada como `dict[str, tuple[int, int]]`
y el código se complica.

**Mi recomendación**: implementa la versión simple, que es la que la guía sanciona y la
que se defiende en dos frases. Si el subject te exige la garantía fuerte, cambia a
pares y documéntalo.

---

## 6. Errores → síntomas

| Lo que escribiste | Lo que pasa |
|---|---|
| `cost + zone_cost(zone_actual)` | La `start` suma coste de más. En mapas con `restricted` la ruta sale mal |
| Marcas `visited` al descubrir el nodo | Distancias subóptimas. Es el bug clásico de "Dijkstra hecho a BFS" |
| No compruebas `if nombre in visited` al extraer | Funciona, pero O(V·E) en vez de O((V+E) log V) |
| `neighbors()` devuelve `None` en vez de `[]` | `TypeError: 'NoneType' is not iterable` en el `for` |
| Pones la `Zone` en la tupla del heap | `TypeError: '<' not supported...` — pero solo con 3+ elementos |
| Reconstruyes sin invertir la lista | La ruta sale al revés, de `end` a `start` |
| `float("inf")` como valor inicial de `dist` | `mypy --strict` se queja: has convertido el dict en `dict[str, float]`. Usa `dist.get(nombre)` y comprueba `is None` |
| Lanzas excepción si no hay camino | Prohibido. `None` es un resultado válido |
| Filtras vecinos por capacidad en `neighbors()` | `shortest_path` deja de ser pura y depende del estado de los drones |

---

## 7. Cómo sabes que funciona

Ejecuta esto sobre los 10 mapas de `fly/maps/` y compara. Estos números están
verificados; si los tuyos no coinciden, hay un bug.

| Mapa | V | E | Coste | Zonas |
|---|---|---|---|---|
| `easy/01_linear_path` | 4 | 3 | 3 | 4 |
| `easy/02_simple_fork` | 5 | 5 | 3 | 4 |
| `easy/03_basic_capacity` | 4 | 3 | 3 | 4 |
| `medium/01_dead_end_trap` | 6 | 5 | 4 | 5 |
| `medium/02_circular_loop` | 7 | 7 | 5 | 5 |
| `medium/03_priority_puzzle` | 7 | 7 | 4 | 5 |
| `hard/01_maze_nightmare` | 17 | 22 | 6 | 7 |
| `hard/02_capacity_hell` | 15 | 21 | 5 | 6 |
| `hard/03_ultimate_challenge` | 31 | 37 | 12 | 13 |
| `challenger/01_the_impossible_dream` | 54 | 70 | **19** | 16 |

Ejemplo de ruta completa, la del challenger:

```
start → gate_hell1 → maze_trap_a1 → maze_trap_a2 → micro_gate1 → overflow_hell1
      → conv_restricted1 → conv_restricted2 → conv_restricted3 → final_merge
      → final_torture1 → final_torture2 → final_torture3 → final_torture4
      → final_torture5 → impossible_goal
```

16 zonas = 15 saltos, pero **19 turnos**. La diferencia son las zonas `restricted`.

### El mapa que demuestra por qué BFS no vale

`medium/03_priority_puzzle.txt` tiene dos caminos a `goal`:

| Ruta | Saltos | Turnos |
|---|---|---|
| `start → slow_path1 → slow_path2 → merge_point → goal` | 4 | **5** |
| `start → fast_junction → fast_path → merge_point → goal` | 4 | **4** |

Los dos hacen **4 saltos**. BFS no puede distinguirlos: devuelve el que encuentre
primero, y uno cuesta un turno más. Dijkstra sabe cuál es el barato.

### Dos avisos honestos

**En los 10 mapas oficiales, Dijkstra y BFS devuelven la misma ruta.** Lo único que
difiere es el número que reportan: BFS dice "15 saltos" donde la verdad son 19 turnos.
Nadie te va a decir que tu pathfinding está mal por un test que compara rutas; el
subject te va a preguntar por la complejidad y por el coste, que es otra cosa.

**Ningún mapa oficial tiene `zone=blocked`.** Ni una sola aparición en los 10 ficheros.
Eso significa que el filtro de `neighbors` **no está verificado por los tests del
repo** — necesitas un mapa propio con una zona `blocked` en medio de un corredor, o
nunca vas a saber si funciona. Mínimo:

```
nb_drones: 1
start_hub: a 0 0
hub: b 1 0 [zone=blocked]
hub: c 2 0
end_hub: z 3 0
connection: a-b
connection: b-c
connection: c-z
```

`shortest_path(a, z)` debe devolver `None`: el único camino pasa por `blocked`.

---

## 8. Casos límite

| Situación | Resultado esperado |
|---|---|
| `start is end` | `[start]` — lista de un elemento |
| `end` aislada por `blocked` | `None` |
| `end` en otro componente conexo | `None` |
| Grafo de una sola zona con `start` y `end` distintos | La ruta que exista, o `None` |

Ninguno de estos debe lanzar una excepción.

---

## 9. Solución completa

Referencia. Flake8 limpio y `mypy --strict` limpio, y produce los costes de la tabla
de la §7.

```python
import heapq

from src.models import Graph, Zone, ZoneType

COSTES: dict[ZoneType, int] = {
    ZoneType.NORMAL: 1,
    ZoneType.PRIORITY: 1,
    ZoneType.RESTRICTED: 2,
    ZoneType.BLOCKED: 0,
}


def zone_cost(zone: Zone) -> int:
    """Coste en turnos de entrar en `zone`.

    Un BLOCKED devuelve 0 porque `neighbors()` ya lo ha descartado:
    nunca se entra en uno, así que su coste es irrelevante.
    """
    return COSTES[zone.zone_type]


def shortest_path(graph: Graph, start: Zone, end: Zone) -> list[Zone] | None:
    """Dijkstra: ruta de coste mínimo entre `start` y `end`.

    Devuelve la lista de zonas (start incluido) o None si no hay camino.
    """
    dist: dict[str, int] = {start.name: 0}
    prev: dict[str, Zone] = {}
    visited: set[str] = set()
    heap: list[tuple[int, int, str]] = [(0, 0, start.name)]

    while heap:
        cost, _, name = heapq.heappop(heap)
        if name in visited:
            continue
        visited.add(name)

        if name == end.name:
            break

        zone = graph.zones[name]
        for neighbor in graph.neighbors(zone):
            if neighbor.name in visited:
                continue
            new_cost = cost + zone_cost(neighbor)
            known = dist.get(neighbor.name)
            if known is None or new_cost < known:
                dist[neighbor.name] = new_cost
                prev[neighbor.name] = zone
                tiebreak = 0 if neighbor.zone_type is ZoneType.PRIORITY else 1
                heapq.heappush(heap, (new_cost, tiebreak, neighbor.name))

    if end.name not in dist:
        return None

    route = [end]
    while route[-1].name != start.name:
        route.append(prev[route[-1].name])
    route.reverse()
    return route
```

### Notas sobre la solución

- **`dist.get(...)` con comprobación de `None`, no `inf`.** Un `float("inf")` como
  valor por defecto convertiría `dist` en `dict[str, float]` y `mypy --strict` se
  quejaría. Con `.get()` + `is None` el dict se queda en `int`.
- **`if neighbor.name in visited: continue`** es redundante con la comprobación del
  `while` (un vecino ya cerrado no mejora), pero hace explícita la invariante y evita
  encolar trabajo inútil.
- **`_` en `(cost, _, name)`** descarta el desempate al extraer: al extraer solo te
  importa el coste. El desempate cuenta al *insertar*.
- **El caso `start is end` no necesita caso especial.** El heap empieza con `start`,
  se extrae, `name == end.name` rompe, y la reconstrucción da `[start]`. Está aquí en
  la §3 solo para que lo veas explícito.
