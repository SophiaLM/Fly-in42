# 09. Movimientos, capacidades, restricted, conflictos y finalización

Este es el capítulo **normativo** de la simulación: aquí está, traducida a código,
cada regla del sujeto. Si algo del cap. 10 (scheduling) parece confuso, vuelve aquí:
esta es la parte que **no** es decisión nuestra.

Contenido:

- §1 los tres verbos de un dron
- §2 movimiento normal, paso a paso
- §3 la espera
- §4 movimiento simultáneo y entrada/salida
- §5 `max_drones`
- §6 `max_link_capacity`
- §7 `zone=restricted`: el caso difícil
- §8 catálogo de conflictos
- §9 deadlocks
- §10 finalización
- §11 tabla requisito / decisión
- §12 errores que verás antes de entendernos

---

## 0. Recordatorio de etiquetas

| Etiqueta | Significa |
|---|---|
| **[S]** | Requisito del subject. No negociable. |
| **[C]** | Código que ya existe en `fly/src/`. |
| **[D]** | Nuestra decisión de diseño. |

> Cada vez que veas un `▸` tras un número de regla, es una cita o una paráfrasis
> marcada del enunciado. Cada vez que veas **[D]**, es una decisión pendiente.

---

## 1. Los tres verbos de un dron

**[S] §VII.3**, literalmente:

> At each turn, every drone may:
> - Move to an adjacent connected zone (if capacity allows).
> - Move to a connection towards a restricted zone (that requires 2 turns to be
>   reached). In this case, the drone MUST reach its destination during the next
>   turn. It can't wait extra turns on the connection.
> - Stay in place (e.g., to wait, or if movement is blocked).

Traducido, en cada turno **cada dron** está en exactamente uno de estos estados:

```
┌──────────────────┐
│  EN ZONA         │  position es una Zone
│  ┌────────────┐  │  → mover  : a la vecina (si cabe)
│  │            │  │  → esperar : quedarse
└──┴────────────┘──┘
        │
        │ entra en restricted  (2 turnos)
        ▼
┌──────────────────┐
│  EN TRÁNSITO      │  position es una Connection
│                   │  → nada: DEBE llegar en el siguiente turno
└─────────┬────────┘
          │ llega
          ▼
┌──────────────────┐
│  EN ZONA         │
└─────────┬────────┘
          │ llega a end
          ▼
┌──────────────────┐
│  ENTREGADO       │  ya no se rastrea (§VII.5)
└──────────────────┘
```

Los cuatro estados son **deseables**. Un dron en tránsito está haciendo lo correcto;
un dron que espera está haciendo lo correcto; un dron entregado está terminado. El
único estado "mal" es el que este capítulo no tiene: **perdido**.

---

## 2. El movimiento normal, paso a paso

Movimiento de **1 turno**: el dron pasa de `A` a `B`, conectadas, sin que `B` sea
`restricted`.

### 2.1 Con un solo dron

```python
g = parse_map_file("test/maps/easy/01_linear_path.txt")
# start(0,0) -- waypoint1(1,0) -- waypoint2(2,0) -- goal(3,0)

d = Drone("D1", g.zones["start"], g.zones["goal"])
g.zones["start"].add_drone(d)          # ← sin esto, el invariante está roto

g.move_drone(d, g.zones["waypoint1"])  # True
```

Qué ha pasado por dentro, en orden (`models.py:178-201`):

```
 1. find_connection(start, waypoint1)      →  la Connection existe          ✔
 2. conn.have_capacity()                   →  0 drones en la conexión < 1    ✔
 3. target.can_accept_drone()              →  0 drones < max_drones(=1)      ✔
 ─────────────────────────────────────────────────────────────────────────────
 4. drone.move_to(target)                  →  ejecuta (§2.2)
```

Y qué se ha movido de verdad:

```
 4a. target.add_drone(drone)      # primero:  lanza ValueError si está llena
 4b. self.position.remove_drone(drone)
 4c. self.position = target
```

### 2.2 Por qué `add` antes que `remove`

Orden inverso, y el fallo deja el dron **en ninguna zona**:

```
  remove  →  add falla (llena)  →  drone.position = waypoint1  pero
            waypoint1.drones = []   ✗ el dron no está en ningún sitio

  add     →  add falla           →  nada ha cambiado todavía              ✔
```

