# 01. Conceptos teóricos

Los 4 conceptos que necesitas antes de tocar Fly-in: **grafos**, **OOP**, **tipado**
y las **reglas pedagógicas** que moldan todo el proyecto. Si te sabes esto, el resto
es código.

---

## 1. Grafos — el mapa de ciudades

Un **grafo** es solo dos cosas:

- **Nodos** (o *vértices*): los lugares. En Fly-in son las **zonas**.
- **Aristas** (o *edges*): los caminos entre lugares. En Fly-in son las **conexiones**,
  y son **bidireccionales** (si `a` se conecta con `b`, se puede ir en ambos sentidos).

Metáfora: un mapa de ciudades donde los pueblos son nodos y las carreteras son aristas.

En tu código (`fly/src/models.py`):

- `Zone` = un nodo: `name`, `x`, `y`, `zone_type`, `max_drones`.
- `Connection` = una arista: apunta a dos `Zone` (`a` y `b`).
- `Graph` = *el* mapa completo: `zones` (dict) + `connections` (lista).

> Regla rápida para la defensa: "nodo" y "arista" son el vocabulario genérico;
> "zona" y "conexión" son cómo Fly-in los llama.

### Buscar el camino más corto: BFS vs Dijkstra

Pregunta clave: ¿todos los caminos cuestan igual?

- **BFS** (búsqueda en anchura): cuenta saltos. Funciona si todas las carreteras
  cuestan lo mismo → como contar estaciones de metro. Rápido y simple.
- **Dijkstra**: respeta **costes distintos**. Como un GPS que prefiere 20 km sin
  peaje antes que 10 km con atascos.

En Fly-in los **tipos de zona** cambian el coste:

| Tipo | Coste |
|---|---|
| `NORMAL` | 1 turno |
| `PRIORITY` | 1 turno |
| `RESTRICTED` | 2 turnos |
| `BLOCKED` | intransitable |

Por eso **BFS no vale**: asume que todo cuesta 1, y aquí `restricted` cuesta 2.
Necesitas Dijkstra (o equivalente). Lo tienes anotado como `ZoneType` en
`fly/src/models.py:12`.

**Regla pedagógica dura**: las librerías de grafos (`networkx`, `graphlib`) están
**prohibidas**. La razón no es burocrática: si `networkx.shortest_path()` te lo
resuelve, no puedes defender "¿cuál es la complejidad de tu pathfinding?" en la
revisión. `heapq` (librería estándar) sí suele valer — verifica el límite exacto
con tu equipo.

---

## 2. OOP — programación orientada a objetos

Metáfora: **fichas de un tablero**. Cada ficha (objeto) sabe su propio estado y
puede hacer cosas consigo misma. No hay una "función global" que mueve a todos:
le pides a cada ficha que se mueva.

Vocabulario mínimo:
- **Clase**: la plantilla (qué saben hacer y recordar).
- **Objeto**: una instancia concreta (un dron de verdad, no "el concepto dron").
- **Atributo**: dato que recuerda el objeto (`self.name`).
- **Método**: acción que sabe hacer (`drone.move_to(zone)`).

Sin OOP, representarías una zona como un diccionario suelto y le pasarías 6
argumentos a cada función. Con OOP, la zona *sabe* su nombre, su tipo, su capacidad
y quién está dentro. Eso es lo que ves en `fly/src/models.py`: `Drone` tiene
`position` y `target` porque "sabe dónde está y a dónde va".

**OOP de fachada** (el anti-patrón que suspende): clases que son solo `dict`s con
nombre — sin ningún método de comportamiento, con atributos mutados libremente desde
fuera. Si `Graph` no hace más que guardar datos y cualquiera puede meter un dron en
una zona llena con `zone.drones.append(...)`, no es OOP de verdad.

Señal de OOP sana: las clases exponen **comportamiento del dominio**
(`zone.can_accept_drone()`, `connection.have_capacity()`, `graph.neighbors(zone)`,
`drone.move_to(zone)`), no solo datos.

---

## 3. Tipado estático — las etiquetas de las cajas

Metáfora: antes de una mudanza etiquetas cada caja ("cocina", "libros") sin que
nadie te lo obligue. Python **no exige etiquetar**, pero si lo haces, una herramienta
(`mypy`) comprueba todo *antes* de arrancar que nunca metiste una taza en la caja de
"libros".

Concretamente:

```python
def parse_positive_int(raw: str, field_name: str, line_no: int) -> int:
```

Aquí dices: "entran tres `str`, sale un `int`". `mypy` revisa que en todo el código
nadie llame a la función con algo que no sea `str` (y que el `return` devuelva `int`).

Es el mismo tipo de red de seguridad que te da un compilador de C, pero opcional y
encima de Python. En Fly-in **no es opcional**: el enunciado exige `mypy` sin
errores. Trátalo como un tercer tipo de test. En `fly/src/models.py` todos los
atributos están anotados (`self.name: str = name`) precisamente por esto.

Dos niveles, en tu Makefile:

```make
lint:        mypy .  # flags relajadas y explícitas
lint-strict: mypy . --strict  # mucho más exigente
```

Ejecuta `make lint-strict` pronto y a menudo. Descubrir 40 errores de tipado el
último día es un mal plan.

---

## 4. Reglas pedagógicas — por qué el proyecto es como es

Son 5 reglas que moldean TODO lo demás. El porqué es siempre el mismo: **que puedas
defenderlo en la revisión**.

1. **Prohibido librerías de grafos** → implementas tú el pathfinding y los
   estructuras de datos, para poder explicarlos.
2. **"Completamente orientado a objetos"** → es un requisito evaluable, no estilo.
3. **`flake8` limpio + `mypy` sin errores** → calidad obligatoria en todo el proyecto.
4. **Una excepción no capturada = "no funcional"** → captura todo en `main`, imprime
   a `stderr` y sal con código distinto de cero (como `fprintf(stderr); return 1;`
   en C). Tu parser ya lo hace con `MapParseError`
   (`fly/src/parser/exceptions.py`).
5. **`make install` debe dejar todo listo desde una máquina limpia** → la revisión
   se hace en la máquina de otra persona. Si `make install` falla ahí, el proyecto
   "no funciona", punto.

### La parte difícil (spoiler)

No es el pathfinding (es un algoritmo de libro). Lo difícil es el **motor de
simulación**: coordinar *muchos* drones que comparten recursos limitados turno a
turno. Eso es un problema de *scheduling*, no de "calcular una ruta". El proyecto
está dividido en capas para que cada fichero sea testeable, tipable y revisable por
separado:

```
parser/        lee el mapa y valida  →  producción de un Graph
models.py      las 4 clases del dominio + la topología del grafo
               (Graph.find_connection, Graph.neighbors, índice de adyacencia)
pathfinding.py rutas de coste mínimo (zone_cost, shortest_path)
simulation.py  el motor turno a turno (Simulation.move_drone)  ← aquí se gana o se pierde la nota
visualization  salida
```

Separar capas desde el día 1 es lo que hace posible pasar `mypy --strict` limpio
y revisar en pareja sin dolor.

> **Dónde vive cada cosa y por qué.** Regla práctica: lo que es *comportamiento de
> una entidad* es método de esa entidad (`zone.can_accept_drone()`,
> `drone.move_to()`); lo que es *preguntas sobre la topología del mapa* es método
> del grafo (`graph.neighbors()`, `graph.find_connection()`); lo que es
> *coordinación* entre varias entidades es de quien las coordina
> (`simulation.move_drone()`, `shortest_path()`). Una función libre que recibe
> `graph` como primer parámetro rompe este patrón — es OOP de fachada.