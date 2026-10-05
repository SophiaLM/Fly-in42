# 06. Completando `pathfinding.py`: Dijkstra con `PathFinder`

Ya tienes el mapa parseado y los modelos con su comportamiento (`zone_cost`,
`neighbors`, `can_move`…). Este archivo cierra la parte de routing con la
arquitectura que finalmente implementaste: una clase `PathFinder` que conoce su
grafo y recuerda las rutas ya calculadas, en vez de una función suelta.

Orden del documento: **finalidad** (§1) → **lógica y orden de escritura** (§2) →
**`heapq` en profundidad** (§3) → **pseudocódigo** (§4) → **preguntas y
respuestas** (§5) → **errores reales que se depuraron** (§6) → **código final y
resumen** (§7).

---

## 1. Finalidad del archivo

`pathfinding.py` responde a **una sola pregunta**:

> *Dado un `start` y un `end`, ¿por qué zonas paso y cuánto me cuesta?*

Es el **GPS** del proyecto (routing = *por dónde*; scheduling = *cuándo*). No
mueve drones, no mira quién está en cada zona y no conoce los turnos de la
simulación: eso es de `simulation.py`.

| | |
|---|---|
| **Se construye con** | `PathFinder(graph)` |
| **Método principal** | `shortest_path(start, end)` → `list[Zone]` (con `start` y `end`) o `None` si no hay camino |
| **Estado propio** | El `graph` y una **caché** de rutas ya calculadas |
| **Lee** | La topología (`graph.neighbors`) y el coste de entrar (`zone.zone_cost()`) |
| **No toca** | Ocupación de zonas, capacidad de enlaces, posición de los drones |

```
parser ─► Graph ─► PathFinder(graph) ─► .shortest_path(a, b) ─► ruta ─► simulation
                   ▲ estás aquí
```

`shortest_path` es una **función pura sobre un grafo estático**: mismo `(start,
end)` → siempre la misma ruta. Eso es lo que hace segura la caché.

Uso desde el resto del proyecto:

```python
finder = PathFinder(graph)                 # una vez, al montar la simulación
route = finder.shortest_path(start, end)   # las veces que haga falta
```

---

## 2. La lógica, y el orden en que conviene escribirla

### Paso 0 — Qué ya te da `models.py`

| Necesito saber… | Lo resuelve | Nota |
|---|---|---|
| ¿A qué zonas puedo ir desde aquí? | `graph.neighbors(zone)` | Ya excluye las `BLOCKED` |
| ¿Cuántos turnos cuesta entrar en una zona? | `zone.zone_cost()` | 1 / 1 / 2; `ValueError` en `BLOCKED` (nunca le llega una) |
| ¿Cómo obtengo la zona a partir de su nombre? | `graph.zones[name]` | Diccionario por nombre |

### De dentro hacia fuera: el orden de escritura

Conviene escribir las piezas **de la más pequeña e independiente a la que las
usa a todas**, no de arriba a abajo del archivo:

1. **`_step_cost` primero.** Solo necesita una `Zone`, sin grafo ni búsqueda
   alrededor. Se testea sola: `assert _step_cost(zona) == (1, 0)`.
2. **`_build_route` después.** Tampoco depende de Dijkstra, solo de que exista
   un `prev` ya construido. Se puede probar con un `prev` inventado a mano.
3. **`_dijkstra` al final.** Es quien **usa** a las dos anteriores: al
   escribirla, sus piezas ya están escritas y probadas, así que si algo falla
   sabes que el problema está en la combinación, no en una pieza suelta.
4. **`shortest_path` la última**, porque solo envuelve a `_dijkstra` con la
   caché — no tiene lógica de búsqueda propia.

Es la idea de "construir desde las hojas": cada pieza nueva se apoya en piezas
ya verificadas.

### Qué es estado de la clase y qué es local a una búsqueda

Esta es la distinción que justifica que sea una clase y no una función:

| Dato | ¿Dónde vive? | Por qué |
|---|---|---|
| `graph` | **Atributo** (`self.graph`) | Es el mismo para todas las búsquedas |
| `_cache` | **Atributo** (`self._cache`) | Debe **sobrevivir** entre búsquedas: es su razón de ser |
| `dist`, `prev`, `visited`, `heap` | **Variables locales** de `_dijkstra` | Pertenecen a **una** búsqueda concreta |

