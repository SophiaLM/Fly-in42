*Creado por sophluna para peer evaluating*

# ask&ques.md — Compilatorio de preguntas y respuestas

> **Alcance:** todo lo que sé de **cómo funciona mi programa por dentro** y de
> **los conceptos teóricos** del proyecto. Recopila el parser, los modelos, el
> grafo, el pathfinding, la simulación y la visualización, con lo verificado
> contra el código real.
>
> **Fuente de verdad:** el código de `fly/src/`. Este documento se escribe
> después de ejecutar, no de recordar: si una respuesta no se puede comprobar en
> el código, no está aquí.

> **Cómo usar este documento.** No es un tutorial: es el fichero que consultas
> cuando el peer review te pregunte *"¿por qué hiciste esto?"*. Cada respuesta
> está escrita para poder **decirse en voz alta**, y todas remiten a una función
> o a una clase concreta —nunca a un número de línea, que se desactualiza— para
> que puedas abrir el fichero y señalarlo.
>
> Las referencias entre bloques (por ejemplo *"ver E5"*) son internas al propio
> documento: si buscas la respuesta a por qué se reparte la flota entre varias
> rutas, el índice te lleva al bloque y al número exactos.

## Índice

| Bloque | Contenido | Preguntas |
|---|---|---|
| **A** | El parser, línea a línea: formato, metadata, validación y errores | 15 |
| **B** | Los modelos y el grafo: zonas, conexiones, drones, invariantes | 14 |
| **C** | El pathfinding: Dijkstra, el coste par, las rutas alternativas | 20 |
| **D** | Teoría, OOP, herramientas y visualización | 26 |
| **E** | La simulación: el turno, las dos fases, las capacidades | 17 |

Bloques temáticos: **A** responde *"¿cómo lees el fichero?"*, **B** *"¿cómo es
el modelo de datos?"*, **C** *"¿cómo decides por dónde va cada dron?"*, **D**
*"¿por qué se escriben las cosas así?"* (conceptos, complejidad, estilo, colores)
y **E** *"¿cómo se mueven los drones turno a turno?"*.

> **Una nota de notación, para no confundir.** Las preguntas se numeran `A1`,
> `B1`, `C1`… y se citan así: *"ver E7"*. Los drones del proyecto se llaman
> `D1`, `D2`… y en los ejemplos salen dentro de bloques de código o entrecomillados
> como `D1-waypoint1`. Cuando un dron aparece en prosa se dice **"el dron D1"**, para que
> `D1` a secas nunca pueda confundirse con la pregunta D1.

---

# Bloque A — El parser

### A1. ¿Por qué el parseo es de una sola pasada, hacia delante?

Porque el enunciado lo permite: §VII.4 dice *"Connections must link only
**previously defined** zones"*. Como una conexión solo puede apuntar a zonas ya
leídas, al llegar a una línea `connection: a-b` **ya tienes** ambos extremos en el
`dict`. No hace falta una segunda pasada ni ningún grafo intermedio.
`parse_map_file` recorre la lista de líneas una vez y va construyendo el `Graph`
según lee. Con un fichero de 200 líneas, dos pasadas serían el doble de I/O para
obtener exactamente el mismo resultado.

### A2. ¿Por qué `partition("-")` y no `split("-")`?

Porque `split` devuelve una lista y hay que contar posiciones; `partition`
devuelve una tupla de tres con el separador **en el medio**, siempre. En
`parse_metadata` (`clave=valor`), en `classify_line` (el prefijo `hub:`) y en
`parse_connection_line` (`zona-zona`) eso convierte *"¿dónde corto?"* en *"tengo
el antes, el `=`, y el después"*, sin `[0]`/`[1]` que se pueden indexar mal.
Además `partition` **no falla** si no hay separador: devuelve `("", "", texto)`,
y el `if not sep` de `parse_connection_line` detecta el caso limpio.

### A3. ¿Cómo se detectan los nombres de zona duplicados?

Con un `if zone.name in zones` dentro del bucle de `parse_map_file`. Se hace
**ahí** y no al final, por un principio que generaliza a todo el parser: *cada
comprobación vive donde está disponible su información*. Un duplicado se ve en
el momento de insertar. En cambio, *"exactamente un `start_hub` y un
`end_hub`"* **no se puede saber hasta haber leído todo el fichero** — de ahí los
contadores `start_count` y `end_count` que se comprueban al final de
`parse_map_file`.

### A4. ¿Por qué `a-b` y `b-a` son la misma conexión?

Porque las conexiones son **bidireccionales** (§VI): `a-b` y `b-a` describen la
misma arista, solo que escrita al revés. Si no se normalizara, un mapa podría
declarar la misma conexión dos veces y la lista `connections` tendría un
duplicado — que rompería `find_connection` y el índice de adyacencia. La
solución, en `parse_connection_line`: `sorted((name_a, name_b))` produce una
clave canónica, y un `set` de esas claves detecta el duplicado **con una sola
comprobación para ambos sentidos**.

### A5. ¿Cómo se detecta que un nombre de zona lleva un espacio?

No buscándolo. `body.split()` **ya partió** los espacios, así que
`hub: mi zona 3 4` llega como 4 tokens en vez de 3, y la comprobación es de
**aridad**: `if len(tokens) != 3` en `parse_zone_line`. Es un bonus de usar
`split()`: el parser no necesita un tokenizer, porque el formato ya está
separado por espacios.

### A6. ¿Por qué hay dos funciones para enteros?

Porque las coordenadas **admiten negativos** y las capacidades **no**. El
challenger tiene zonas en `y = -1` e incluso `y = -2`, y `hard/02_capacity_hell`
tiene el `start` en `0 -1`, así que `parse_int_field` solo exige que sea un
entero; `parse_positive_int` además exige `> 0`. Usar la misma para las dos
habría rechazado un mapa válido o aceptado `max_drones=0`.

### A7. ¿Por qué `max_drones` en `start_hub`/`end_hub` se ignora sin dar error?

Porque §VII.4 lo dice literalmente: *"it is ignored and is **not** a validation
error"*. Son las dos únicas zonas sin límite (§VII.2: todos empiezan ahí, todos
terminan ahí). Así que `parse_zone_line` ni siquiera mira el valor cuando es
start o end: el `if not (is_start or is_end)` salta el parseo entero.
Consecuencia bonus: `Zone.max_drones` queda `None` **exactamente** en esas dos
zonas, así que `None` significa una sola cosa en todo el modelo — y por eso el
tipo `int | None` es honesto.

### A8. ¿Por qué el default de `max_drones` es `1` y no `None`?

Porque §VI lo dice: *"`max_drones=<number>` (**default: 1**)"*, y §VII.2 lo
remata: *"By default, a zone may contain at most one drone at any given turn"*.
`None` en mi modelo significa **sin límite**, así que dejar `None` por defecto
desactivaba la restricción en la mayoría de los enlaces de los propios mapas de
prueba. Los defaults son parte del **formato del fichero**, así que se aplican
en el parser (`meta.get("max_drones", "1")`), no en el modelo. Por eso
`Connection.max_link_capacity` es `int` y no `int | None`: nunca hay ausencia,
luego la unión era imposible.

### A9. ¿Qué pasa si alguien pone un `#` al final de una línea?

Hoy es un **error**, y de dos formas distintas según dónde esté el `#`. En una
línea de zona, el `#` se cuenta como token extra y salta la comprobación de
aridad:

```
hub: h 1 0 # nota        →  Line 3: expected '<name> <x> <y>', got 'h 1 0 # nota'
```

En una línea de conexión el fallo es distinto y más confuso, porque
`parse_connection_line` parte por el primer guion y se lleva el resto:

```
connection: h-e # nota   →  Line 6: unknown zone 'e # nota'
```

`strip_noise` solo descarta líneas **completas** que empiezan por `#`. El
enunciado (§VI) dice *"Comments start with `#` and are ignored"*, sin aclarar si
pueden ir en línea. Asumo que un comentario es una línea entera, y por eso
`strip_noise` no toca nada más. Ningún mapa oficial trae comentarios en línea, así
que la decisión no afecta a la validación real.

### A10. ¿Por qué el orden de la metadata no importa?

Porque `parse_metadata` la convierte a un `dict`, y un `dict` no guarda orden que
se pueda depender de... pero **sí** garantiza que la búsqueda por clave es
exacta. La regla "los tags pueden ir en cualquier orden" (§VI) sale gratis: da
igual si el mapa escribe `[zone=restricted color=red]` o `[color=red
zone=restricted]`. El riesgo es el contrario: si el código iterara la metadata,
el resultado **dependería del orden del fichero**, y eso es exactamente lo que
el proyecto no quiere.

