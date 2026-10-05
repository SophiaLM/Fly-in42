# 10. Scheduling: cuándo puede cada dron recorrer su camino

Este es el capítulo que decide el proyecto. Los capítulos 08 y 09 eran el marco:
estado, movimientos, capacidades. Este es el que tiene las **decisiones abiertas**, y
por eso todavía **no elige nada**: las presenta, las compara y te pregunta.

La regla de este capítulo, y del trabajo entero:

> **Nada de lo que está aquí es un requisito del subject.** El subject dice *qué* es
> legal; no dice *a quién* le toca moverse primero. Eso es nuestro, y hay que poder
> defenderlo.

---

## 1. El problema, sin mencionar ninguna solución

### 1.1 Pathfinding responde a una pregunta; scheduling a otra

| | Pathfinding | Scheduling |
|---|---|---|
| Pregunta | ¿Por qué zonas **puede** ir un dron? | ¿**Cuándo** puede ir por ellas? |
| Se responde con | Dijkstra (`pathfinding.py`) | El bucle de turnos (cap. 08 §4) |
| Mira | Topología y costes | Ocupación y orden |
| Es | Una **función pura**: mismo grafo → misma ruta | ** dependent del estado**: cambia cada turno |
| Se puede cachear | Sí (`PathFinder._cache`) | No: la respuesta caduca |

Metáfora que ya usaste en el proyecto (`sobre_mi_pryecto.md` §1): el routing es el
**GPS** y el scheduling son los **semáforos**. Un GPS te dice *"por aquí, son 400
metros"*. No sabe que hay cuatro coches delante del semáforo, ni que uno de ellos va a
tirar 30 segundos más. Por eso la ruta más corta de cada dron **no** es
automáticamente la mejor para la flota.

### 1.2 El mismo conjunto de caminos, dos turnos distintos

Esto no es una afirmación teórica: sale de uno de los mapas oficiales. Tomemos
`easy/02_simple_fork` tal cual está:

```
   start ───[cap 2]─── j (max_drones=2) ─── path_a (cap 1) ─── goal
                  │                                                 ▲
                  └───────── path_b (cap 1) ─────────────────────┘

   start-junction : max_link_capacity = 2
   resto de enlaces: max_link_capacity = 1  (el default de §VI)
   4 drones
```

El `PathFinder` calcula **una** ruta. La pregunta del scheduler es: **¿cuántos drones
mandamos por cada rama?** Y la respuesta cambia el resultado:

### Reparto A — los 4 por `path_a`

```
 turno 1:  D1→j   D2→j                        (j cabe 2, el enlace permite 2)
 turno 2:  D1→path_a   D2 espera   D3→j       (path_a llena; j se liberó una plaza)
 turno 3:  D1→goal     D3→path_a              (D2 espera, D4 espera: j llena)
 turno 4:  D3→goal     D4→j
 turno 5:  D4→path_a
 turno 6:  D4→goal     D2→path_a              (path_a se liberó este turno)
 turno 7:  D2→goal
                                        ────── makespan = 7
```

### Reparto B — 2 por `path_a`, 2 por `path_b`

```
 turno 1:  D1→j   D2→j
 turno 2:  D1→path_a   D2→path_b
 turno 3:  D1→goal   D2→goal   D3→j         (j se vació en el turno 2)
 turno 4:  D3→path_a   D4→j
 turno 5:  D3→goal   D4→path_b
 turno 6:  D4→goal
                                        ────── makespan = 6
```

**Mismo mapa, mismo algoritmo de routing, un turno de diferencia.** Y el objetivo de
§VII.7 para este mapa es ≤ 8, así que los dos "pasan"... pero en `hard/02` y
`hard/03` la diferencia se multiplica, porque ahí hay tres compuertas de capacidad 1
en serie.

### 1.3 El otro eje: el orden de evaluación

Y al revés: si el **reparto** ya está decidido, el **orden** en que se atienden los
drones dentro de un turno sigue importando. El caso mínimo, con dos drones y una zona
que ambos quieren:

```
   start ── j (max_drones=1) ── goal      2 drones, j es el cuello de botella

   Both quieren j en el turno 1.  Solo uno puede.

   Orden A: D1 primero            → D1→j, D2 espera      makespan 2
   Orden B: D2 primero            → D2→j, D1 espera      makespan 2
```

Aquí da igual. Pero basta con que **los dos drones no tengan la misma distancia
restante** para que deja de dar igual:

```
   S ── p ── q ── M (cap 1) ── G          D1 va por p-q-M   (le faltan 3)
   S ── M ── G                            D2 va por M        (le faltan 2)

   turno 1: D1 quiere M, D2 quiere M.
     Si gana D2  → D2 llega antes, D1 espera → makespan 4
     Si gana D1  → D1 llega antes, D2 espera → makespan 4
   (aquí da igual porque la diferencia es 1)

   S ── p1 ── p2 ── p3 ── M (cap 1) ── G   D1 le faltan 4
   S ── p2 ── p3 ── M ── G                 D2 le faltan 3

   turno 1: los dos están en start; los dos quieren M... o no.
   Ahora sí: si D2 (el más corto) pierde la plaza, espera un turno de más
   del necesario, y ese turno lo paga el makespan.
```

**La conclusión que hay que dejar clara para defenderse:** con `max_drones=1` en casi
todas partes del mapa, la **sobre-demanda por una plaza es la norma, no la
excepción**. Cada turno hay más drones que plazas en algún cuello de botella. Eso
significa que **la regla de desempate importa más que la regla de prioridad**: la
prioridad solo decide entre los que están en cola, y la cola siempre está llena.