Si `dist` o `visited` fueran atributos, la segunda búsqueda heredaría los datos
de la primera y daría rutas incorrectas. Regla práctica: **si un dato solo
tiene sentido mientras dura una búsqueda, es local; si tiene que sobrevivir
entre llamadas, es atributo**.

### `@staticmethod`: cuándo sí y cuándo no

La pregunta que decide es siempre la misma: **¿el método necesita algo de
`self`?**

| Método | ¿Usa `self.graph` o `self._cache`? | Marca |
|---|---|---|
| `_step_cost(zone)` | No. Solo mira `zone.zone_cost()` y `zone.zone_type` | `@staticmethod` |
| `_build_route(prev, start, end)` | No. Solo recorre el `prev` que le pasan | `@staticmethod` |
| `_dijkstra(self, start, end)` | Sí: `self.graph.zones[...]`, `self.graph.neighbors(...)` | método normal |
| `shortest_path(self, start, end)` | Sí: lee y escribe `self._cache` | método normal |

**Qué cambiaría si no lo fueran:** en el comportamiento, nada — se comprobó
ejecutando la misma implementación sin `@staticmethod` y todos los tests
seguían pasando, igual que `flake8` y `mypy --strict`. Lo que cambia es la
firma (tendrían un `self` que nunca se usa) y la comunicación con quien lee el
código: `@staticmethod` dice de un vistazo "esto no toca el estado del
objeto". Es exactamente la señal que detecta `pylint` con su regla
`no-self-use` cuando falta — no es un error, es un aviso de estilo que puedes
adelantarte a dar tú mismo.

### El coste es un par: `(turnos, preferencia)`

El subject pide dos cosas a la vez: minimizar turnos (lo que puntúa) y
preferir `priority` en empates (*"should be prioritized"*). Se resuelven con
un coste de dos números que se comparan **en orden**: primero turnos; solo si
empatan, preferencia.

| Zona que entras | Turnos | Preferencia |
|---|---|---|
| `NORMAL` | 1 | 0 |
| `PRIORITY` | 1 | **−1** |
| `RESTRICTED` | 2 | 0 |

El `-1` no es un coste real — el coste real de `priority` sigue siendo 1 turno,
eso lo da `zone.zone_cost()`. Es un **descuento** que hace más pequeño (mejor)
el número que Dijkstra compara, y solo actúa cuando dos rutas empatan en
turnos. Por eso vive en `_step_cost` (algoritmo), no en `models.py` (mundo).

Como los turnos van primero, `priority` **nunca alarga una ruta**:
`(4, 0)` gana siempre a `(5, -3)`, aunque la segunda tenga más `priority`.

### El bucle, resumido

1. **Extraer** de la frontera la zona más barata.
2. Si ya estaba cerrada, descartarla (entrada obsoleta).
3. **Cerrarla**: su coste ya es definitivo.
4. Si es `end`, **parar**.
5. Para cada vecino no cerrado: si `coste_actual + coste_de_entrar(vecino)`
   mejora lo conocido, actualizar y meter en la frontera.

Se para **al cerrar `end`**, no al descubrirlo. Si el bucle termina y `end`
nunca se cerró, no hay camino: se devuelve `None` (resultado válido, no error).

### Reconstruir la ruta: por qué de `end` a `start`, y no al revés

`prev` solo puede guardar **"desde quién llegué"**, nunca **"hacia quién voy"**:
una zona puede tener muchos vecinos que intenten mejorarla, pero se queda con
uno solo (el mejor); en cambio, esa misma zona puede ser el mejor camino
*hacia* varias zonas a la vez. Por ejemplo, si `start` es predecesor de `b` y
de `c`, `prev[b] = start` y `prev[c] = start` conviven sin problema — pero la
relación inversa (`next[start] = ?`) tendría que apuntar a dos sitios con una
sola clave, y un diccionario no puede.

Por eso la única dirección en la que **se puede caminar con los datos que
tienes** es hacia atrás: empiezas en `end`, preguntas `prev[end]`, y sigues
hasta `start`. Construir la lista así (con `append`, que es `O(1)`) y darle la
vuelta una vez al final (`O(n)`) sigue siendo `O(n)` en total — óptimo.
Insertar directamente en orden con `route.insert(0, zona)` sería `O(n)` **por
cada inserción**, es decir `O(n²)` en total: mucho peor en rutas largas.