### A11. ¿Por qué una excepción propia (`MapParseError`) y no `ValueError` pelado?

Por dos razones. Una práctica: `main` captura **`MapParseError`** y sale con `1`;
si el parser lanzara `ValueError` genérico, el `except` también lo atraparía y se
tragaría bugs internos como si fueran errores de formato del usuario. Y de
contrato: `ValueError` es *"el tipo de valor es incorrecto"*, y un mapa mal
formado no es un valor mal formado, es un **documento** mal formado. Es la
distinción entre "error del usuario" y "bug de programador".

### A12. ¿Dónde se comprueba cada cosa, dentro o fuera del bucle?

La respuesta es *depende de cuándo exista la información*, y es la misma idea
que A3:

| Se comprueba… | Por qué |
|---|---|
| Dentro del bucle: nombre duplicado, aridad, tipo de zona, color vacío, capacidad positiva, zona inexistente, conexión duplicada | Toda esa información ya está en la línea actual |
| Al final de `parse_map_file`: exactamente un start y un end | Requiere haber leído **todo** el fichero |
| Antes del bucle: la primera línea es `nb_drones` | Es la regla de §VII.4; si no, no se puede parsear nada |

### A13. ¿Por qué `main` sale con `1` y no con otro código?

Por convención de Unix: `0` = todo bien, distinto de `0` = fallo. Y porque §III.1
trata *"crash during the review"* como no funcional, lo que implica un mensaje
claro a `stderr` y un código de salida que un script pueda comprobar. De ahí el
`f"error: {exc}"` de `main` en vez de un `print` a secas.

### A14. ¿Se valida la metadata contra una lista de claves válidas?

No, y es una decisión consciente. `parse_metadata` acepta cualquier
`clave=valor`: una línea con `[foo=bar zone=priority]` se parsea bien, aplica el
`zone=priority` e **ignora** el `foo`. Lo que hay que entender es que hay dos
niveles distintos:

| Nivel | Qué valida |
|---|---|
| `parse_metadata` | La **forma**: que cada token tenga `=` y que no haya claves repetidas |
| `validators.py` | El **contenido** de las cuatro claves que el proyecto entiende: `zone`, `color`, `max_drones`, `max_link_capacity` |

§VI lista las claves pero no dice que haya que rechazar las desconocidas. Y
rechazarlas sería peor: un mapa puede llevar pistas extra para otro consumidor, y
que el simulador no las entienda no es motivo para declararlo inválido.

### A15. ¿Por qué `parse_zone_type` recorre el Enum en vez de usar `ZoneType(valor)`?

Porque el objetivo no es obtener el enumerado —eso lo haría `ZoneType(valor)`
en una línea— sino **el mensaje de error**. `parse_zone_type` recorre el Enum
completando el `MapParseError` con la lista de valores permitidos:

```
zone='restrcted' is not valid. Allowed values: normal, blocked, restricted, priority.
```

Una excepción mal explicada es medio bug: el revisor tiene que abrir el código
para saber qué escribir. Y el tipado por delante de nada de eso: el `-> ZoneType`
de la firma obliga a que toda rama devuelva un enumerado de verdad.

---

# Bloque B — Los modelos y el grafo

### B1. ¿Qué es un invariante y quién lo protege?

Un **invariante** es una afirmación que debe ser cierta en todo momento. El de
este proyecto es:

> Un dron está en `zona.drones` **si y solo si** `drone.position is zona`.

No se mantiene solo: hay que protegerlo. Y lo protegen **`Drone.detach()`** y
**`Drone.attach()`**, los dos únicos sitios que cambian la ocupación.
`detach` valida que el invariante estuviera bien **antes** de romperlo, y lanza
`ValueError` si el dron no estaba en la zona que dice `position`; `attach` delega
en `zone.add_drone`, que lanza si el destino está lleno. Sin esa pareja, la
capacidad del proyecto no se aplicaba y nada fallaba.

### B2. ¿Por qué `move_to` es un atajo y no el método principal?

Porque la simulación necesita **vaciar antes de llenar**, y eso no se puede
expresar con un método que hace las dos cosas. Por eso `Drone` tiene tres
entradas y una regla de oro:

| Método | Qué hace | Cuándo se usa |
|---|---|---|
| `detach()` | Saca el dron de su zona. **No** cambia `position` | La simulación, al empezar a resolver el turno |
| `attach(zone)` | Aterriza el dron y sincroniza `position` | La simulación, al final de la fase de aplicar |
| `move_to(zone)` | Atajo: `detach()` + `attach()` | Fuera de la simulación |

La regla de oro está en el docstring de `move_to`: **nadie debe llamar a
`move_to` durante la resolución de un turno**. Si se llamara, el orden de las
listas dejaría de ser "vaciar todos, luego llenar todos" y volvería a depender
del orden de iteración. El atajo existe por comodidad, no por necesidad.

### B3. ¿Y qué pasa si el destino está lleno cuando se llama a `attach`?

Lanza `ValueError` desde `zone.add_drone`, y el dron se queda **donde estaba**,
porque `attach` llama a `add_drone` **antes** de asignar `self.position`. Ese
orden importa: si se asignara `position` primero, el fallo dejaría al dron
claiming estar en dos sitios a la vez, y el invariante de B1 quedaría roto de
forma silenciosa.

Y ojo al matiz de `move_to`, que es un atajo: como `detach()` va primero, un
fallo en `attach()` deja al dron **sin estar en ninguna zona**, no en dos. Es un
estado intermedio que el invariante de B1 no cubre, y por eso `move_to` no se
usa en la simulación (ver B2).

### B4. ¿Por qué la regla de `blocked` vive en `can_accept_drone` y no en `can_move`?

Porque `add_drone` es la **única vía** por la que un dron puede entrar en una
zona, y llama a `can_accept_drone`, que devuelve `False` siempre si la zona es
`BLOCKED`. Así que es **imposible** alojar un dron en una bloqueada — no porque
alguien lo compruebe en el punto de decisión, sino porque el objeto se niega a
alojarlo. Compáralo con poner el `if` en `can_move`: también funciona, pero deja
`add_drone` como puerta trasera. La diferencia se ve en el peer review:
*"comprobé que no se entraba"* → *"`add_drone` no lo permite, y es la única
puerta"*.

Además el filtrado ocurre ya en el routing: `Graph.neighbors()` descarta las
zonas `BLOCKED`, así que ni siquiera se consideran candidatas. Verificado con un
mapa propio: una zona `blocked` que dead-end nunca recibe un dron, y el
pathfinding tampoco la visita.

### B5. ¿Por qué hay un `can_move` y un `move_drone`?

Es **CQS** (Command-Query Separation): un método **pregunta** o **ejecuta**, no
las dos cosas. `Graph.can_move` es una pregunta pura: no cambia nada, así que se
puede consultar muchas veces para evaluar opciones sin comprometerse con ninguna.
`Graph.move_drone` ejecuta: valida usando `can_move` y, si puede, mueve. Y
devuelve `False` **sin tocar nada** cuando no es legal, porque *"un dron no puede
moverse porque la zona está llena"* es un resultado **normal** de una simulación,
no un error.

Conviene ser preciso aquí, porque es la pregunta que más se repite: `can_move`
es la pregunta **estructural** (existe conexión, hay hueco en el enlace, cabe en
la zona *ahora*). La regla completa del turno, que incluye las reservas del
mismo turno y el caso de `restricted`, está en `Simulation.can_start_move` (ver
E6). Las dos existen porque responden a preguntas distintas.

### B6. ¿Por qué `neighbors()` filtra `BLOCKED` pero no la capacidad?

Porque son dos clases de información distintas. `BLOCKED` es **topología**: esa
zona no existe para el routing, siempre. La capacidad es **estado**: cambia cada
turno según quién esté dentro. Si `neighbors()` mirara la ocupación,
`shortest_path` dejaría de ser una **función pura** (mismo grafo + mismo `start` +
mismo `end` → siempre la misma ruta) y su resultado dependería de dónde
estuvieran los drones. Y una función pura se puede **cachear**, que es lo que
hace `PathFinder.shortest_path`.

### B7. ¿Qué es `_adjacency` y por qué existe si ya tengo `connections`?