`move_to` (`models.py:137-158`) lo documenta y además pone un **guard**: si el
invariante ya estaba roto antes de la llamada, lanza `ValueError` en vez de empeorar
el estado. El orden correcto **no** contradice §VII.3: §VII.3 habla de la liberación
**por turno**, y eso lo implementa `simulation.py`, no `move_to` (`act.md` §2.1b).

### 2.3 El movimiento NO sabe de turnos

`move_drone` no sabe qué turno es. No puede: es una operación de *una zona a otra*.
El turno lo pone `simulation.py` alrededor. Por eso `move_drone` es exactamente igual
para un movimiento de 1 turno que para el primer tramo de uno de 2: la diferencia no
está en el movimiento, está en **lo que se hace después**.

---

## 3. La espera

Esperar es una acción de primer orden. Ejemplo real, `easy/01_linear_path` con 2
drones y `max_drones=1` en cada zona:

```
Turno 1:  D1: start → waypoint1     D2: espera (w1 está ocupada por D1 al final del turno)
Turno 2:  D1: waypoint1 → waypoint2  D2: start → waypoint1     (w1 se liberó este mismo turno)
Turno 3:  D1: waypoint2 → goal       D2: waypoint1 → waypoint2
Turno 4:  D2: waypoint2 → goal       D1: entregado (llegó en el turno 3)
                                        ────── fin: makespan = 4
```

Son **4 turnos**, y coincide con el cálculo de §5.2. Dos detalles que importan:

- La **entrega ocurre al llegar** (`[S]` §VII.5): D1 llega a `goal` en el turno 3 y
  queda entregado en ese mismo turno. No hay un turno extra de "entrega", así que la
  simulación termina en el turno 4 y no en el 5.
- D2 entra en `waypoint1` **en el mismo turno en que D1 lo deja**. Eso es §VII.3 en
  acción, y es lo que separa 4 turnos de 7.

### 3.1 Cuándo espera un dron **[D]**

El sujeto **no dice** cuándo esperar; dice que esperar es legal. Las razones
posibles son cuatro, y distinguirlas es clave para el peer review:

| Motivo | Descripción | ¿Quién lo decide? |
|---|---|---|
| **Bloqueo de destino** | La zona de destino está llena (o casi) | **[C]** `can_accept_drone()` |
| **Bloqueo de enlace** | La conexión no tiene hueco | **[C]** `have_capacity()` |
| **Reserva de un `restricted`** | Al entrar en `restricted`, el destino no tiene hueco reservado | **[S]** §VII.3: no puede esperar en la conexión |
| **Decisión propia** | Podría moverse pero es mejor esperar | **[D] scheduling** |

Los tres primeros se detectan preguntando a los objetos. El cuarto es el único que no
se deduce de una regla, y es el tema del capítulo 10.

---

## 4. Movimiento simultáneo: entrada y salida

**[S] §VII.3**, las dos frases que lo gobiernan:

> - Drones moving out of a zone free up capacity for that same turn.
> - A zone must have available capacity for a drone to move into it (**after all
>   drones moving out have freed up space**).

### 4.1 La aritmética de la capacidad

Para validar una entrada hay que contar el estado **post-salidas**, no el actual:

```
  capacidad disponible en Z = capacidad(Z)
                              - |ocupantes(Z) que NO salen este turno|
                              - |entrantes ya aceptados a Z este turno|

  La entrada es legal si  disponible >= 1
```

Con un ejemplo, el más pequeño posible:

```
  Mapa:   start ── w ── goal          w con max_drones=1
  Estado: w = [D1].   D1 va a w2.  D2 (en start) quiere entrar en w.

     oxidase = {w, w2}                 ← los dos se van
     ocupantes de w que NO se van = 0   ← D1 se va
     → disponible = 1 - 0 = 1  ✔  D2 entra
```

Y el caso contrario, que es el que da miedo:

```
  Estado: w = [D1].   D1 va a w2.  D2 y D3 (en start) quieren entrar en w.
    salientes  outgoing = {w, w2}
     disponibles = 1 - 0 = 1
     D2 entra ✔   →   quedan 0
     D3 no cabe ✗  →  D3 espera
```

Nótese que la información que hace posible esta aritmética **solo existe entre las
dos fases**. En la fase 1 los tres drones han declarado; en la fase 2 se cuentan
junto los que salen y los que entran. Por eso la fase 1 no puede "aplicarse" sobre la
marcha.

### 4.2 El intercambio, que parece un choque y no lo es