| Si esto | entonces |
|---|---|
| La capacidad casi nunca sobra | hay sobre-demanda en casi todos los turnos |
| Hay sobre-demanda en casi todos los turnos | el desempate decide el resultado |
| El desempate decide el resultado | **el desempate es la decisión más importante del proyecto** |

---

## 2. Qué tiene que decidir el scheduler (y qué no)

### 2.1 Lo que decide **[D]**

| # | Decisión | §cap. 09 |
|---|---|---|
| D-1 | ¿Cuántos drones van por cada camino? | §8.4 |
| D-2 | ¿En qué orden se atiende a los drones en un turno? | §8.1 |
| D-3 | Si varios quieren la misma plaza, ¿quién gana? | §8.1 |
| D-4 | ¿Un dron que podría moverse espera a propósito? | §3.1 |
| D-5 | ¿Un dron que espera mucho sube de prioridad? | §9.4 |
| D-6 | ¿Se replanifica cuando el camino se satura? | §11 |

### 2.2 Lo que NO decide (ya está decidido)

| Regla | Quién la pone |
|---|---|
| Turno de dos fases | **[S]** §VII.3 |
| No entrar en `blocked` | **[C]** `Zone.can_accept_drone` |
| Respetar `max_drones` | **[C]** `Zone.can_accept_drone` |
| Respetar `max_link_capacity` | **[C]** `Connection.have_capacity` |
| Un `restricted` son 2 turnos sin esperar en el enlace | **[S]** §VII.3 |
| Entregado = deja de rastrearse | **[S]** §VII.5 |

**Cualquier respuesta que contradiga esa tabla es un bug**, no una decisión de diseño.

### 2.3 Las tres piezas del scheduler

Independientemente de la estrategia, el bucle tiene esta forma:

```
   ┌── fase 1:.intenciones ────────────────────────────────────────┐
   │  para cada dron activo (en algún orden):                       │
   │      candidato = siguiente_paso(dron)          ← routing        │
   │      intención[dron] = (candidato, recursos que necesita)      │
   └─────────────────────────────────────────────────────────────────┘
                              │
   ┌── fase 2: resolución ──────────────────────────────────────────┐
   │  ordenar las intenciones según la ESTRATEGIA                    │
   │  recorrerlas granting en ese orden:                             │
   │      ¿cabe la plaza? → conceder / poner en cola                │
   │      ¿cabe la conexión? → conceder / poner en cola             │
   │      ¿es un restricted sin destino reservado? → no conceder     │
   └─────────────────────────────────────────────────────────────────┘
                              │
   ┌── fase 3: aplicación ──────────────────────────────────────────┐
   │  aplicar todas las concedidas a la vez (cap. 08 §5)             │
   │  los drones en tránsito avanzan su contador                     │
   └─────────────────────────────────────────────────────────────────┘
```

Lo que cambia entre estrategias es **una sola línea**: el criterio de `ordenar`.
Por eso una estrategia_first es, en el código, unas pocas líneas.

---

## 3. El criterio que optimizamos

Antes de elegir estrategia hay que decir **qué es "mejor"**, porque si no, "mejor" no
significa nada.

### 3.1 El objetivo principal **[S]**

§VII.6 lo dice sin rodeos:

> The performance of a solution is evaluated based on the **total number of
> simulation turns**. The fewer the number of turns, the better.

Ese número tiene nombre: el **makespan**, el turno en que llega el **último** dron
(cap. 09 §10.3).

### 3.2 Lo que NO es el objetivo

| Métrica | Por qué no es la principal |
|---|---|
| Turnos medios por dron | Un dron puede tardar 2 y otro 40; el promedio miente |
| Coste total de las rutas | Es una consecuencia del routing, no del scheduling |
| Drones movidos por turno | Es una consecuencia del makespan |

Y una consecuencia importante del makespan:

> **No sirve con que la mayoría llegue rápido.** Sirve con que **uno solo** no se
> atasque. Por eso las zonas trampa y los cuellos de botella dominan el diseño.

### 3.3 Métricas secundarias **[S] opcional**

§VII.6 las menciona como "no obligatorias pero animadas":

| Métrica | Cómo se calcula |
|---|---|
| Drones movidos por turno | `len(tokens) / T` |
| Media de turnos por dron | `makespan_por_dron` |
| Coste total de las rutas | `PathFinder.path_cost` (documentado en `02_pathfinding.md` §7, **no implementado**) |

Optimizar una segunda métrica **no debería costar turnos**. Si cuesta, es que hemos
optimizado la secundaria y hemos perdido la principal. Regla sana: **el makespan
manda; el resto se imprime, no se optimiza.**

---

## 4. El vocabulario de la complexities

Para poder comparar estrategias hace falta una notación. Con `D` drones, `V` zonas,
`E` conexiones, `T` turnos y `k` rutas:

| Símbolo | Significado | Valor típico (challenger) |
|---|---|---|
| `D` | drones | 25 |
| `V` | zonas | 54 |
| `E` | conexiones | 70 |
| `T` | turnos (makespan) | objetivo < 45 |
| `k` | rutas distintas | 2–4 |
| `deg` | grado medio de una zona | ~2,6 |

Y las dos operaciones de las que todo depende:

| Operación | Con estructura | Con lista |
|---|---|---|
| "extraer el mínimo de un conjunto" | `O(log n)` con `heapq` | `O(n)` |
| "ordenar D intenciones" | `O(D log D)` | `O(D log D)` |

**Y la consecuencia práctica:**

```
   Por turno:      ordenar/heap sobre D drones      →  O(D log D)
   Por simulación: T turnos × eso                  →  O(T · D log D)

   Challenger:  T=45, D=25  →  45 · 25 · log₂25  ≈  45 · 25 · 4,6  ≈  5.200

   Con adjacency index y Dijkstra cacheado, esto es instantáneo.
   El coste NO está en el scheduler. Está en no hacer algo tonto por dron y turno.
```

Tranquilizador, pero con una advertencia: si `T` se dispara por un deadlock y el
tope de no-progreso está mal puesto (por ejemplo 10.000 turnos), el mismo `O(T·D log D)`
pasa a ser un problema. **El tope de turnos es también una decisión de rendimiento.**

---

## 5. Las estrategias, una por una

Para cada una: **Idea · Ventajas · Inconvenientes · Complejidad · Cuándo funciona ·
Cuándo falla · Qué tan defendible es en peer review**.

---

### E-1 · Orden fijo (por nombre)

**Idea.** Los drones se atienden siempre en el mismo orden: `D1, D2, D3, …`. El
primero que pide la plaza contested se la lleva. Cero estado, cero parámetros.

```python
for drone in sorted(self.drones, key=lambda d: d.name):
    ...
```

**Ventajas**
- La más simple de implementar y de explicar: "el que tiene el número más bajo entra
  primero".
- **Determinista por construcción**, sin pedirle nada al `sorted()`: el nombre es
  `str` y por tanto totally ordered.
- No hay parámetros que elegir, y por tanto nada que tunear.
- Reproducible en el peer review: el revisor puede calcularlo a mano.

**Inconvenientes**
- Los drones altos (`D7`…`D25`) pueden quedarse **congelados** si los bajos tienen
  siempre prioridad y siempre hay alguien con prioridad delante. Es el
  *starvation* clásico.
- No sabe nada de distancias: un dron a un solo salto de `goal` puede ir detrás de uno
  que tiene medio mapa por delante.
- Es la peor posible en el makespan, y la diferencia se nota en `hard/03` (15 drones).

**Complejidad.** `O(D log D)` por turno si se ordena cada vez; `O(D)` si se ordenan
una vez al inicio. Total `O(T·D)`.

**Cuándo funciona bien.** Mapas con pocos drones y cuello de botella único, donde lo
que hay que serializar es una cola y el orden de la cola da igual.

**Cuándo puede fallar.** Muchos drones (≥8) y varios cuellos de botella. Aquí es donde
`hard/02` (12 drones) y `hard/03` (15) se levan la peor parte.

**Peer review.** *Muy fácil de explicar* y por eso mismo *poco impresionante*: es la
respuesta obvia, y el revisor va a preguntar "¿y si el `D13` nunca llega?". La defensa
es: *"funciona bien en easy/medium, y en hard documento el número real que da"*. Es
honesta, pero es weak.

---

### E-2 · Prioridad por cercanía al objetivo (el más cerca primero)

**Idea.** Cada dron tiene una distancia conocida al final (`dist`). En cada turno se
atiende primero al que tiene **menos turnos restantes**.

```
   D1 le faltan 2 saltos   ─┐
   D2 le faltan 5 saltos   ─┼──▶  orden: D1, D2
   D3 le faltan 9 saltos   ─┘
```

Y para calcular "turnos restantes" hace falta una distancia **hacia atrás**: un
Dijkstra **invertido** desde `goal`, hecho **una vez** y cacheado.

**Ventajas**
- Aprovecha el caso fácil: los drones que ya casi están llegan y se van, y el makespan
  lo marca el último.
- **Anti-starvation parcial**: un dron nunca va a estar mucho tiempo en cola si los que
  compiten con él tienen más camino.
- La distancia se calcula **una vez** (`O((V+E) log V)`) y se cachea como `PathFinder`
  ya cachea rutas (`pathfinding.py:18-20`). El coste por turno es solo ordenar.

**Inconvenientes**
- El "más cerca primero" **no quiere decir "el más urgente"**. Un dron a 1 salto de
  una zona `restricted` necesita 2 turnos, y uno a 3 saltos sin `restricted` puede
  llegar antes.
- Puede **invertir el flujo** en un cuello de botella: si el dron más cercano es el
  que ya está *en* la zona y su siguiente paso está libre, se mueve y el resto espera
  detrás, cuando lo óptimo sería dejar pasar a otro y que el que está dentro wait.
- Con `max_drones=1`, la distancia **no dice nada sobre la disponibilidad**: dos zonas
  a la misma distancia pueden estar una vacía y otra con cola de 5.

**Complejidad.** Precomputación `O((V+E) log V)`; por turno `O(D log D)`. Total
`O((V+E) log V + T·D log D)`.

**Cuándo funciona bien.** Mapas donde la distancia a `goal` correlate bien con el
makespan: rutas en serie, pocas alternativas, pocos `restricted`.

**Cuándo puede fallar.** Mapas con muchas rutas alternativas y cuellos de botella
desiguales: manda al más cercano a una cola larga mientras otro tiene un camino libre
a la derecha.