`_adjacency: dict[str, list[Zone]]` es un **índice derivado**: por cada zona, la
lista de sus vecinas. Se construye una vez en `Graph.__init__` con **dos**
`append` por conexión, porque las conexiones son bidireccionales. Sin él,
`neighbors()` tendría que recorrer `self.connections` entero: `O(E)`, y como
Dijkstra la llama una vez por nodo, el algoritmo entero sería `O(V·E)`. Con el
índice, `O(grado)`, y el total cae a `O((V+E) log V)`.

Los números del challenger lo justifican solos: 54 zonas y 70 conexiones. Una
matriz densa `54 × 54` reservaría 2916 posiciones para guardar 70 aristas — 42
veces más memoria — y además seguiría estando mal en cuanto se añadiera una
zona. El índice guarda exactamente lo que existe.

Y es **derivado, no fuente de verdad**: `self.connections` sigue siendo la lista
canónica, y `_adjacency` no se muta después de construirse. Por eso el guion
bajo en el nombre: es una implementación interna.

### B8. ¿Por qué `Zone.max_drones` es `int | None` y `Connection.max_link_capacity` es `int`?

Porque los dos `None` significarían cosas distintas, y solo una es real.
`Zone.max_drones = None` significa **sin límite**, y ocurre exactamente en dos
casos: `start` y `end` (§VII.2, A7). `Connection.max_link_capacity` **jamás** es
`None`, porque §VI fija default `1` y siempre hay valor. Mantener `int | None`
ahí era una unión imposible que además obligaba a `have_capacity()` a tener una
rama muerta. Regla general: **un tipo opcional debe reflejar una ausencia que de
verdad pueda ocurrir.**

### B9. ¿Por qué las claves del grafo son `str` y no `Zone`?

Por cuatro razones, todas prácticas. (1) El nombre es **único** —lo garantiza el
parser—, así que identifica sin ambigüedad. (2) Es **legible en un traceback**: ves
`'waypoint1'`, no `<fly.src.models.Zone object at 0x7f…>`. (3) Es **ordenable**:
dos `str` siempre se comparan, y eso da **desempates deterministas** en el heap
(`heapq` necesita la tupla completa ordenable). (4) Evita depender de la
identidad de un objeto mutable como clave de diccionario.

El coste: los dos desdoblamientos extra (`[self.position.name]` en el
pathfinding). Asumido, y es el intercambio correcto.

### B10. ¿Por qué `find_connection` es `O(E)`? ¿No es lento?

Sí lo es: recorre `self.connections` comparando extremos. Pero se puede
defender con números. En el challenger son 70 conexiones, y `decide` la llama una
vez por dron activo y turno: 25 × 70 = 1750 comparaciones por turno, unas 75 000
en los 43 turnos de la partida. Frente a un Dijkstra por dron, que serían 25 ×
`O((V+E) log V)`, es ruido.

Lo que sí es cierto es que se puede bajar a `O(1)` guardando un
`dict[(str, str), Connection]` en `Graph.__init__`, igual que ya se hizo con
`_adjacency`. Está medido, no supuesto: la diferencia en tiempo de ejecución es
nula porque el cuello de botella del programa no está ahí.

### B11. ¿Por qué `Graph.find_connection` compara con `==` y no con `is`?

Porque `Zone` **no define `__eq__`**, así que Python usa la identidad por
defecto: `a == b` es `a is b`. Funciona porque el parser garantiza que solo hay
un objeto `Zone` por nombre — y es exactamente la propiedad de *"referencias a
objetos de verdad, no a nombres"* que hace que el grafo no pueda apuntar a una
zona inexistente.

### B12. ¿Por qué el tránsito es un campo `transit` aparte y no se ensancha `position`?

Porque ensanchar `position` a `Zone | Connection` **rompería el invariante de
B1**. Tal como está, la afirmación es:

> Un dron está en `zone.drones` **si y solo si** `drone.position is zona`.

Con `position: Zone | Connection` habría que redefinirla a "si `position` es una
`Zone`, el dron está en `position.drones`; si es una `Connection`, está en
`connection.drones` y en ninguna zona" — es decir, la invariante original pasa a
tener una excepción que hay que documentar en un docstring para que el revisor la
encuentre. Con `transit` aparte, la invariante se queda **intacta** y sin
excepciones: `position` siempre es una zona, y `transit` es el dato adicional que
solo tiene sentido mientras se vuela.

### B13. ¿Por qué `Connection.label` es una `@property` y no un método?

Porque no es un dato, es un **valor derivado** de `a.name` y `b.name`. Con un
método habría que escribir `conn.label()` en cada uso, y eso comunica "esto es una
operación" cuando en realidad es "esto es cómo se llama esta conexión". Con
`@property` se lee `conn.label`, que es **exactamente la misma sintaxis** que
`Zone.name`, y el formato de §VII.5 (`D<ID>-<connection>`) se aplica igual a las
dos cosas.

Además `@property` de solo lectura hace que el nombre no se pueda reasignar y
romper a medias. Y no duplica estado: `a` y `b` siguen siendo la fuente de verdad,
así que el valor se recalcula en cada acceso. El coste es cero en la práctica, y
lo que compra es que el nombre no exista en dos sitios.

### B14. ¿Qué pasa si se llama a `zone_cost()` sobre una zona `BLOCKED`?

Lanza `ValueError`, y es intencionado. `zone_cost()` mira `ZONE_COSTS`, que solo
tiene `NORMAL`, `PRIORITY` y `RESTRICTED`: una zona bloqueada no tiene coste
porque **no tiene coste que pagar**. Convertir ese `KeyError` en un `ValueError`
con el nombre de la zona es la diferencia entre un fallo que dice algo y un
traceback interno.

---

# Bloque C — El pathfinding

### C1. ¿Por qué Dijkstra y no BFS?

Porque BFS cuenta **saltos**, y aquí no todos los saltos cuestan lo mismo: entrar
en una zona `restricted` cuesta 2 turnos. En un mini-mapa `start ─r→ goal` y
`start ─b→ goal` hay dos rutas de 2 saltos, pero cuestan 3 y 2 turnos
respectivamente: BFS no puede distinguirlas y devolvería la que saliera primero,
no la más barata. Dijkstra ordena por **coste acumulado**, no por número de
saltos.

### C2. ¿Por qué el coste va en el **nodo de destino**, no en la arista?

Porque §VII.3 lo define así: *"cost in turns, based on the zone type of the
**destination**"*. Equivale a decir que el coste de la arista `u → v` es
`zone_cost(v)`. Dos consecuencias que se ven en el código:

- El bucle de `_dijkstra` suma `self._step_cost(neighbor)`, **nunca** el coste de
  la zona actual.
- `start` **nunca** suma coste, porque es el origen y a ella no se "entra". Si el
  coste fuera de la zona actual, el primer paso ya pagaría de más.

Y una zona `restricted` cuesta 2 **sea por el lado que entres**: el coste
depende del destino, no del sentido.

### C3. ¿Qué es la `heap` y por qué `heapq`?

La `heap` es la **frontera**: las zonas descubiertas pero todavía sin procesar,
ordenadas siempre por la más barata. `heapq` mantiene una `list` de Python
organizada internamente como *min-heap*: sigue siendo una `list`, pero con un
orden que **solo se mantiene si la tocas a través de las funciones del módulo**.
Si haces `heap.append(x)` a mano, el invariante interno se rompe.

Por qué importa: sin heap, obtener el mínimo exige recorrer la lista entera →
`O(V²)`. Con heap es `O(log V)`. Es la diferencia entre `O(V²)` y
`O((V+E) log V)`.

De las 8 funciones de `heapq` solo se usan **dos**: `heappush` y `heappop`.

### C4. ¿Qué es *lazy deletion*?

Cuando mejoras la distancia de una zona que **ya estaba encolada**, `heapq` no
permite borrar la entrada vieja: se inserta la nueva y la vieja se queda dentro.
Al extraerla, el `if name in visited: continue` de `_dijkstra` la descarta. Es
*eliminación perezosa* y es lo que mantiene la complejidad en `O((V+E) log V)`.
La alternativa —borrar de en medio— costaría `O(V)` por operación.

### C5. ¿Por qué el desempate es `(turnos, preferencia)` y no subir el coste de `normal`?