```
  Estado t:              Estado t+1:
  start:[D1,D2]  ──┐     start:[]     ───▶  D2 se va
  w1:[D2]        ──┤     w1:[D1]           D1 se queda
  w2:[D1]        ──┘     w2:[D2]           D2 se va

  Dos drones cruzan en sentidos opuestos. Legal.
  En ningún instante hay dos drones en la misma zona.
```

Es legal, pero **es una decisión de diseño si lo exploited o no**. Nada obliga a que
un dron tome el camino de otro si lo que quiere es cruzar. Ver cap. 10.

---

## 5. `max_drones` — cuántas personas caben en una sala

**[S] §VI** (default): `max_drones=<number>` (default: 1).
**[S] §VII.2:** *"By default, a zone may contain at most one drone at any given
simulation turn."*

### 5.1 Dónde está implementado **[C]**

```
  models.py:52-63   Zone.can_accept_drone()

      if zone_type is BLOCKED:        return False     ← §VI "blocked" inválida
      if is_start or is_end:          return True      ← §VII.2 sin límite
      if max_drones is None:          return True      ← sin límite (a mano)
      return len(self.drones) < self.max_drones
```

Y tres decisiones ya tomadas alrededor:

| Decisión | Dónde | Por qué |
|---|---|---|
| El default `1` lo pone el **parser**, no el modelo | `builders.py:38-47` | El default es parte del formato del fichero |
| El default `1` **nunca** se aplica a `start`/`end` | `builders.py:39` | §VII.4: "se ignora y no es error de validación" |
| `Zone.max_drones` es `int \| None`, `Connection.max_link_capacity` es `int` | `models.py:46`, `:89` | `None` solo existe de verdad en start/end |

### 5.2 Qué cuenta como "ocupado"

**[D] + [S]** Hay un matiz sutil aquí, y es la razón por la que el turno de dos fases
no es opcional:

```
  "¿Está llena la zona?" tiene dos respuestas posibles:

   (a) ¿Está llena AHORA MISMO?          → no mira quién se va    ✗ más restrictivo
   (b) ¿Estará llena cuando termine el turno?  → sí lo mira        ✔ lo que dice §VII.3
```

El subject es explícito: **(b)**. Y la diferencia no es un detalle, son turnos:

```
  Mapa:  start ── w1 ── w2 ── goal      (todas max_drones=1)
  2 drones.

Regla (a) — ignorar que las salidas liberan:
                 T1: D1→w1        T2: D1→w2, D2 espera
                 T3: D2→w1        T4: D2→w2        T5: D2→goal                = 5 turnos
   Regla (b) — §VII.3 real:
                 T1: D1→w1        T2: D1→w2, D2→w1
                 T3: D2→w2 (D1 ya salió)  T4: D2→goal                          = 4 turnos
```

El mapa `easy/01_linear_path` tiene objetivo **≤ 6 turnos** (§VII.7) y 4 es lo
correcto con la regla del subject. Con la regla (a) se llega igual (5 < 6), así que
el benchmark **no te delata**. En mapas con cuello de botella la diferencia sí es
notable. Otro motivo por el que ningún benchmark del repo te salva de un error de
scheduling: te salva del error de **parsing** (§4 de `act.md`).

### 5.3 La excepción de `start` y `end`

**[S] §VII.2:**

> The only special exceptions to occupancy rules are:
> - The **start** zone: all drones begin here and may share the space initially.
> - The **end** zone: multiple drones can arrive here and are considered delivered.

Consecuencias que ya están en el código y que conviene tener presentes al validar
un movimiento:

| Zona | Capacidad | En el simulador significa |
|---|---|---|
| `start` | ∞ | Todos nacen ahí; y si alguno vuelve, cabe |
| `end` | ∞ | Todos los drones se acumulan al final; nunca hay cola ahí |

> ⚠️ **Punto ciego conocido:** `start` no tener límite hace que un dron pueda
> "quedarse en la puerta" sin estorbar a nadie, y `end` no tenerlo hace que la
> última zona nunca sea un cuello de botella. En `hard/03_ultimate_challenge` eso
> cambia el resultado. No es un bug del modelo: es el subject.

---

## 6. `max_link_capacity` — cuántas personas caben en un pasillo

**[S] §VI** (default): `max_link_capacity=<number>` (default: 1).
**[S] §VII.2:** *"Connection capacity (max_link_capacity) defined on connections
limits how many drones can traverse the same connection simultaneously."*

### 6.1 La diferencia con `max_drones`, en una frase

> `max_drones` limita **dónde se está**. `max_link_capacity` limita **por dónde se
> pasa**.