---

## 3. `heapq`, en profundidad

`heapq` mantiene una `list` de Python organizada internamente como *min-heap*:
el elemento más pequeño siempre accesible en `O(1)`, y meter o sacar algo
cuesta `O(log n)`, sin ordenar la lista entera cada vez. No es un tipo nuevo:
sigue siendo una `list`, pero con un orden interno que solo se mantiene si la
tocas **a través de las funciones del módulo**, nunca con `append` directo.

### Las ocho funciones del módulo, y cuáles usamos

| Función | Qué hace | ¿La usamos? |
|---|---|---|
| `heapq.heappush(heap, item)` | Inserta manteniendo el orden | **Sí** — al descubrir o mejorar un vecino |
| `heapq.heappop(heap)` | Saca y devuelve el mínimo | **Sí** — al inicio de cada vuelta del `while` |
| `heapq.heapify(lista)` | Convierte una lista ya existente en heap, en `O(n)` | No — construimos el heap insertando de uno en uno |
| `heapq.heappushpop(heap, item)` | Inserta y saca el mínimo en una sola llamada, más barata que por separado | No — no encaja: primero decidimos si insertamos, no siempre extraemos a la vez |
| `heapq.heapreplace(heap, item)` | Saca el mínimo y luego inserta, sin comprobar tamaño | No, mismo motivo |
| `heapq.merge(*iterables)` | Fusiona secuencias ya ordenadas en una sola, de forma perezosa | No — sirve para combinar streams ya ordenados (logs por fecha), no es este problema |
| `heapq.nlargest(n, ...)` / `heapq.nsmallest(n, ...)` | Los `n` mayores/menores sin ordenar toda la colección | No — es para "dame el top N", otro caso de uso |

En Dijkstra solo hacen falta dos: `heappush` para meter descubrimientos,
`heappop` para sacar el más barato.

### Qué te ahorra frente a hacerlo a mano

| Alternativa | Coste de "sacar el más barato" | Problema |
|---|---|---|
| Lista sin ordenar, buscar el mínimo cada vez | `O(n)` por búsqueda | El algoritmo entero se degrada a `O(V²)` |
| Lista siempre ordenada (insertar en su sitio) | `O(n)` por inserción | Mismo coste, solo cambia dónde se paga |
| `heapq` | `O(log n)` para insertar y para extraer | Es la diferencia entre `O(V²)` y `O((V+E) log V)` |

### Detalle importante: por qué la clave es `(coste, nombre)` y no `(coste, zona)`

`heapq` compara las entradas **elemento a elemento**. Con el mismo coste, pasa
a comparar el segundo elemento. Un `Zone` no se puede comparar con otro
(`TypeError`), y lo traicionero es que solo salta con **3 o más** entradas en
el heap: los mapas pequeños pasan, y revienta en el laberinto grande. Con
`str` siempre se puede comparar, y de regalo el desempate sale **determinista**
(alfabético): mismos resultados en cada ejecución.

---

## 4. Pseudocódigo explicativo

```
clase PathFinder:

    __init__(graph):
        self.graph  = graph
        self._cache = {}                       # (start, end) → ruta | None

    shortest_path(start, end):                 # ── PÚBLICO ──
        clave = (nombre de start, nombre de end)
        si clave no está en la caché:
            caché[clave] = _dijkstra(start, end)
        ruta = caché[clave]
        devolver None si ruta es None, si no una COPIA de ruta

    _step_cost(zona):                          # ── coste de entrar ──
        preferencia = -1 si zona es PRIORITY, si no 0
        devolver (zona.zone_cost(), preferencia)

    _dijkstra(start, end):                     # ── la búsqueda ──
        dist    = { start: (0, 0) }            # LOCALES: viven solo esta búsqueda
        prev    = {}
        visited = {}
        heap    = [ ((0, 0), start) ]

        mientras heap no esté vacío:
            (coste, nombre) = sacar el mínimo del heap
            si nombre ya está en visited:  continuar     # entrada obsoleta
            cerrar nombre
            si nombre es end:  romper                    # coste definitivo

            para cada vecino de la zona `nombre`:        # neighbors quita BLOCKED
                si vecino está cerrado:  continuar
                nuevo = coste + _step_cost(vecino)       # al ENTRAR en el vecino
                si vecino sin coste conocido, o nuevo < el conocido:
                    dist[vecino] = nuevo
                    prev[vecino] = zona actual
                    meter (nuevo, vecino) en heap

        # ── AQUÍ, fuera del while, no dentro ──
        si end nunca se cerró:  devolver None
        devolver _build_route(prev, start, end)

    _build_route(prev, start, end):            # ── reconstruir ──
        ruta = [end]
        mientras el último de ruta no sea start:    # comparar por NOMBRE
            añadir prev[último]
        dar la vuelta a ruta
        devolver ruta
```