**Peer review.** *Fácil de explicar* ("el que está más cerca del final tiene prioridad")
y con una justificación buena: *"en el makespan, el dron que está más cerca es el que
determina cuándo acaba la simulación"*. Con un diagrama de §1.3 (los dos drones con
distintas distancias restantes) se defiende muy bien.

---

### E-3 · Prioridad por tiempo estimado (ETA)

**Idea.** Igual que E-2, pero en lugar de contar saltos se cuenta **turnos reales**:
un `restricted` en el camino pesa 2. La distancia se calcula con los mismos costes que
`ZONE_COSTS` (`models.py:21-25`), que ya están.

```
   D1: le faltan 4 saltos, uno de ellos restricted   → ETA = 5 turnos
   D2: le faltan 4 saltos, ninguno restricted       → ETA = 4 turnos   ← va primero
```

**Ventajas**
- Es la métrica **correcta** para el makespan: "cuántos turnos me faltan de verdad" es
  exactamente lo que determina el final.
- Es la generalización correcta de E-2: cuando no hay `restricted`, E-3 y E-2 coinciden
  (y entonces E-3 no tiene coste extra).

**Inconvenientes**
- Es un refinamiento de E-2, así que **hereda todos sus fallos**.
- La ETA **no sabe de esperas**: estima el camino ideal, no el camino con colas. En
  `hard/02`, donde lo que marca los turnos son las compuertas, la ETA es optimista.
- Exige que el inverso de Dijkstra use los mismos costes que el pathfinding, y hoy
  `_step_cost` (`pathfinding.py:22-26`) está diseñado para ir **hacia delante**. Reutilizarlo
  al revés no es gratis, y `restricted` además obliga a contar el turno en la conexión.

**Complejidad.** Igual que E-2.

**Cuándo funciona bien.** Mapas con `restricted` en rutas cortas, donde dos caminos con
los mismos saltos tienen coste muy distinto (`medium/03_priority_puzzle`).

**Cuándo puede fallar.** Los mismos casos que E-2.

**Peer review.** *Buena*, pero exige explicar dos cosas (la ETA y su límite). Si se
elige esta, la respuesta a *"¿por qué no el más corto?"* es: *"porque el makespan se
mide en turnos, no en saltos, y un `restricted` son dos"* — que es la misma respuesta
que ya das para justificar Dijkstra frente a BFS (`ask&ques.md` C1). Eso reutiliza un
argumento que ya tienes, y reutilizar argumentos es buena estrategia.

---

### E-4 · Greedy de máximo avance

**Idea.** En cada turno, se calcula para cada dron **cuántos movimientos podría hacer
si nada se lo impidiera**, y se atiende primero al que más podría avanzar. "Grandes
primero".

```
   D1 puede avanzar 1 paso  ─┐
   D2 puede avanzar 4 pasos  ─┼──▶  orden: D2, D1
   D3 no puede avanzar       ─┘        (D3 espera; no tiene a dónde ir)
```

**Ventajas**
- Directamente orientado al makespan: mueve a los que "están libres" y deja a los
  bloqueados, que es lo que suele preservar el paralelismo.
- Elimina de un plumazo el problema del dron bloqueado: no entra en la cola porque la
  cola no le compete.
- Es la opción que más se ve "inteligente" en el peer review si se dibuja bien.

**Inconvenientes**
- "Cuántos movimientos podría hacer" hay que definirlo con cuidado, y cualquier
  definición razonable **mira el estado del turno siguiente**, no el actual.
- Es **miope**: maximiza el paralelismo de *este* turno a costa de atascar el
  siguiente. Es el compromiso clásico de los planificadores *voraces* (greedy).
- **No es simétrico**: dos drones con el mismo potencial y distinta distancia restante
  se ordenan por algo que no afecta al makespan final.
- Muy dependiente de la calidad de `siguiente_paso()`: si esa función es mala, la
  estrategia es mala y no se ve por qué.

**Complejidad.** `O(D · deg)` por turno si "cuánto puede avanzar" se calcula explorando;
`O(D log D)` si se cachea por posición. Total `O(T·D·deg)`.

**Cuándo funciona bien.** Mapas anchos con muchas rutas alternativas y pocas
restricciones.

**Cuándo puede fallar.** Mapas en serie (todo el mundo compite por lo mismo): el "más
potencial" es el que está más al principio de la cola, que es lo contrario de
justo.

**Peer review.** *La más difícil de defender.* La pregunta *"¿por qué mover primero al
que más puede avanzar?"* no tiene una respuesta intuitiva, y la respuesta honesta es
"porque lo probé y daba mejor". Eso no es una defending; es un dato empírico. Si se
quiere defender de verdad hace falta una demostración de que no produce *starvation*,
y eso hay que medirlo, no razonarlo.

---

### E-5 · Prioridad por cuello de botella

**Idea.** Un dron tiene prioridad si su ruta pasa por un recurso **escaso**
(`max_link_capacity=1` o `max_drones=1` y ya con cola). El objetivo: sacar primero a
los drones que van a necesitar el cuello de botella **más adelante**, para que la cola
se vacíe más tarde y la última persona pase antes.

```
   Recurso      cola    drones pendientes que lo necesitan
   m (cap 1)     3         D2, D5, D9
   g1 (cap 1)    0         D3, D7

   Los que van a m son urgentes: si tardan, m sigue ocupado al final.
   → D2, D5, D9 primero
```

**Ventajas**
- Es la única estrategia que **mira el final de la simulación** en vez de un turno. El
  recurso con cola es un predictor directo de "dónde se va a atascar la cola".