Y de ahí sale la diferencia práctica más importante del proyecto:

```
  Una zona retiene a los drones varios turnos: un dron que está en w1 sigue
  occupying w1 mientras decide, espera o calcula.

  Una conexión solo se ocupa durante el turno del cruce (salvo el tránsito de
  restricted). Terminado el cruce, el pasillo está vacío.
```

Es decir: **el pasillo es un recurso más escaso que la sala**. En la mayoría de los
mapas, `max_link_capacity=1` es la restricción que marca los turnos, no
`max_drones`.

### 6.2 El problema: la lista no representa al cruce **[C]**

`Connection.drones` existe (`models.py:90`) y `have_capacity()` lo lee
(`models.py:103-111`), y `Connection.add_drone` / `remove_drone` ya validan
(`models.py:113-121`). Pero:

```
  Turno 5:  D1 cruza a-b (1 turno)    D2 cruza a-b (1 turno)
  a-b con max_link_capacity=1

  Connection.drones durante el turno:  [D1]  →  have_capacity() = False  ✔
  Connection.drones al terminar:       []     →  have_capacity() = True

  El problema no es durante el turno (bien), sino ENTRE turnos:
  si el scheduler pregunta have_capacity() ANTES de que nadie haya entrado,
  ve [D2] y [D3] y dice "sí, cabe" a los dos.
```

Es el mismo problema del contador por turno, y su causa es que la ocupación de una
conexión es **efímera** (un turno) mientras que la de una zona es **persistente**
(varios turnos). Dos duraciones distintas, un solo atributo.

### 6.3 Tres modelos posibles **[D]**

| Modelo | Cómo | Turnos por turno | Dificultad |
|---|---|---|---|
| **A. Contador por turno** | Al empezar el turno, las conexiones se vacían y se vuelven a llenar con los que cruzan | ✔ correcto | Baja |
| **B. Solo lista de vuelo** | Solo cuentan los drones en tránsito (`restricted`) | ✗ el cruce de 1 turno no cuenta | Nula |
| **C. Tabla de reservas** | `reservas[(turno, conexión)] += 1` al validar | ✔ correcto | Media |
| **D. A + B juntos** | Dos listas: `en_este_turno` y `en_vuelo` | ✔ correcto | Baja |

> El **[B]** es el estado actual y es un **dead state**: `have_capacity()` devuelve
> siempre `True`. La regla §VII.2 está escrita pero no se ejecuta. No es un bug de
> `models.py` — es que le falta el consumidor (`simulation.py`), y ese consumidor tiene
> que decidir cuál de los cuatro modelos quiere.

La decisión está en la lista de preguntas finales. Lo que **no** depende de la decisión
es que el comportamiento del subject es el mismo en los cuatro modelos correctos
(A, C, D): si `max_link_capacity=1`, un dron por turno, siempre.

---

## 7. `zone=restricted` — el caso difícil

Este es el único punto donde "mover" son **dos turnos**, y donde la línea de output
tiene un token distinto.

### 7.1 Por qué cuesta 2 turnos

**[S] §VI:** `restricted` — *"A sensitive or dangerous zone. Movement to this zone
costs 2 turns."*

El nombre del tipo ya lo dice: es una zona **peligrosa**. El coste no es un
arbitrario del enunciado, es la representación de un peligro que obliga a parar en
la conexión antes de entrar. No hace falta inventarse una razón más: el subject lo
define así y punto.

En `pathfinding.py` ese 2 ya se aplica: `ZONE_COSTS[RESTRICTED] = 2`
(`models.py:24`) y `_step_cost` lo usa (`pathfinding.py:22-26`). O sea, **el routing
ya sabe que cuesta 2**; lo que falta es el reloj.

### 7.2 Qué ocurre exactamente **[S]**

Las dos frases que lo definen:

> Move to a connection towards a restricted zone (that requires 2 turns to be
> reached). **In this case, the drone MUST reach its destination during the next
> turn. It can't wait extra turns on the connection.**
>
> For multi-turn movements (restricted zones), the drone occupies the connection
> during transit and **cannot wait on the connection for an empty space** in the
> destination zone.

Turno a turno, con A → B donde B es `restricted`:

```
  turno t      D1 en A                    A.drones = [D1]
               "voy a B"                  → impresión:  D1-B            (§VII.5)

  turno t+1    D1 en la conexión A–B      A.drones = []      ← ¡ya no ocupa A!
               (OBLIGADO a llegar)        conn.drones = [D1]
                                          → impresión:  D1-A-B            (¡el token
                                                                             de la conexión!)

  turno t+2    D1 en B                    B.drones = [D1]
               (llegada obligatoria)      conn.drones = []
                                          → impresión:  D1-B
```