---

## 5. Preguntas y respuestas

**¿Por qué una clase si el algoritmo sería el mismo como función?**
El subject exige un proyecto *completamente orientado a objetos*, y una
función que recibe `graph` como primer argumento roza el patrón de fachada.
Pero la razón más sólida es que la clase tiene **estado real** (`graph` y la
caché), que responde con código a la pregunta del subject *"¿estás
recalculando o cacheando rutas?"*.

**¿Por qué la caché devuelve una copia y no la lista guardada?**
Si `Simulation` recorriera la ruta con `route.pop(0)` y recibiera la misma
lista que hay en la caché, la siguiente consulta devolvería una ruta ya
mutilada. Copiar cuesta `O(longitud de la ruta)`, insignificante frente a una
búsqueda entera.

**¿Por qué se cachea también el `None`?**
Porque "no hay camino" cuesta calcularlo tan caro como cualquier otra
respuesta (la búsqueda recorre todo lo alcanzable) y volverá a preguntarse
igual.

**¿Por qué `zone_cost()` se llama sobre el vecino y no sobre la zona actual?**
Porque el subject fija el coste por el **tipo de la zona de destino**. Si se
aplicara a la actual, `start` sumaría coste de más y los mapas con
`restricted` darían rutas equivocadas.

**¿La preferencia negativa no rompe Dijkstra? Dijkstra odia los pesos negativos.**
El problema de los pesos negativos es que seguir avanzando *abarate* un
camino. Aquí no ocurre: cada paso suma al menos 1 turno, y como el primer
número del par manda, avanzar siempre "empeora" la comparación aunque la
preferencia baje.

**¿Por qué `None` y no una excepción si no hay camino?**
Es un resultado válido de la búsqueda: excepción para lo que *no debería
pasar*, valor de retorno para lo que *puede pasar con normalidad*.
`Simulation` debe poder decidir qué hacer con un dron sin ruta.

**¿Qué pasa si `end` es `blocked`, o si `start` es `end`?**
Si `end` es `blocked`, `neighbors` nunca la ofrece y el resultado es `None`.
Si `start` es `end`, se extrae, se cierra, coincide con `end` y se para: la
ruta es `[start]`. Ninguno necesita un `if` especial.

**¿Cuál es la complejidad?**
`O((V + E) log V)` en tiempo por búsqueda y `O(V + E)` en memoria. Depende de
que `graph.neighbors()` sea barato, y lo es gracias a `_adjacency`.

**¿Por qué no meter también el coste total de la ruta en lo que devuelve `shortest_path`?**
Se probó (`tuple[list[Zone], int]`) y generó problemas de tipado en cadena: la
caché, la reconstrucción y el propio `shortest_path` tenían que cargar con ese
segundo valor aunque no siempre hiciera falta — fue la causa de 6 de los 8
errores de `mypy --strict` que se encontraron (§6). Se resolvió con
`path_cost(route)` aparte: una función pequeña que suma `zone_cost()` de la
ruta cuando se necesita, sin complicar el tipo de la caché.

---

## 7. Código final y resumen

### `pathfinding.py`