- Justifica formalmente la frase de `ask&ques.md` D15 (*"los turnos los marca el cuello
  de botella, no la longitud del camino"*) con código, no solo con prosa.
- Reduce el caso peor del *starvation* en cuellos de botella (los que dependen de un
  recursoscaro no se acumulan al fondo).

**Inconvenientes**
- Hay que **precomputar** qué recursos usa cada dron y qué tanscaros son. Con
  `max_drones=1` por defecto, "todo es un cuello de botella": la noción de "escaso"
  necesita un criterio (¿capacidad ≤ 1? ¿cola ≥ k?).
- La información cambia **cada turno** (la cola cambia), así que o se recalcula cada
  turno, o se recalcula cada k turnos.
- Es la estrategia más cara de explicar y de mantener: es un concepto nuevo, y los
  conceptos nuevos en un peer review son un riesgo.
- Puede **invertir el flujo**: mandar primero al dron que va al cuello de botella puede
  vaciar una zona intermedia que otro dron necesitaba para pasar.

**Complejidad.** Precomputación `O(k·(V+E))` para puntuar los recursos de las k rutas;
por turno `O(D log D)` con la puntuación recalculada, o `O(D·D)` si se recalcula a
mano. Total `O(k·(V+E) + T·D log D)` en la versión(cacheada).

**Cuándo funciona bien.** Mapas tipo `hard/02` y `hard/03`: compuertas en serie, colas
en los cuellos de botella, una sola ruta posible.

**Cuándo puede fallar.** Mapas con muchas rutas y pocas cuellos: el criterio apenas
distingue, así que se comporta casi como E-1, con toda la complejidad añadida.

**Peer review.** *La másell's de explicar* pero también la más generously
defendible si se ha medido: *"mira, en `hard/02` esta estrategia da N turnos frente a
M con el orden fijo"*. Es un argumento empírico, pero un empírico **con un mecanismo
explicado**, que es infinitamente mejor que un empírico sin mecanismo.

---

### E-6 · Antigüedad / *aging*

**Idea.** Cada dron lleva un contador de turnos esperando. Si supera un umbral `k`, su
prioridad sube por encima de la regla normal. O más simple: **el que más ha esperado
tiene prioridad**.

```
   D1: 0 turnos esperando   ─┐
   D2: 3 turnos esperando   ─┼──▶  orden: D2, D1
   D3: 1 turno esperando    ─┘
```

**Ventajas**
- Es el **antídoto directo y barato** contra el *starvation*. Cualquier estrategia de
  las anteriores puede envolverse en E-6 para que sea *justa*.
- Es la regla que usan de verdad los planificadores de CPU y de red, y eso se puede
  citar.
- Es trivially explicable: *"nadie espera más de k turnos"* es una frase que se
  entiende sin diagrama.

**Inconvenientes**
- **El aging puro (E-6 solo) es una estrategia mala**: prioriza a quien más ha
  esperado, que no tiene por qué ser quien está más cerca de acabar. En un cuello de
  botella único crea una oscilación (el que más espera va primero, luego el otro...).
- Como **regla de desempate** es ideal; como estrategia principal es mala.
- Necesita un parámetro `k`, y los parámetros son cosas que hay que justificar.

**Complejidad.** `O(D log D)` por turno, con un `int` más por dron.

**Cuándo funciona bien.** Como **segundo criterio**, cuando dos drones empatan en la
regla principal. Ahí es imbatible: desempata de forma útil y justa.

**Cuándo puede fallar.** Como estrategia única. Y en mapas donde la espera es
estructural (colas de capacidad 1), el aging solo cambia **quién** está en la cola de
la cabeza, no cuánto dura la cola.

**Peer review.** *Excelente como respuesta a la pregunta inevitable*: *"¿qué pasa si
alguien se queda sin mover nunca?"*. La respuesta *"el aging le sube la prioridad a la
larga k turnos"* es exactamente lo que un revisor quiere oír, porque ya ha visto
muchos proyectos donde un dron se queda atrás para siempre.

---

### E-7 · Rotación (round-robin por turnos)

**Idea.** En vez de un orden fijo, el orden de atención **rota**: el dron que fue
atendido primero en el turno `t` pasa al final para el turno `t+1`. Es E-1 con memoria
de una sola posición.

```
   turno 1:  D1, D2, D3
   turno 2:  D2, D3, D1
   turno 3:  D3, D1, D2
```

**Ventajas**
- **Elimina el `starvation` por construcción**, sin parámetros: si todos son atendidos
  en rotación, ninguno se queda atrás para siempre.
- Sigue siendo determinista.
- Coste cero: es un índice que se incrementa.

**Inconvenientes**
- **Rompe el criterio de prioridad**: el dron más cercano puede ir primero en un turno y
  el tercero en el siguiente, y eso no lo quiere nadie. Es fairness sin eficiencia.
- Con `max_drones=1`, rotar la cola **no cambia el makespan**: la cola se drena en el
  mismo orden de todos modos, solo que más lento por el recuerdo. Puede incluso
  empeorar el makespan, porque el dron que estaba en cabeza puede pasar al fondo de la
  cola de una zona.

**Complejidad.** `O(D log D)` por turno. Un índice más.

**Cuándo funciona bien.** Mapas con una sola ruta y un cuello de botella, donde lo que
importa es la justicia, no la velocidad.

**Cuándo puede fallar.** Mapas donde hay varios caminos utilizables a la vez: la
rotación desperdicia el paralelismo.

**Peer review.** *Fácil de explicar* y *muy fácil de descalificar*: *"pero eso
reparte drones al azar, ¿no?"*. Difícil defender E-7 como estrategia **principal**.

---

### E-8 · Reparto de rutas (k shortest paths)

No es una alternativa a las anteriores: es un **complemento** que se puede combinar
con cualquiera de E-1 a E-7. Pero es tan determinante (§1.2 lo demostró con números)
que hay que tratarla aparte.

**Idea.** En lugar de una sola ruta para todos, calcular `k` rutas distintas y
distribuir los drones entre ellas.

```
   E-1:  shortest_path(start, goal)                       1 búsqueda  →  1 ruta
   E-8:  shortest_path(start, goal)                       1 búsqueda  →  ruta 1
         shortest_path(start, goal, evitando ruta 1)      1 búsqueda  →  ruta 2
         shortest_path(start, goal, evitando rutas 1 y 2) 1 búsqueda  →  ruta 3
```

**Ventajas**
- Es **la** palanca que mueve el makespan en `hard/02` y `hard/03`, por la aritmética
  de §1.2: cada ruta paralela da un turno extra de flujo.
- Es **lo que dice §VII.1**: *"Distribution of drones across multiple paths"*. O sea,
  el subject lo **pide explícitamente**. Ignorarlo es arriesgado.
- Con la caché de `PathFinder` (`pathfinding.py:18`) calcular 3 rutas cuesta 3
  búsquedas, no 3×D: la caché ya lo hace gratis.
- Se **ve** en el peer review: *"estos 4 drones van por `path_a` y estos 4 por
  `path_b`"* es una frase con un diagrama detrás.

**Inconvenientes**
- Hay que **excluir** la ruta anterior en la siguiente búsqueda, y eso significa que
  `PathFinder` necesita una forma de "búsqueda con penalización" o "búsqueda
  restringida". Hoy `shortest_path(start, end)` no tiene ese parámetro (`pathfinding.py:69`),
  así que **esto toca `pathfinding.py`**.
- El reparto `k` drones por ruta no es necesariamente óptimo: si una ruta tiene un
  cuello de botella y la otra no, hay que repartir por **cuello de botella**, no a
  partes iguales.
- `k` es un parámetro más que justificar (¿2? ¿3? ¿Cuántos vecinos tiene `start`?).

**Complejidad.** `O(k·(V+E) log V)` para las k búsquedas. Una vez. El reparto en sí es
`O(D)`.

**Cuándo funciona bien.** Mapas con bifurcaciones reales: `easy/02`, `medium/03`,
`hard/01`, `hard/03`, y en principio el challenger.

**Cuándo puede fallar.** Mapas con una sola ruta (no hay nada que repartir) y —esto es
lo importante— **cuando el cuello de botella está DESPUÉS de la bifurcación**. Repartir
no sirve de nada si todos se reencontran en el mismo `M`:

```
        a1 -- a2 --+
       /          \
  S --+           M (cap 1) ── G     4 drones, dos ramas
       \          /                    ← ¡repartidas siguen serializando en M!
        b1 -- b2 --+

   Repartir 2 y 2: el cuello sigue siendo M. La diferencia se la come la cola.
```

En ese caso el reparto **no empeora** nada y da la sensación de haber hecho algo. Es un
peligro real para el peer review: un revisor pregunta *"¿el reparto mejora algo aquí?"*
y la respuesta honesta puede ser *"en este mapa no"* (`01_dijkstra.md` Tricuñuela 4 ya
advierte de un caso parecido con `priority`).

**Peer review.** *La más fácil de defender* **si** se acompaña de la tabla de §1.2 con
los números reales de `easy/02`. Y es la que el subject nombra, lo que la hace
imprescindible.

---

### E-9 · Reserva con mirada al futuro (*lookahead*)

**Idea.** No se concede una plaza solo porque cabe **ahora**, sino solo si el dron puede
**completar** el movimiento. Para un `restricted` es literal (§VII.3). Y la versión
general: antes de conceder un movimiento, se comprueba que el dron no se va a quedar
**encajonado** en el destino.

```
   Regla simple [S] :  entrar en restricted exige plaza reservada en el destino
   Regla fuerte [D]  :  entrar en CUALQUIER zona exige que exista un plan de salida
                       (o al menos que el destino no sea un callejón sin salida lleno)
```

**Ventajas**
- La regla fuerte es la que **realmente** mata los deadlocks: en `medium/01_dead_end_trap`
  no dejaría entrar a nadie en `dead_end` mientras `dead_end` esté llena.
- Es la extensión natural de una regla que **ya está en el subject** (§VII.3), lo que
  hace la defensa mucho más fácil: *"el subject ya dice que no puedes esperar en la
  conexión; yo extiendo el mismo principio a las zonas"*.
- Es **testeable**: *"ningún dron debería quedarse sin salida"* es un invariante que se
  puede comprobar después de cada turno.

**Inconvenientes**
- La regla fuerte **puede paralizar** la simulación si se aplica sin prudencia: si
  todas las opciones llevan a un callejón lleno, nadie se mueve, y el tope de
  no-progreso (cap. 09 §9.3) aborta. Es decir: el antídoto del deadlock se puede
  convertir en la **causa** del error.
- Exige saber qué es "sin salida": si `dead_end` es legal como zona, ¿por qué no ir
  nunca? Porque hay otros drones dentro, pero eso es estado, y entonces la regla se
  come el problema.
- Es difícil de diferenciar de "el scheduler ha decidido que no es buen momento", que es
  justo la distinción que §VII.1 quiere clara.

**Complejidad.** La regla simple: nada (`O(1)`). La regla fuerte: `O(D · deg)` por turno,
o peor si "plan de salida" significa un `shortest_path` por dron y turno (que se cachea,
así que `O(1)` amortizado si la ruta ya está calculada).

**Cuándo funciona bien.** Mapas con trampas explícitas (`medium/01_dead_end_trap`).

**Cuándo puede fallar.** Mapas sin callejones, donde no aporta nada; y mal implementado,
en cualquier mapa.

**Peer review.** *Muy buena*, porque es la regla del subject **extendida con el mismo
espíritu**, y porque responde de antemano a la pregunta de §III.1 (*"si el programa se
cuelga, es no funcional"*). Pero hay que medir que no produce paros.

---

### E-10 · Búsqueda sobre el espacio de estados

**Idea.** En vez de decidir turno a turno, **planificar** los próximos `h` turnos
explorando el espacio de estados (quién está en qué zona) y elegir el plan que
minimiza el makespan. Es A\* o BFS sobre el estado de la simulación, no sobre el grafo
de zonas.

**Ventajas**
- Es **el único enfoque que optimiza de verdad**, porque optimiza el makespan
  directamente en vez de buscar una heurística que lo aproxime.
- Si el horizonte `h` cubre el mapa entero, encuentra la solución óptima (o demuestra
  que no hay solución).

**Inconvenientes**
- El espacio de estados es **(distribución de drones sobre zonas)**: para `D` drones y
  `V` zonas son del orden de `V^D` (muchísimo). Con `D=25` y `V=54` es
  imposible.
- Con horizon `h` limitado, la búsqueda es `O(b^h)` con `b` el branching factor. Con
  `h=3` y `b=6` ya son 216 estados por nodo, y cada estado hay que generarlo moviendo
  todos los drones.
- **Rompe la separación del proyecto**: el cap. 01 (`sobre_mi_pryecto.md` §3) separa
  routing de scheduling. Aquí el scheduler **reimplementa el routing** dentro de la
  búsqueda, porque el "siguiente paso" ya no viene de `PathFinder` sino del propio
  plan.
- Es, con diferencia, **lo más difícil de defender** y lo que más código exige.

**Complejidad.** `O(b^h · D)`. Con `b = 6`, `h = 5` → 7776 · D. Y `h` no puede
crecer.

**Cuándo funciona bien.** Mapas pequeños (4–6 zonas, 2–3 drones), como **verificador
de optimalidad**: si el greedy da 7 y la búsqueda exhaustiva da 6, se sabe que el
greedy pierde 1.

**Cuándo puede fallar.** En cualquier mapa real. En el challenger es inabordable.

**Peer review.** *La peor opción para el peer review si es la principal*: alguien
preguntará por la complejidad y la respuesta es exponencial, y la segunda pregunta
será *"¿y si no cabe en memoria?"*. Como **herramienta de verificación** (comparar el
número del greedy con el óptimo en los mapas easy) es **excelente** y se puede
mencionar como tal.

---

### 5.1 Resumen comparativo

| | Idea en una frase | Coste/turno | Anti-`starvation` | ¿Mejora el makespan? | Peer review |
|---|---|---|---|---|---|
| **E-1** | Orden fijo `D1..Dn` | `O(D)` | ✗ | Regular | Fácil, pero obvia |
| **E-2** | El más cerca del final | `O(D log D)` | ~ | Bien | Fácil y buena |
| **E-3** | El de menor ETA | `O(D log D)` | ~ | Bien | Buena |
| **E-4** | El que más puede avanzar | `O(D·deg)` | ✗ | Impredecible | Difícil |
| **E-5** | El que va al cuello de botella | `O(D log D)` | Parcial | **Muy bien** en hard | Media, con datos |
| **E-6** | El que más ha esperado | `O(D log D)` | **✓** | Malo solo | Excelente como desempate |
| **E-7** | Rotación | `O(D log D)` | **✓** | Regular | Fácil, débil |
| **E-8** | Reparto k rutas | precomp. | — | **Muy bien** si hay ramas | La más fácil |
| **E-9** | Reservas con lookahead | `O(1)`–`O(D·deg)` | ✓ | Bien | Buena |
| **E-10** | Búsqueda exhaustiva | `O(b^h·D)` | ✓ (óptimo) | Óptimo | Mala (exponencial) |

---

## 6. Una nota de expectativas (importante para el peer review)

Con `max_drones=1` y `max_link_capacity=1` en casi todo (los defaults de §VI), cada
zona y cada enlace tienen **capacidad de una sola ficha**. Es decir: el problema es
*"mover N fichas de un vértice a otro en un grafo, minimizando el número de rondas,
con movimiento simultáneo"*.

Eso tiene una forma muy parecida a los problemas de **movimiento de fichas con coste
mínimo**, que son de los difíciles combinatorios. Traducción práctica:

| Lo que eso significa | Consecuencia |
|---|---|
| No hay un algoritmo greedy que garantiza el óptimo | El objetivo de §VII.7 es un **objetivo**, no una promesa |
| Cuellos de botella de capacidad 1 **imponen** cotas inferiores | 12 drones y una compuerta de capacidad 1 ⇒ **≥ 12 turnos** solo por esa compuerta |
| Las ramas paralelas dan Benefit sí, pero acotado | `k` ramas ⇒ ≈ `1/k` del tiempo de cola, no `/k` del makespan |

La cota inferior del segundo punto es un argumento **precio** para el peer review, y
sale directamente de §VI + §VII.7:

```
   hard/02_capacity_hell:  12 drones
   La cadena start → gate1 → gate2 → gate3 tiene max_drones=1 en las tres compuertas
   ⇒ cada compuerta necesita ≥ 12 turnos ⇒ makespan ≥ 12 + camino de salida

   Objetivo de §VII.7: ≤ 35 turnos.   Resultado de referencia: 45.
   La pregunta correcta en el peer review no es "¿por qué no 20?" sino
   "¿cuál es la cota inferior de este mapa y qué tan cerca estás?"
```

Calibrar la expectativa **antes** de la revisión es una de las cosas que separan un
proyecto bien explicado de uno que se defiende con excusas.

---

## 7. Las piezas que toda estrategia necesita

Para poder elegir y luego implementar, hay que tener decididos estos "parámetros
conceptuales". Cada uno es una pregunta abierta **[D]**:

| Parámetro | Pregunta | Opciones |
|---|---|---|
| **Reparto de rutas** | ¿Cuántas rutas? ¿Cómo se asignan los drones? | 1 ruta · k round-robin · k por demanda · k por cuello de botella |
| **Prioridad** | ¿Qué dron se atiende primero? | E-1 a E-7 |
| **Desempate** | Si dos empatan, ¿quién? | Orden fijo · aging · el de ETA menor |
| **Espera voluntaria** | ¿Un dron que puede moverse espera? | No (siempre avanza) · Sí, por qué |
| **Antidoto de deadlock** | ¿Qué impide el atasco? | Tope de no-progreso · reservas · aging |
| **Replanificación** | ¿Se recalcula el camino? | No (estático) · Si el paso está bloqueado · Por congestión |
| **Tope de turnos** | ¿Cuándo se aborta? | Sin tope · Por no-progreso (1 turno) · Por nº absoluto |

Y hay **una variable más** que no es una decisión de scheduling pero condiciona a
todas, y que está en el cap. 08 §7.4 y en el cap. 09 §7.6:

| Parámetro | Pregunta | Impacto |
|---|---|---|
| **Estado en tránsito** | ¿`position` se ensancha o hay campo aparte? | Es el tipo de todo lo demás, y fija el invariante |

---

## 8. Las decisiones que debemos tomar juntos

Esta es la lista que se convierte en preguntas al final de este trabajo. **Ninguna
tiene respuesta cerrada por el subject ni por el código actual.**

| # | Decisión | Por qué importa | Dónde se aplica |
|---|---|---|---|
| 1 | ¿Cuántas rutas y cómo se reparten los drones? | Es lo que más mueve el makespan (§1.2) | Scheduler + `pathfinding` |
| 2 | ¿Qué prioridad entre drones? | Decide quién avanza en cada cola | Scheduler |
| 3 | ¿Cómo se desempata? | Con `max_drones=1` la sobre-demanda es la norma | Scheduler |
| 4 | ¿Se esperadq a propósito? | Puede ganar o perder turnos | Scheduler |
| 5 | ¿Qué se hace con un dron sin ruta? | Sin esto el programa se cuelga | Simulación |
| 6 | ¿Cómo se modela la capacidad del enlace? | Hoy `max_link_capacity` no se aplica | Cap. 09 §6.3 |
| 7 | ¿Cómo se representa el dron en tránsito? | Fija el tipo de `position` y el invariante | Cap. 08 §7.4 |
| 8 | ¿Se replanifica? | Con rutas estáticas los mapas hard se atascan | Scheduler + routing |
| 9 | ¿Qué se hace si un turno no mueve a nadie? | Un bucle infinito es "no funcional" | Simulación |
| 10 | ¿Simplicidad/explicabilidad o rendimiento? | Es un compromiso, no un detalle | Todo el diseño |
| 11 | ¿Qué estrategia concreta? | La decisión que lo engloba todo | Scheduler |

---

## 9. Lo que NO entra en este capítulo

- **El código de `simulation.py`.** Este capítulo elige la estrategia; el código viene
  después, y solo cuando la estrategia esté decidida.
- **El output.** Cómo se imprime el turno es el cap. 11.
- **La visualización.** Cómo se ve el grafo es el cap. 11 también.
- **El benchmark de turnos.** Está en §6, y su respuesta es "se mide después,
  cuando exista `Simulation`".

## 10. Verificación al terminar

1. Saber explicar la diferencia entre routing y scheduling **sin mirar el cap. 08**, y
   dar un ejemplo de mapa donde cambia el resultado.
2. Saber decir por qué el desempate importa más que la prioridad en estos mapas, y
   tener el argumento de §1.3.
3. Saber dar una cota inferior de turnos para `hard/02` y explicarla con los defaults
   de §VI.
4. Saber explicar por qué `max_drones=1` convierte la ocupación de una conexión en un
   problema de duración distinta al de una zona.
5. Saber decir qué parte de E-8 no requiere tocar `pathfinding.py` y qué parte sí.
6. Tener una preferencia argumentada entre E-1 y E-5, y saber decir qué medirías para
   defenderla.
7. Saber decir qué estrategia es **imposible** en este proyecto y por qué (E-10, por
   ejemplo, y el coste en estado del espacio de estados).