Fíjate en las tres cosas que pasan a la vez en el turno t+1:

1. **D1 sale de A.** Ya no ocupa la sala. La sala se libera **este mismo turno**.
2. **D1 ocupa la conexión.** Por eso `have_capacity()` de `A–B` ahora cuenta a D1.
3. **D1 todavía no está en B.** B tiene que tener el hueco **reservado**, no libre.

### 7.3 Por qué no puede esperar en la conexión

Porque el subject dice literalmente *"cannot wait on the connection for an empty
space"*. Es decir: **si el hueco no existe al salir, no se sale**.

```
  ✗ Lo que NO se puede hacer (turno t+1):

      turno t   : D1 sale de A hacia la conexión, "&gt; ya luego me colaré en B"
      turno t+1 : B sigue llena   →  D1 no puede entrar   →  ✗ prohibido

  ✓ Lo que SÍ se puede hacer (reserva):

      turno t   : se comprueba que B tendrá hueco
                  (contando quién sale de B este mismo turno)
                  → si lo hay, D1 entra en la conexión CON LA PLAZA RESERVADA
      turno t+1 : D1 entra en B. Sin excusas: la reserva es una promesa.
```

La diferencia es una palabra: **reserva**. Y es la razón por la que la validación del
turno no puede ser sólo "mira si cabe ahora":

```
  ┌────────────────────────────────────────────────────────────────┐
  │  Al validar "D1 quiere entrar en B (restricted)", hay que      │
  │  comprobar el hueco de B contra el estado POST-SALIDAS, y ese   │
  │  hueco se CONSUME en el momento de la declaración, no en el    │
  │  momento de la llegada.                                         │
  └────────────────────────────────────────────────────────────────┘
```

O sea: **la fase de validación tiene que consumir la plaza en el destino**, aunque
el dron no llegue hasta dos turnos después. Sin ese consumo previo, la reserva no existe
y dos drones pueden "reservar" la misma plaza.

### 7.4 Cuándo se libera la conexión **[D]**

Aquí el subject es **concreto en una mitad y ambiguo en la otra**:

| Momento | ¿Libera el enlace? | Base |
|---|---|---|
| Al entrar en la conexión (turno t+1) | No, la ocupa | **[S]** "the drone occupies the connection during transit" |
| Al llegar a B (turno t+2) | **Sí**, lógicamente | **[S]** "MUST reach its destination" |
| En el turno en que sale de A hacia la conexión (turno t), ¿ya cuenta para `max_link_capacity`? | **Sin resposta en el subject** | **[D]** |
| En el turno en que llega a B (t+2), ¿el enlace lo cuenta todavía o está libre? | **Sin respuesta en el subject** | **[D]** |

La última fila es la fina. Con `max_link_capacity=1`:

```
  Turno t   : D1 entra en la conexión A–B        ← ¿ocupa el enlace este turno?
  Turno t+1 : D1 llega a B                        ← ¿el enlace está libre este turno,
                                                        o D1 sigue "en" él hasta el final?

  Lectura 1 (ocupa t y t+1):  D2 no puede ni intentar el cruce hasta t+2
  Lectura 2 (ocupa solo t):    D2 puede cruzar el mismo turno t+1 que D1
```

Diferencia observable: un turno por cada `restricted` del camino. En
`medium/02_circular_loop` hay un `restricted` (`exit_point`); en `hard/02` hay tres
seguidos (`restricted_tunnel1..3`). **[D]** Decisión nuestra. Está en las preguntas.

### 7.5 Ejemplo completo: dos drones hacia el mismo `restricted`

```
  Mapa:  start ── r (restricted, max_drones=1) ── goal        2 drones

  Turno 1:  D1: start → conexión start-r     (reserva la plaza en r)
            D2: espera                       (¿start-r está libre este turno? no:
                                             D1 ya lo ocupa mientras dura el vuelo)
  Turno 2:  D1: r            ← llega        (la reserva se cumple)
            D2: espera                       (r vuelve a estar lleno con D1)
  Turno 3:  D1: goal
            D2: start → conexión start-r     (ahora sí, r está libre)
  Turno 4:  D2: r
  Turno 5:  D2: goal

  Turno final = 5
```