```python
"""Rutas de coste minimo entre zonas del mapa (Dijkstra).

Dado un start y un end, ¿por qué zonas paso y cuánto me cuesta?
"""

import heapq

from src.models import Graph, Zone, ZoneType

# Coste de un camino: (turnos, preferencia). Se compara en ese orden:
# los turnos mandan; la preferencia solo desempata entre rutas empatadas.
Cost = tuple[int, int]


class PathFinder:
    """Calcula rutas de coste mínimo sobre un grafo estático.

    Guarda las rutas ya calculadas: como el grafo no cambia, la misma
    pregunta (start, end) siempre tiene la misma respuesta.
    """

    def __init__(self, graph: Graph) -> None:
        self.graph: Graph = graph
        self._cache: dict[tuple[str, str], list[Zone] | None] = {}

    @staticmethod
    def _step_cost(zone: Zone) -> Cost:
        """Coste de entrar en `zone`: sus turnos y su preferencia.

        La preferencia es -1 en una zona PRIORITY y 0 en el resto: cuanto
        más baja, mejor. Solo desempata entre rutas con los mismos turnos.
        """
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

    def _dijkstra(self, start: Zone, end: Zone) -> list[Zone] | None:
        """Búsqueda de Dijkstra sin caché. Devuelve la ruta o None."""
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
                turns, preference = cost
                step_turns, step_pref = self._step_cost(neighbor)
                new_cost = (turns + step_turns, preference + step_pref)
                known = dist.get(neighbor.name)
                if known is None or new_cost < known:
                    dist[neighbor.name] = new_cost
                    prev[neighbor.name] = zone
                    heapq.heappush(heap, (new_cost, neighbor.name))

        # Fuera del while: aquí es donde ya se sabe si end se cerró o no.
        if end.name not in visited:
            return None
        return self._build_route(prev, start, end)

    def shortest_path(self, start: Zone, end: Zone) -> list[Zone] | None:
        """Ruta de coste mínimo entre `start` y `end`.

        Minimiza los turnos y, a igualdad de turnos, prefiere la ruta con
        más zonas PRIORITY. Devuelve la lista de zonas (start incluido) o
        None si no hay camino. Devuelve una copia: modificarla no altera
        la caché.
        """
        key = (start.name, end.name)
        if key not in self._cache:
            self._cache[key] = self._dijkstra(start, end)
        route = self._cache[key]
        return None if route is None else list(route)

    def path_cost(self, route: list[Zone]) -> int:
        """Turnos totales de recorrer `route` (sin contar el start).

        Utilidad aparte, no participa en la búsqueda ni en la caché: solo
        suma zone_cost() de cada zona de la ruta menos la primera, que es
        el punto de partida y no cuesta nada llegar a ella. Sirve para el
        reporte de métricas secundarias del subject (VII.6: total path
        cost), sin tener que arrastrar ese dato por toda la caché.
        """
        return sum(zone.zone_cost() for zone in route[1:])
```

### Resumen de todo

| Pieza | Qué hace | Por qué así |
|---|---|---|
| `Cost = tuple[int, int]` | Alias: `(turnos, preferencia)` | El par se compara en orden: turnos manda, preferencia desempata |
| `PathFinder.__init__` | Guarda `graph` y crea `_cache` | Es el estado que justifica la clase |
| `_step_cost` (`@staticmethod`) | Coste de entrar en una zona | No usa `self`; envuelve `zone_cost()` del modelo y añade la preferencia, que es decisión del algoritmo, no del mundo |
| `_build_route` (`@staticmethod`) | Reconstruye la ruta con `prev` | No usa `self`; recorre hacia atrás porque es la única dirección que `prev` permite, y da la vuelta una vez al final (`O(n)`, no `O(n²)`) |
| `_dijkstra` | La búsqueda | `dist`, `prev`, `visited`, `heap` son **locales**: viven una sola búsqueda |
| `visited` marcado al extraer | Coste definitivo | Es lo que distingue a Dijkstra de un BFS |
| `if name in visited: continue` | Descarta entradas obsoletas del heap | Mantiene `O((V + E) log V)` |
| Comprobación de `end` **fuera** del `while` | Detecta "sin camino" | El bug real de §6.1: dentro del `while` devolvía `None` casi siempre |
| `shortest_path` | API pública: consulta la caché o busca | Una sola puerta de entrada; devuelve copias |
| `path_cost` | Turnos totales de una ruta ya calculada | Aparte de la caché, para no repetir el error de tipado de §6.3 |

**Complejidad:** `O((V + E) log V)` tiempo por búsqueda, `O(V + E)` memoria.
**Sin librerías de grafos:** solo `heapq` de la stdlib.