Porque son dos cosas distintas. `priority` cuesta lo mismo que `normal` en
turnos (§VI: *"Movement to this zone costs 1 turn **but should be
prioritized**"*). Si subieras el coste de `normal` a 2 para forzar que `priority`
ganara, cambiarías el **resultado** del pathfinding, no solo su orden: rutas
con distinto número de saltos empezarían a elegir de otra manera, y el algoritmo
ya no estaría minimizando turnos, que es lo que §VII.6 mide.

La solución es un **coste par**: `(turnos, preferencia)`, comparado
lexicográficamente en `_step_cost`:

| Tipo | Coste |
|---|---|
| `NORMAL` | `(1, 0)` |
| `PRIORITY` | `(1, −1)` |
| `RESTRICTED` | `(2, 0)` |

Y el invariante crítico: **`priority` nunca alarga una ruta**, porque `(4, 0)`
gana siempre a `(5, −3)`. El `−1` no es un coste real, es un **descuento** que
solo actúa cuando dos rutas empatan en turnos.

### C6. ¿Por qué `priority` es un −1 en el pathfinding y no una regla de `models.py`?

Porque el **mundo** no sabe qué es "preferido": una zona `priority` no es más
cara ni más rápida que una `normal`. La preferencia es una decisión **del
algoritmo**, no del dominio. Por eso vive en `PathFinder._step_cost`, no en
`Zone`. Y por eso no se duplica en `Simulation`: una regla, un sitio.

Verificado en `medium/03_priority_puzzle`: la ruta que devuelve el pathfinding
pasa por `fast_junction` y `fast_path`, las dos únicas zonas `priority` del mapa,
cuando existen dos caminos con el mismo número de turnos.

### C7. ¿Por qué se para al **cerrar** `end`, no al descubrirlo?

Porque cuando se extrae `end` de la frontera, su distancia es **definitiva**:
ningún otro camino puede llegar más barato. En el momento de descubrirlo su
distancia es solo provisional y podría mejorarse. El `break` de `_dijkstra` está
justo después de `visited.add(name)`, no antes, por eso `end` sale **cerrado**.
Parar antes ahorra trabajo real.

### C8. ¿Por qué `prev` va hacia atrás?

Porque un nodo puede tener muchas salidas y solo un predecessor. `prev[b] =
start` y `prev[c] = start` conviven sin conflicto; un `next[start]` **no** podría
apuntar a dos sitios a la vez. Así que la reconstrucción va de `end` hacia atrás
con `prev` en `_build_route`, y luego se invierte con `append` + `reverse`.

Y ese `append` + `reverse` es `O(n)`. Insertar al principio
(`route.insert(0, zona)`) sería `O(n²)` porque Python lista mueve todos los
elementos en cada inserción.

### C9. ¿Por qué `shortest_path` devuelve una **copia**?

Porque devuelve `list(route)` y no `route`. La lista vive en `self._cache`; si
devolviera la referencia, el llamante podría hacer `route.pop(0)` —que es justo
lo que hace un consumidor de rutas para avanzar por ella— y **mutilaría la
caché**: la siguiente consulta devolvería una ruta ya cortada. Verificado: dos
llamadas seguidas devuelven objetos distintos.

El coste es `O(longitud de la ruta)`, y se paga a cambio de que la caché sea
intocable.

### C10. ¿Por qué se cachea también el `None` (el fallo)?

Porque **"no hay camino" cuesta lo mismo de calcular que cualquier otra
respuesta**, y la simulación va a preguntar exactamente lo mismo para cada dron
(25 veces en el challenger). Cachear el fallo es tan gratis como cachear el
éxito y evita 25 búsquedas idénticas.

### C11. ¿Por qué una **clase** y no una función libre?

La razón sólida **no** es el OOP de fachada, es que la clase tiene **estado
real**: `self.graph` y `self._cache`. Eso responde con código a la pregunta de
§VII.1 *"¿estás recalculando o cacheando rutas?"* — la caché es un atributo
visible, no un diccionario global. Una función libre que recibe `graph` como
primer parámetro y no recuerda nada, sería fachada de verdad.

### C12. ¿Por qué el heap guarda `(coste, nombre)` y no `(coste, zona)`?

Porque `heapq` compara **tuplas**, elemento a elemento. Si el segundo elemento
fuera un objeto `Zone`, al desempatar intentaría comparar dos `Zone` y `Zone` no
define `__lt__` → `TypeError`. Con `str` siempre se puede comparar, y de regalo
el desempate es **alfabético y por tanto determinista**: mismos resultados en
cada ejecución.

⚠️ **Y el bug traicionero**: comparar dos enteros que son iguales **no** lanza
error. Ese bug **solo salta con 3 o más entradas en el heap**. Los mapas
pequeños pasan y revienta en el laberinto grande. Es la clase de fallo que
aparece el día de la revisión y no en los tests.

### C13. ¿Qué complejidad tiene y cómo la defiendo?

| | Coste |
|---|---|
| **Tiempo** | `O((V + E) · log V)` |
| **Memoria** | `O(V + E)` |

Desglose: `V log V` por insertar y extraer cada zona de la frontera; `E log V`
por revisar cada conexión y actualizar. La memoria es **lineal, no cuadrática**:
nunca se crea una tabla de "todas las zonas contra todas", solo la adyacencia
(`≈ 2E` referencias frente a `V²` celdas de una matriz — 140 frente a 2916 en el
challenger).

Y depende de una cosa: que `graph.neighbors()` sea `O(grado)`. Eso es lo que
justifica `_adjacency` (B7).

### C14. ¿Qué **no** hace `shortest_path`?

No mira ocupación, no mira turnos, no sabe cuántas veces se llamará, no conoce
la lista de drones. Es el **GPS**: dice por dónde. Los semáforos (cuándo puede
mover cada uno) son de `simulation.py`. Esa separación es lo que permite
cachearlo y testearlo por separado.

Lo único que hace y no sea un `shortest_path` puro es aceptar un conjunto de
aristas `forbidden`, que se usa solo desde `alternative_routes` para forzar rutas
alternativas. La ruta devuelta depende solo del grafo y de `forbidden`, nunca de
quién esté volando.

### C15. ¿Por qué un dron sin ruta devuelve `None` y no lanza excepción?

Por el criterio del proyecto: **excepción para lo que no debería pasar, valor de
retorno para lo que puede pasar con normalidad**. La ausencia de ruta entre dos
zonas es un **resultado válido** del algoritmo —en un mapa con un componente
aislado es legal—, no un error. Además `None` es inequívoco: lista vacía sería
una ruta mala, `None` es "no hay".

### C16. ¿Y qué hace `Simulation` con un dron sin ruta?

No le hace nada, porque la situación no llega a existir: `Simulation.__init__`
llama a `alternative_routes` **antes** de crear ningún dron, y si no devuelve
ninguna ruta lanza `SimulationError`, que `main` imprime como `error:` y devuelve
con código `1`. Se decide antes de jugar el primer turno porque empezar una
partida que se sabe imposible solo gasta turnos; para este proyecto, abortar con un
mensaje claro es más defendible que simular para siempre.

### C17. ¿Cómo se obtienen rutas alternativas sin escribir un k-shortest-paths?

Con un truco de forallar aristas. `alternative_routes` empieza por la ruta
óptima y luego, en hasta `MAX_ROUNDS` rondas, **prohíbe una arista cada vez** y
vuelve a lanzar `_dijkstra`. Al quitar `a-b` la búsqueda tiene que hallar otra
manera de pasar, y así salen rutas nuevas — sin bucles, porque ninguna arista se
prohíbe dos veces — sin implementar un algoritmo de k caminos, que es bastante
más código y bastante más difícil de defender.

Dos acotaciones que hacen que no se dispare: solo se intenta con rutas ya
descubiertas, y `MAX_CANDIDATES = 12` corta el bucle cuando se han encontrado
suficientes. Al final el conjunto se pasa por `alternative_routes` para quedarse
**solo con las más baratas** (ver C18).

### C18. ¿Por qué se descartan las rutas alternativas más largas?

Porque **repartir la flota entre rutas más largas no reparte: alarga el viaje**.
Si dos rutas cuestan 20 y 22 turnos, mandar la mitad de los drones por la de 22 no
acorta nada y les añade 2 turnos a esa mitad. La función se queda solo con las
rutas cuyo `_turn_cost` iguala al mínimo, de modo que el reparto nunca empeora el
makespan de nadie.

Verificado en los diez mapas oficiales: **todas** las rutas que devuelve
`alternative_routes` tienen el mismo coste. Nunca se reparte entre rutas de
distinto precio.

### C19. ¿Cuántas rutas alternativas hay en la práctica?

Menos de las que se imagina. Medido con `alternative_routes` sobre los diez mapas
oficiales:

| Mapa | Rutas de coste mínimo | Turnos |
|---|---|---|
| `easy/01_linear_path` | 1 | 4 |
| `easy/02_simple_fork` | **2** | 4 |
| `easy/03_basic_capacity` | 1 | 4 |
| `medium/01_dead_end_trap` | 1 | 8 |
| `medium/02_circular_loop` | 1 | 15 |
| `medium/03_priority_puzzle` | 1 | 8 |
| `hard/01_maze_nightmare` | **2** | 13 |
| `hard/02_capacity_hell` | 1 | 16 |
| `hard/03_ultimate_challenge` | 1 | 26 |
| `challenger/01_the_impossible_dream` | **2** | 43 |

Solo tres de los diez mapas tienen más de una ruta posible, y los otros siete se
resuelven con una. Eso explica por qué el reparto no mejora todo: en siete mapas
**no hay nada que repartir**, y el makespan lo marca el cuello de botella, no la
longitud del camino (ver D15).

### C20. ¿Por qué `edge_key` ordena el par de nombres?

Porque un enlace se puede recorrer en los dos sentidos y la clave tiene que ser
la misma en ambos. `edge_key` devuelve `(a.name, b.name)` o `(b.name, a.name)`,
la que sea menor alfabéticamente. Y el parser ya impide que un nombre de zona
lleve guion, así que el par de nombres identifica el enlace sin necesitar la
conexión.

Esa misma normalización es la que usa `parse_connection_line` para detectar
conexiones duplicadas (A4): una idea, dos sitios, y por eso no pueden
desincronizarse.

---

# Bloque D — Teoría, OOP, herramientas y visualización

### D1. ¿Qué es la complejidad y por qué hay que defenderla?

Es cuánto crece el trabajo cuando crece la entrada. `O(n)` es lineal (doblar
entrada, doblar trabajo), `O(n²)` es cuadrático (doblar entrada, cuadruplicar),
`O(log n)` es logarítmico (casi no crece).

Se defiende por **dos** razones. Una es práctica: saber si el algoritmo aguanta
25 drones y 54 zonas. La otra es **la que importa aquí**: §V prohíbe
`networkx`, y la justificación que se sostiene en el peer review es *"mi
algoritmo es `O((V+E) log V)` porque…"*. Si no sabes la complejidad, no tienes
respuesta, y entonces la prohibición parece burocracia en vez de un ejercicio.

### D2. ¿Por qué están prohibidas `networkx` y `graphlib`?

Porque el objetivo del ejercicio es **implementar el algoritmo**, no llamarlo.
`networkx.shortest_path()` te lo resuelve, y entonces ya no puedes defender cuál
es la complejidad de tu pathfinding ni por qué Dijkstra. El enunciado lo dice sin
ambigüedad (§V) y la guía lo concreta: `heapq` **sí** vale, porque es librería
estándar y es una estructura de datos, no el algoritmo.

### D3. ¿Qué es "OOP de fachada" y por qué es un anti-patrón?

Es tener clases que son **solo contenedores con nombre**, sin comportamiento
propio, cuyos atributos se mutan libremente desde fuera. La revisión de este
proyecto lo trata como motivo de suspenso, y es fácil ver por qué: una clase así
no protege nada.

El ejemplo canónico es `zone.drones.append(...)`: si el dron se mete en la zona
llamando a una lista desde fuera, nadie pasa por `can_accept_drone()`, la
capacidad no se aplica, y **el fallo es silencioso**. La señal de OOP sana es lo
contrario: exponer el **comportamiento del dominio** (`zone.can_accept_drone()`,
`connection.have_capacity()`, `drone.attach()`) y dejar los atributos privados
detrás.

### D4. ¿Qué es "tell, don't ask"?

Es pedirle al objeto que **haga** algo, en vez de atravesarlo para preguntarle sus
datos y operar sobre ellos desde fuera.

```python
# ask: el grafo manipula la zona del dron por detrás
drone.position.remove_drone(drone)
drone.position = target

# tell: el dron mantiene coherente su propio estado
drone.attach(target)
```

No es purismo. La versión `tell` es la que hace imposible el bug: no hay forma de
cambiar `position` sin que el dron pase por `add_drone`, que es la puerta que
aplica la capacidad.

### D5. ¿Qué es la **cohesión** y por qué un fichero = una responsabilidad?

Cohesión = "cada clase (o módulo) tiene una sola razón de existir". El criterio
práctico: si el nombre del fichero no lo describe, está mal partido. `parser/io.py`
solo lee ficheros, `parser/metadata.py` solo parte líneas, `validators.py` solo
valida valores sueltos, `models.py` solo define el dominio, y `visualization.py`
solo presenta.

Es lo que hace mantenible un `main.py` de 800 líneas con todo mezclado — que es
exactamente lo contrario de lo que el proyecto quiere. Y es lo que permite cambiar
cómo se guarda la adyacencia **sin tocar** `pathfinding.py`: bajo acoplamiento.

### D6. ¿Qué es la tipificación estática y qué gana exactamente?

Escribir el tipo **antes** de ejecutarlo. En la práctica, para este proyecto:

| Ganancia | Ejemplo concreto |
|---|---|
| Los errores aparecen **antes** de ejecutar | `dist` como `dict[str, Cost]` y luego `dist[zone]` — mypy lo dice al escribir |
| Las anotaciones **documentan** | `-> Connection \| None` te dice que puede no haber conexión |
| Obliga a decidir los casos borde | `-> None` te obliga a poner `return` en cada rama |

Y sobre todo: mypy es **un tercer tipo de test**, distinto del que ves cuando
ejecutas y del que escribes. Cobertura distinta ⇒ bugs distintos que aparecen.

⚠️ El riesgo real: descubrir 40 errores de tipado el último día. `make
lint-strict` es un seguro.

### D7. ¿Por qué hay `lint` y `lint-strict`?

Dos niveles de rigor. `make lint` es el **obligatorio** (§III.2 fija los flags
exactos): `flake8` + `mypy` con `--warn-return-any --warn-unused-ignores
--ignore-missing-imports --disallow-untyped-defs --check-untyped-defs`.
`make lint-strict` añade `--strict`: más comprobaciones, no más obligatorias.

El nivel obligatorio es el que corre el evaluador. El estricto es para mí mismo,
y conviene pasarlo pronto y a menudo.

### D8. ¿Por qué "una excepción no capturada = no funcional"?

Porque durante la revisión, un traceback significa que el revisor no puede
evaluar nada: el programa se cayó. La regla práctica del proyecto:

| Situación | Señal correcta | Por qué |
|---|---|---|
| Mapa inválido o ilegible | `MapParseError` → `stderr` + exit ≠ 0 | Error del **usuario** |
| Dron que no puede moverse | `move_drone` → `False`, `Intent("wait")` | **Normal** en una simulación |
| No hay ruta | `shortest_path` → `None` | **Resultado válido** |
| Se rompe un invariante | `ValueError` | **Bug del programador** |

La regla: **excepción para lo que no debería pasar; valor de retorno para lo que
puede pasar con normalidad.**

`UnicodeDecodeError` y `OSError` (fichero que no existe) están capturados en
`main` y salen como `error:` con código `1`, no como traceback.

### D9. ¿Por qué un entorno virtual y no el Python del sistema?

Por **reproducibilidad**. El enunciado §III.3 lo recomienda y §III.1 lo convierte
en regla: `make install` tiene que funcionar en una máquina limpia, que es la del
revisor. Sin venv, la versión de `flake8` o de `mypy` de tu máquina se cuela en el
resultado.

Y con la misma lógica: **dependencias mínimas**. El parser, el pathfinding, la
simulación y la visualización son **solo librería estándar, a propósito**. Menos
dependencias = menos superficie de fallo = menos cosas que pueden romperse el día
de la revisión.

### D10. ¿Por qué un `Makefile` y no un script?

Porque `make` **declara** comandos en vez de ejecutarlos, y la declaración es
reproducible y documentable a la vez. `make help` es documentación que no puede
quedarse obsoleta, porque la genera del propio fichero. Además separa el *qué*
(qué tarea hay) del *cómo* (qué intérprete exacto la ejecuta) — que es justo el
problema de "works on my machine".

`$(ARGS)` existe por un motivo concreto: **la revisión se hace en la máquina de
otro**, así que el comando tiene que poder recibir el fichero por parámetro.
Y `clean` no toca `venv/` a propósito (los `find` usan `-name venv -prune`):
limpiar cachés no debería destruir tu entorno.

### D11. ¿Qué es PEP 257 y por qué importan los docstrings?

Es la convención de docstrings de Python: qué se documenta, en qué orden
(purpose → params → returns) y cómo se formatea. §III.1 lo exige, y no es
decoración: **los docstrings son lo que el peer review lee** para entender por
qué el código es así sin tener que ejecutarlo.

Un docstring que explica el *porqué* vale mucho más que uno que repite el nombre.
`Drone.move_to` tiene uno que explica el orden de las operaciones y por qué el
atajo no debe usarse en la simulación; `Simulation.can_start_move` tiene uno que
explica por qué mira también el turno siguiente. Eso se defiende solo.

### D12. ¿Por qué enumerados (`ZoneType`) y no cadenas sueltas?

Porque un `Enum` es un **vocabulario cerrado**: el conjunto de valores válidos
está definido en un sitio, y `parse_zone_type` valida el string contra `zone.value`
en vez de contra una lista suelta en un `if`. El resto del código compara
`zone_type is ZoneType.BLOCKED` — y `is` con enumerados es comparación por
identidad: no puede haber dos `BLOCKED` distintos, así que no hay forma de
equivocarse al comparar.

Y un bug de typo (`"restrcted"`) es imposible: el nombre no existe, y el error que
sale lista los valores válidos.

### D13. ¿Qué es una **función pura** y por qué importa aquí?

Una función pura da el mismo resultado para la misma entrada, **sin depender de
estado externo**. `PathFinder.shortest_path` es pura: el mismo grafo y los mismos
extremos dan siempre la misma ruta, esté quien esté donde esté.

Dos beneficios concretos: se puede **cachear** (misma entrada, misma salida, no
hay que recalcular) y se puede **testear en solitario** (no hace falta montar una
simulación). Por eso `neighbors()` filtra `BLOCKED` y nunca la ocupación (B6) —
meter estado dentro rompería las dos cosas.

### D14. ¿Qué es un ciclo en un grafo y por qué Dijkstra no se cuelga?

Un ciclo es un camino que vuelve a un nodo ya visitado. Dijkstra no se cuelga
porque cada nodo se **cierra una sola vez** (`visited`), así que el ciclo se
rompe solo: al intentar relajar un nodo ya cerrado, la comprobación
`if neighbor.name in visited: continue` lo descarta. Los mapas oficiales lo
tienen a propósito —`medium/02_circular_loop` cierra un anillo, y `hard/01` tiene
ciclos— **para comprobar exactamente eso**.

### D15. ¿Qué es un **cuello de botella** y por qué marca los turnos?

Es un punto por el que **todos** los drones tienen que pasar. Con
`max_drones=1` o `max_link_capacity=1` (los defaults de §VI), un cuello de
botella **serializa** la flota: aunque la ruta sea de 1 salto, 12 drones tardan
12 turnos en pasar.

Por eso `hard/02_capacity_hell` tiene compuertas en serie de capacidad 1: **los
turnos los marca el cuello de botella, no la longitud del camino.** Y explica por
qué el reparto de rutas (E2) mueve la aguja en unos mapas y en otros no: si solo
hay una ruta posible, no hay nada que repartir (C19).

### D16. ¿Qué es el **makespan**?

El número de turnos hasta que llega el **último** dron. Es la métrica principal
(§VII.6: *"the fewer the number of turns, the better"*). La consecuencia
importante: no sirve con que *la mayoría* llegue rápido; sirve con que **uno solo**
no se atasque. Por eso los deadlocks y las zonas trampa (`medium/01_dead_end_trap`
tiene una rama muerta sin salida) son tan relevantes.

Medido en los diez mapas: 4, 4, 4, 8, 15, 8, 13, 16, 26 y 43 turnos, cumpliendo
todos los targets y batiendo el récord de 45 del challenger.

### D17. ¿Qué es un **deadlock**?

Un ciclo de esperas: A quiere el sitio de B, B quiere el de A, y ninguno se
mueve. §VII.1 lo nombra explícitamente (*"avoidance of path conflicts and
deadlocks"*).

El caso de este proyecto es el **atasco permanente**: todos los drones esperan en
una zona que no se vacía porque quien la ocupa está esperando en la siguiente. El
antídoto es doble: (1) decidir bien a quién se le concede la plaza cuando hay más
demanda que oferta (§VII.1, reparto de rutas, E2), y (2) un **tope de seguridad**
en el bucle de turnos (E13) que detecte "este turno no se movió nadie" y salva con
un error en vez de colgarse.

### D18. ¿Qué es un turno en **dos fases** y por qué es obligatorio?

Fase 1: todos los drones **declaran** su intención (quiero ir a X). Fase 2: se
valida todo contra el estado **después** de aplicar las salidas, y se aplica todo
a la vez.

Es obligatorio por §VII.3 (*"a zone must have available capacity for a drone to
move into it, **after all drones moving out have freed up space**"*) y porque la
alternativa no es determinista. La prueba, ejecutada sobre un mapa con `w` y `x`
de `max_drones=1` y dos drones:

```
turno 1:  D1-w
turno 2:  D1-x D2-w        ← el dron D1 sale de w y el dron D2 entra en w
                                       en el MISMO turno
turno 3:  D1-e D2-x
turno 4:  D2-e
```

Ese intercambio es legal **precisamente** porque el turno tiene dos fases. Con
resolución dron a dron, el mismo turno daría `[True, True]` o `[False, True]`
dependiendo del orden de iteración, y un resultado que depende del orden no es
una simulación: es una moneda al aire. La implementación está en E5.

### D19. ¿Por qué `Connection.drones` existe si nadie lo puebla?

Porque la idea inicial era que la lista *fuera* la contabilidad, y al final la
comptabilidad vive en otro sitio. **Verificado: `Connection.drones` está siempre
vacía** —0 elementos en cualquier punto de cualquier partida oficial—, así que
`have_capacity()` con su `reserved=0` por defecto devuelve siempre `True`. Quien
realmente aplica la capacidad del enlace es la tabla de reservas de `Simulation`
(E7).

ElAPI sigue siendo coherente: `add_drone`, `remove_drone` y `have_capacity`
existen y funcionan, y `have_capacity(reserved=...)` está diseñado justo para
sumar las reservas. Lo que no hay es una llamada a `Connection.add_drone` desde la
simulación, porque una conexión no "guarda" al dron: lo que cuenta es si ese dron
tiene committing el enlace para ese turno, y eso es un dato del turno, no de la
conexión.

### D20. ¿Por qué la representación visual es obligatoria y no extra?

§VII.1 lo dice dos veces: *"**must** provide visual feedback"*, y §X lo lista
entre los entregables. §IX dice que el bonus *"solo se revisa si se cumplen los
obligatorios"*.

Y hay un dato que la convierte en algo más que un añadido: **`color` aparece en
el 100 % de las 150 zonas de los diez mapas oficiales**, que son 150 de 150. O
sea, la visualización no es un extra: los datos para ella ya están en los
ficheros de prueba, y el parser los conserva en `Zone.color`.

Restricción a respetar: §VI dice que `color` es *"any valid single-word string"* y
que **no hay lista fija de colores**. Los mapas usan `rainbow`, que no está en
ninguna paleta. Una lista blanca **rechazaría mapas válidos**.

### D21. ¿Por qué no usar A\*?

Porque necesita una **heurística admisible** (que nunca sobrestime el coste
restante). Aquí las coordenadas `x, y` **no están ligadas al coste**: dos zonas
cercanas en el plano pueden estar conectadas por un enlace de 1 turno, y una
distancia euclídea sobrestimaría. Sin heurística segura, A\* puede devolver rutas
no óptimas — es decir, peor que Dijkstra Y más difícil de defender.

### D22. ¿Por qué el modelo es una **lista de adyacencia** y no una matriz?

Porque los mapas son **dispersos**: casi ninguna pareja de zonas está conectada. En
el challenger hay 54 zonas y 70 conexiones, así que una matriz `54 × 54` se
llenaría de ceros: 2916 celdas para guardar 70 aristas. La lista guarda solo lo
que existe, y responde "vecinos de X" en `O(grado)` en vez de `O(V)`.

### D23. ¿Por qué se usa `crc32` y no `hash()` para los colores desconocidos?

Porque `hash()` de un `str` **cambia en cada proceso**: está saltado por
`PYTHONHASHSEED`. Si el fallback del color usara `hash()`, el mismo mapa daría
colores distintos en cada ejecución, y la salida dejaría de ser reproducible —
justo lo contrario de lo que pide un formato que se compara con `diff`.

`zlib.crc32` es determinista entre procesos y entre máquinas, y con
`FALLBACK_OFFSET + crc32(nombre) % FALLBACK_SPAN` reparte los nombres desconocidos
por los 216 colores del cubo. En los mapas oficiales el único nombre fuera de la
tabla es `rainbow`, que cae al fallback.

### D24. ¿Por qué los colores solo se emiten si tiene sentido?

Porque a `stderr` y a un fichero no le sirven, y estorban. `colors_enabled`
comprueba dos cosas:

| Comprobación | Por qué |
|---|---|
| `NO_COLOR` en el entorno | Es la convención de [no-color.org](https://no-color.org/) y **manda sobre cualquier otra cosa** |
| `sys.stdout.isatty()` | Al redirigir a un fichero, los códigos de escape se cuelan en el texto y rompen cualquier comparación línea a línea |

Verificado: al redirigir la salida, el texto sale limpio, sin un solo `\033`.

### D25. ¿Por qué `token_order` no ordena por nombre?

Porque ordenar por nombre pone `D10` antes que `D2`. `token_order` extrae el
**número** del dron del token y ordena por entero, así que la línea es legible y
estable. Y como los nombres de zona no pueden llevar guion (A5), el destino
empieza justo detrás del primer guion, lo que hace que `D1-Alfa-Beta` —el dron
cruzando el enlace Alfa-Beta— se ordene por el `1`, no por el texto.

Un token sin número reconocible no rompe la comparación: se va al final con una
clave grande, en vez de levantar `TypeError`.

### D26. ¿Por qué la salida son **eventos** y no un estado?

Porque §VII.5 lo dice: *"Drones that do not move in a given turn are omitted from
that line"*. El output es una lista de **sucesos**, no una foto. Un dron que
espera no aparece, y no hay forma de distinguir "esperando" de "todavía no ha
existido".

La consecuencia útil es que el formato es **compacto**: cada token es
exactamente un cambio de posición, y como el destino es lo que se escribe
(`D1-waypoint1`, nunca `start-D1`), no hace falta el origen ni guiones
extra. `format_turn` además colapsa tokens repetidos con `set()`, porque la
salida debe depender de los drones y no de cómo se recorrieran.

---

# Bloque E — La simulación

### E1. ¿Qué problema es exactamente el de la simulación?

**Scheduling**, no routing. El pathfinding responde a *por dónde*; la simulación
responde a *cuándo*. Y §VII.1 lo dice: drones que se mueven simultáneamente,
repartidos en varios caminos, esperando cuando toca, sin colisiones ni
deadlocks. Un GPS no sabe que otros coches van por la misma calle, y por eso la
ruta más corta de cada dron **no es** automáticamente la mejor para la flota.

### E2. ¿Por qué una ruta para todos no basta?

Porque **todos** los drones comparten los mismos cuellos de botella. Si los 25
drones delchallenger fueran por la misma ruta, cada compuerta de capacidad 1 los
serializa y el makespan es la suma de las esperas.

Medido: forzando que los 25 drones compartan la misma ruta, el challenger pasa de
**43 a 67 turnos**. Con el reparto round-robin de `Simulation.__init__`
(`routes[(i - 1) % len(routes)]`), 43.

Y conviene ser honesto con el matiz, porque el peer review lo pregunta: el reparto
solo ayuda si **hay más de una ruta posible**. Solo tres de los diez mapas
oficiales lo tienen (C19). En los otros siete `alternative_routes` devuelve una
sola ruta y el reparto no hace nada — y ahí los turnos los marca el cuello de
botella (D15), no la longitud del camino.

### E3. ¿Qué estado necesita un dron para simularse?

Cuatro cosas, repartidas en `Drone`:

| Atributo | Para qué |
|---|---|
| `position` | La zona en la que está. Siempre una `Zone`, nunca una conexión (B12) |
| `route` + `route_index` | Su ruta **propia** y por dónde va. `route[route_index]` es siempre su zona actual |
| `transit` | La conexión que está cruzando, o `None` |
| `transit_turns_left` | Cuánto le queda de vuelo |

Y hay una regla sobre `route_index` que conviene destacar: **solo avanza al
aterrizar**, nunca al empezar a cruzar una zona `restricted`. Por eso el invariante
de ruta es `route[route_index]` = zona actual y `route[route_index + 1]` = zona
que espera, y por eso `collect_intents` puede leer `route[route_index + 1]` para
saber dónde va a aterrizar un dron en tránsito sin adivinar nada.

Cada dron recibe su **propia copia** de la ruta: `Drone.__init__` hace
`list(route)`, así que dos drones con la misma ruta no comparten el objeto.

### E4. ¿Cuál es el bucle mental del turno?

`step()` hace exactamente cuatro cosas, en este orden:

1. **Avanza el reloj.** `self.turn += 1`, y `purge_reservations()` olvida las
   reservas de turnos ya jugados.
2. **Fase 1 — `collect_intents()`**: cada dron activo declara qué va a hacer. No
   se mueve nada.
3. **Fase 2 — `resolve()`**: se aplican las intenciones en cuatro pasos
   ordenados (E5) y se devuelven los tokens del turno.
4. **Detecta falta de progreso** (E13) y devuelve un `TurnResult`.

El reloj avanza **al principio** a propósito: así el turno que se decide, el turno
en el que se entrega y el turno que se informa son siempre el mismo número.

### E5. ¿Por qué `resolve()` tiene cuatro pasos y en ese orden?

Porque el orden es lo que hace legal un intercambio de plazas. En `resolve`:

| # | Paso | Qué consigue |
|---|---|---|
| 1 | Todos los que se mueven hacen `detach()` | Se **vacían** todas las zonas de salida |
| 2 | Los que venían en tránsito hacen `attach()` | Aterrizan con la plaza que ya se les había reservado |
| 3 | Los que empiezan a cruzar una `restricted` entran en `transit` | Ocupan el enlace e imprimen `D<ID>-<conexión>` |
| 4 | Los demás hacen `attach()` y avanzan `route_index` | Ya pueden entrar porque las zonas están vacías |

Vaciar antes de llenar es **la** regla de §VII.3, y es lo que permite que D1 salga
de `w` y el dron D2 entre en `w` en el mismo turno con `max_drones=1` (D18).

El paso 3 va antes del 4 por un motivo concreto: un dron que empieza a cruzar una
`restricted` **no** aterriza, pero sí necesita su hueco contado antes de que otro
intente aterrizar en la zona de la que sale. Y al final hay un quinto bucle, el de
entregas, que queda como **red de seguridad**: solo queda vivo cuando `start` y
`end` son la misma zona, caso en el que el dron nunca se mueve porque ya está en
su destino.

### E6. ¿Cuál es la regla completa para que un dron pueda moverse?

No es una sola pregunta, son cuatro, y `decide` las va descartando en orden:

| # | Pregunta | Si la respuesta es "no" |
|---|---|---|
| 1 | ¿Tiene siguiente paso en su ruta? | Se entrega |
| 2 | ¿Existe conexión entre origen y destino? | Espera |
| 3 | ¿Está libre la conexión **este turno**? | Espera |
| 4 | ¿Está libre la conexión **el turno siguiente**, si el destino es `restricted`? | Espera |
| 5 | ¿Cabe en el destino, contando lo ya comprometido? | Espera |

La cuarta es la que se olvida: cruzar una `restricted` ocupa el enlace **dos**
turnos, así que `can_start_move` mira `link_is_free` para `self.turn` y para
`self.turn + 1`. Reservar solo el turno actual dejaría que otro dron se colara en
el enlace durante el vuelo.

Cuando la respuesta es sí, `decide` **se compromete**: reserva el enlace para este
turno (y el siguiente si toca), y anota el zona de salida en `will_leave` y la de
llegada en `will_enter`. Ese es el mecanismo que hace que la decisión del dron
`D1` cambie lo que puede hacer el dron `D2` sin que nadie se haya movido todavía.

### E7. ¿Cómo se modela la capacidad de una conexión?

Con una **tabla de reservas por turno**: `link_reservations` es un
`dict[(turn, Connection), int]`, y `reserve_link` suma ahí en vez de tocar la lista
`drones` de la conexión.

Es la única forma de decir *"este dron ocupa el enlace ahora y también el turno
que viene"*, que es exactamente lo que pasa al cruzar una `restricted`. Con una
lista de drones presentes no se puede expresar: el dron está en el enlace pero
figura en ninguna zona.

`link_is_free(conn, turn)` es la consulta, y siempre suma lo reservado a la
capacidad real de la conexión:

```
have_capacity(reserved) = len(self.drones) + reserved < self.max_link_capacity
```

Como `Connection.drones` está siempre vacía (D19), en la práctica el término
`reserved` es el que decide. Y `purge_reservations` se queda con las entradas cuyo
turno es **mayor o igual** al actual: nunca toca las del turno en curso ni las del
siguiente, que son las que siguen en juego.

### E8. ¿Por qué las zonas no usan reservas y las conexiones sí?

Porque son dos preguntas distintas y la respuesta sale de los datos:

| Qué expresar | Mecanismo |
|---|---|
| "Este dron ocupa el enlace ahora **y el turno que viene**" | Tabla de reservas por turno (`link_reservations`) |
| "Esta zona tiene hueco **después** de que salgan los que se van" | Contadores del turno: `will_leave`, `will_enter`, `arriving` |

Para una zona basta con una aritmética, y es la que hace `zone_is_free`:

```
reserved = arriving + will_enter - will_leave
```

`arriving` son los drones que estaban en tránsito y aterrizan este turno — hay que
contarlos aparte porque **todavía no figuran en ninguna zona**, que es
justamente el problema de B12— y por eso `collect_intents` los recorre primero.
`will_leave` puede ser mayor que `will_enter`, y por eso `reserved` **puede ser
negativo**: quien pregunta no necesita saber los movimientos ya decididos por
otros drones, solo su efecto neto sobre la zona.

### E9. ¿Por qué las intenciones se recogen en orden `D1`, `D2`…?

Porque cuando hay más drones que plazas, alguien tiene que quedarse esperando, y
eso no puede depender del orden del `dict` ni de la identidad de los objetos.
`ordered_drones` y `ordered_intents` ordenan por `drone_num`, que extrae el
número del **nombre**.

Y `drone_num` no ordena por el nombre entero justamente por eso: `"D10" < "D2"`
como cadena. Un dron con un nombre no reconocible no rompe la comparación: se va
al final con `UNKNOWN_DRONE_ORDER`.

Verificado: dos ejecuciones seguidas del challenger producen exactamente la misma
secuencia de turnos.

### E10. ¿Por qué el dron en tránsito no consulta nada?

Porque su hueco **ya era suyo** desde el turno en que empezó a cruzar. Por eso
`decide` devuelve `Intent("arrive", drone)` sin mirar conexiones ni capacidades: si
volviera a preguntar, su propia reserva se contaría dos veces y se bloquearía a sí
mismo.

Y es coherente con §VII.3, que dice que el dron *"MUST reach its destination during
the next turn"* y *"cannot wait on the connection for an empty space"*. El hueco
en el destino se **consume al declarar** la intención, no al llegar. Por eso, en
el turno en que empieza a cruzar, `decide` ya mete su zona de destino en
`will_enter`, y `collect_intents` la mete también en `arriving` para el turno
siguiente: la plaza está comprometida durante los dos turnos.

### E11. ¿Por qué `Intent` es un dataclass y no un tupla o un bool?

Porque un turno tiene cuatro desenlaces y luego hay que distinguir quién hace
qué. `IntentKind` es un `Literal["arrive", "deliver", "wait", "move"]`, y `Intent`
guarda `kind`, `drone`, `to` y `conn`. Los dos últimos solo tienen sentido para
`kind="move"`.

Lo que aporta frente a un `bool` es que `resolve` puede **separar por tipo** con
`ordered_intents`, y de ahí sale el orden de los cuatro pasos de E5. Con un
`bool` no habría forma de saber si un dron que espera en tránsito tiene que
aterrizar o simplemente esperar. Y con `slots=True` es un objeto sin `__dict__`:
menos memoria y ningún atributo accidental.

### E12. ¿Por qué los drones entregados salen de la lista en el mismo turno?

Porque `resolve` hace `self.drones.remove(intent.drone)` en cuanto `attach` lo
deja en el `end_zone`. Si se hiciera al principio del turno siguiente, `step`
jugaría un turno entero sin nada que hacer solo para poder detectarlo — y ese turno
vacío sería el último que se contaría, una línea de más en la salida.

Eso vale para las dos formas de llegar: cuando el dron **camina** al `end_hub` y
también cuando aterriza **viniendo de un tránsito**. Las dos ramas de `resolve`
comprueban `dest is self.end_zone` y retiran el dron en el acto. Y funciona
igual si el propio `end_hub` es `restricted`: en ese caso el aterrizaje pasa por
la rama de tránsito, y esa rama también lo retira.

Consecuencia directa: el número de líneas impresas **es** el número de turnos, y
un dron entregado no puede volver a aparecer. Y como `is_finished` es
`not self.drones`, `step` devuelve `None` en cuanto se vacía la lista.

### E13. ¿Cómo se detecta el cuelgue?

Esperar es una acción legítima, así que un dron quieto **no es un error**. Pero un
bug del scheduler no puede convertirse en un bucle infinito, porque §III.1 trata
eso como no funcional.

`step` lleva un contador `turns_without_progress`: lo pone a cero si el turno
produjo algún token, y si no lo incrementa. Cuando supera
`MAX_TURNS_WITHOUT_PROGRESS = 2` —es decir, tres turnos consecutivos sin nada—
lanza `SimulationError`, que `main` imprime como `error:` y devuelve con código
`1`.

Un valor de 2 es deliberado: da margen para un pico de congestión legítimo y aun
así corta antes de que un reviewer se impaciente. Y si el tope estuviera en 10 000,
el mismo `O(T · D log D)` del bucle de turnos pasaría a ser un problema de
rendimiento.

### E14. ¿Por qué el scheduler es estático y no recalcula rutas?

Porque la ruta **no se recalcula nunca** y un dron que no cabe **espera**. Es un
intercambio consciente, y hay que defenderlo con datos: la estrategia
dinámica (ETA, cuello de botella, *lookahead*) es estrictamente más potente, pero
introduce recálculo, y con recálculo el resultado de un turno depende del orden en
que se procesan las decisiones — justo el determinismo que da valor a una
simulación.

Y la medición respalda la decisión: una vez repartida la flota entre rutas
alternativas, un scheduler estático con desempate determinista alcanzó los mismos
turnos que el routing iba a marcar. `Simulation.decide` lo dice en su docstring:
*"El scheduler es estático: la ruta no se recalcula nunca y un dron que no cabe
espera."*

### E15. ¿Por qué `Simulation` no imprime nada?

Porque el printing es **presentación**, y la presentación es de
`visualization.py`. La
separación es lo que hace que el motor se pueda probar sin capturar `stdout`: un
test puede llamar a `step()` en bucle y mirar los `tokens` que devuelve.

`TurnResult` lleva el número de turno y la lista de tokens, y es lo único que
cruza la frontera entre los dos módulos. El bucle de `main` es entonces trivial:
llamar a `step()`, pasar los tokens a `format_turn`, e imprimir si la línea no
está vacía.

### E16. ¿Por qué `main` no imprime una línea si el turno no tuvo eventos?

Porque `format_turn` devuelve `""` cuando no hay tokens, y `main` hace `if line:`.
Es coherente con D26: la salida es una lista de sucesos, así que un turno sin
sucesos no produce línea.

Ahora bien, en una simulación que termina bien **esto no debería ocurrir nunca**.
Si aparece una línea vacía, es el síntoma de que la detección de falta de progreso
(E13) no saltó antes, y por eso el contador existe.

### E17. ¿Qué pasa si el mapa tiene el `start_hub` bloqueado?

`Simulation.__init__` lo comprueba y lanza `SimulationError`, que `main` imprime
como `error:` y devuelve con código `1`. Antes de este guard, ese caso terminaba en
un `IndexError` desde lo más profundo del bucle: el mensaje no decía nada útil y
el revisor veía un traceback en vez de un error de configuración.

Es el mismo patrón que E16 pero por el motivo contrario: la simulación prefiere
**fallar con un mensaje claro** antes de empezar, y para este proyecto eso es más
defendible que dejar que el programa se caiga.