Observa el turno 1: D2 **no** puede ni intentar. Y no es una decisión del scheduler,
es la consecuencia de que `max_link_capacity` por defecto es 1 y el dron ocupa el
enlace durante el tránsito.

### 7.6 El invariante durante el tránsito **[D]**

`models.py:137-158` protege:

> `drone in zone.drones` ⟺ `drone.position is zone`

Ese invariante **no se puede mantener** tal cual mientras un dron vuela: no está en
ninguna zona. Hay que redefinirlo, y la redefinición depende de cómo se modele el
tránsito (cap. 08 §7.4):

> **Redefinición [D]:** si `position` es una `Zone`, el dron está en
> `position.drones`. Si `position` es una `Connection`, el dron está en
> `position.drones` y en **ninguna** zona.

Si se elige la opción B (campo `transit` aparte), el invariante se queda **intacto**,
que es un argumento a favor de B. Si se elige A, hay que documentar la redefinición en
el docstring de `move_to`, o el revisor la encuentra él.

---

## 8. Catálogo de conflictos

Cinco conflictos, con su detección y su resolución. Todos salvo el último son
**[S]**: se resuelven preguntando a los objetos.

### 8.1 Dos drones quieren la misma plaza (sobre-demanda)

```
  Mapa:  start ── j (max_drones=1) ── goal       2 drones

  Turno 1:  D1: start → j      ✔
            D2: start → j      ✗ no cabe          (sobre-demanda: 2 piden, 1 hay)
```

**Qué NO decide el subject**: cuál de los dos se lleva la plaza. **[D]** Es la
decisión más importante de scheduling. Pero el sujeto sí dice que no puede pasar esto:

> *"A valid simulation must: comply with all movement and occupancy rules... Avoid
> all conflicts (e.g., exceeding zone or connection capacity)."* — §VII.6

Es decir: **perder una plaza es legítimo, violar la capacidad no**. Eso es lo que
justifica "esperar" como respuesta.

### 8.2 Zona llena

```
  Turno 3:  D2 quiere entrar en w1. w1 tiene 1 dron y max_drones=1.
            → no cabe. D2 espera.          (sub-demanda o sobre-demanda, da igual)
```

Detección: **`Zone.can_accept_drone()`** (`models.py:52`) **sobre el estado
post-salidas**, no sobre el actual (§4.1).

### 8.3 Conexión llena

```
  Turno 5:  D2 y D3 quieren cruzar a-b (max_link_capacity=1)
            → uno entra, el otro espera.
```

Detección: `have_capacity()` **más** el modelo de §6.3, que es **[D]**.

### 8.4 Varios drones por el mismo camino

Esto **no** es un conflicto: es la norma. En un mapa con una sola ruta, los N drones
van en fila y la zona intermedia se convierte en una cola.

```
  Mapa:  start ── w1 ── w2 ── goal      max_drones=1 en todo

  Turno 1: D1 → w1
  Turno 2: D1 → w2    D2 → w1          (w1 liberada en el mismo turno)
  Turno 3: D1 → goal  D2 → w2
  Turno 4:           D2 → goal

  Los 4 turnos los marca w1 y w2, no la longitud del camino.
```

Eso es el **cuello de botella** (cap. 10 §8) y es el motivo por el que §VII.1 dice
*"Distribution of drones across multiple paths"*: si hay dos caminos, repartir salva.

### 8.5 Espera en cascada

```
  Turno 2: D3 espera porque w1 está lleno.
  Turno 3: D3 espera porque w1 sigue lleno (D2 entró).
  Turno 4: D3 espera porque ahora está lleno D3...
```

La espera no es un estado terminal: es una **cola**. Y una cola es exactamente lo que
se forma cuando un cuello de botella tiene capacidad 1. Distinguir "espera porque no
puede" de "espera porque el scheduler decidió" es una de las cosas que hay que poder
explicar.

### 8.6 Los cuatro conflictos en una tabla

| Conflicto | Lo detecta | Quién lo resuelve | Regla |
|---|---|---|---|
| Zona llena | `Zone.can_accept_drone` | el modelo | **[S]** |
| Conexión llena | `Connection.have_capacity` | el modelo + modelo §6.3 | **[S]** / **[D]** |
| Sobre-demanda por una plaza | ninguno: **es legal** | el scheduler | **[D]** |
| Intercambio / rotación | nada que detectar | el scheduler | **[D]** |
| Nadie puede moverse | — | detección de no-progreso | **[D]** |

---

## 9. Deadlocks

### 9.1 Qué es **[S]**

§VII.1 lo nombra: *"Avoidance of path conflicts and deadlocks"*. La definición
clásica es un ciclo de esperas:

```
  D1 quiere w2, que tiene D2
  D2 quiere w1, que tiene D1
  D1 espera a que D2 se mueva
  D2 espera a que D1 se mueva
  → nadie se mueve nunca
```

En este proyecto el caso real **no es** el deadlock circular: las conexiones son
bidireccionales y `blocked` no se puede atravesar, así que un ciclo de espera "puro"
es raro. El caso real es otro:

### 9.2 El deadlock real: el atasco permanente **[C] + [D]**

```
  Mapa:  start ── w1 (max_drones=1) ── w2 (max_drones=1) ── goal
         y una zona muerta:  start ── dead_end

  Todos los drones quieren w1. w1 tiene un dron esperando decidir.
  El que está en w1 quiere w2. w2 tiene un dron. ...
  Con max_drones=1, en cada turno solo uno puede avanzar y el resto espera.
```

Cuando eso **no** avanza, no hay ciclo: hay **congelación**. Y el congelamiento
provocado por scheduling tiene dos fuentes conocidas:

| Fuente | Síntoma |
|---|---|
| **Prioridad fija** | Los drones con menor prioridad nunca se mueven porque los de mayor prioridad los relevan siempre |
| **Auto-bloqueo** | El dron que ocupa el cuello de botella no tiene permiso para moverse hasta que se libere un sitio que él mismo bloquea |

### 9.3 El antídoto mínimo: el tope de no-progreso **[D]**

**[S] §III.1** dice que *"If your program crashes due to unhandled exceptions during
the review, it will be considered non-functional"*, y un bucle infinito es, para
efectos prácticos, un crash: el revisor espera y el programa no termina.

```
  while not is_finished():
      tokens = step()
      if not tokens:                  ← NINGÚN dron se movió este turno
          raise SimulationStuck()     ← "error: ..." + exit != 0
      emit(tokens)
```

Es una línea y convierte un cuelgue infinito en un error claro. **No** es una decisión
de diseño: es la diferencia entre "no funcional" y "un error que se puede explicar en
30 segundos". Y detecta también el caso "un dron sin ruta se quedó quieto para
siempre" (`PathFinder.shortest_path` devuelve `None`, `pathfinding.py:79`).

### 9.4 Los antídotos de verdad

Los serious están en el cap. 10 (scheduling) porque son estrategias, no reglas:

| Antídoto | Qué hace | Dónde |
|---|---|---|
| **Tope de no-progreso** | Detecta el atasco y aborta limpio | simulación, §D-7 |
| **Reservas** | Un dron no entra si no puede **terminar** su movimiento | validación |
| **Antigüedad (aging)** | Un dron que lleva k turnos esperando sube de prioridad | scheduler |
| **Reparto de rutas** | Los cuellos de botella se reparten en varios caminos | scheduler |

---

## 10. Finalización

### 10.1 Cuándo termina **[S]**

§VII.5, literal:

> - Drones that reach the end zone are considered delivered and are no longer tracked.
> - **The simulation ends when all drones have reached the end zone.**

Es decir: **`n_entregados == nb_drones`**. Y nada más.

### 10.2 La condición, en las tres representaciones

| Representación (§8.1) | `is_finished()` |
|---|---|
| Lista activa | `len(self.drones) == 0` |
| Lista de entregados | `len(self.delivered) == self.graph.nb_drones` |
| Marca en el dron | `all(d.delivered for d in self.drones)` |

Todas son **[D]**. Todas cumplen.

### 10.3 El turno en que llega el último

Un detalle de output que suele confundir:

```
  Turno 4:  D1-goal  D2-goal
  ─────────────────────────
  Fin. 4 turnos.  Turno en que se entregó el ÚLTIMO dron = 4.  Makespan = 4.
```

El "número de turnos" que se puntúa (§VII.6) es el **makespan**: el turno del último
dron. No "número de líneas con movimiento" + 1, no "turnos hasta que la mayoría llegó".

> **[D]** Para que eso sea medible, el dron tiene que **dejar de moverse en el mismo
> turno en que entra en `end`**. Si al llegar a `end` "apareciera" y en el turno
> siguiente desapareciera, el makespan sería un turno más alto. Es un detalle, pero
> es un turno.

### 10.4 Lo que NO termina la simulación

| Situación | ¿Fin? |
|---|---|
| Todos en `end` | ✔ **[S]** |
| Un dron sin ruta (`None`) | ✘ → tope de no-progreso (§9.3) → `error:` |
| Turno sin movimiento | ✘ → igual que el caso anterior: tope de no-progreso |
| El mapa tiene una zona aislada | ✘ (el dron que no puede salir se queda quieto) |
| `end` es `blocked` | ✘ → `add_drone` lanza → `ValueError` (§III.1 lo cuenta como bug de programador) |

El último caso merece atención: `shortest_path` devuelve `None` cuando `end` es
`blocked` (`pathfinding.py:65-66`, y `ask&ques.md` C15), así que el dron se quedaría
esperando para siempre y el tope de no-progreso lo convertiría en un error claro. Es
un final defendible.

---

## 11. Requisitos del subject vs. nuestras decisiones

### 11.1 Lo que el subject obliga **[S]**

| # | Regla | §del subject |
|---|---|---|
| 1 | Turno entero, tres verbos | §VII.3 |
| 2 | Dos fases: validar contra el estado post-salidas | §VII.3 |
| 3 | `blocked` no se entra | §VI, §VII.3 |
| 4 | `normal`/`priority` = 1 turno | §VI |
| 5 | `restricted` = 2 turnos, sin esperar en el enlace | §VI, §VII.3 |
| 6 | `max_drones` = 1 por defecto | §VI, §VII.2 |
| 7 | `max_link_capacity` = 1 por defecto | §VI, §VII.2 |
| 8 | `start` y `end` sin límite | §VII.2 |
| 9 | No esperar en la conexión para esperar sitio en el destino | §VII.3 |
| 10 | Terminar cuando todos hayan llegado | §VII.5 |
| 11 | Drones quietos omitidos del output | §VII.5 |
| 12 | Sin deadlocks / conflictos | §VII.1, §VII.6 |
| 13 | Sin excepción no capturada | §III.1 |

### 11.2 Lo que decidimos nosotros **[D]**

| # | Decisión | Cap. |
|---|---|---|
| 1 | Cómo se representa el dron en tránsito | 08 §7.4 |
| 2 | Modelo de la capacidad del enlace (4 opciones) | §6.3 |
| 3 | En qué turno se libera/cuenta la conexión | §7.4 |
| 4 | Quién gana una plaza sobre-demandada | §8.1 |
| 5 | Cuándo espera un dron por decisión propia | §3.1 |
| 6 | Forma del turno (`Turn.validate` vs fase 1/2 en `step`) | 08 §5 |
| 7 | Dron sin ruta | §10.4 |
| 8 | Detección de no-progreso | §9.3 |
| 9 | `Drone.target`: usarlo, llenarlo o borrarlo | 08 §7.5 |
| 10 | Representación de "entregado" (3 opciones) | 08 §8.1 |
| 11 | Ruta estática vs replanificación | 10 |
| 12 | Reparto de rutas | 10 |

---

## 12. Errores que verás antes de entenderlo

Los cinco que van a aparecer mientras escribes, y por qué no son bugs:

| Síntoma | Por qué pasa | Dónde está resuelto |
|---|---|---|
| `ValueError: Drone D3 is not in waypoint2` | Se llamó a `move_to` sin `add_drone` previo | §2.1 |
| `have_capacity()` siempre `True` | Nadie puebla `Connection.drones` | §6.2 |
| Dos drones en la misma zona "a la vez" | Se aplicó la regla (a) de §5.2, no la (b) | §5.2 |
| La simulación se cuelga | Un dron sin ruta se quedó esperando | §9.3 |
| El output está desfasado un turno | El dron aparece en `end` un turno tarde | §10.3 |

---

## 13. Verificación al terminar

1. Saber explicar por qué el turno tiene dos fases citando a §VII.3, no por gusto.
2. Saber explicar la diferencia entre `max_drones` y `max_link_capacity` con un
   ejemplo donde dan números distintos.
3. Saber explicar por qué la plaza de un `restricted` tiene que **reservarse al
   salir** y no al llegar.
4. Saber decir en qué momento se libera la conexión, y reconocer que el subject no
   lo dice en uno de los casos.
5. Saber decir cuándo acaba la simulación, y qué tres cosas pasan cuando acaba.
6. Tener una respuesta para *"¿qué pasa si dos drones quieren la misma zona?"* que
   incluya: **esperar es legal, violar la capacidad no**.
7. Saber que `Connection.drones` **no** modela el cruce de un turno, y qué modelo
   alternativo hay.