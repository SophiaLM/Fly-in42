# 08. Simulación discreta: qué es un estado y qué es un turno

Este capítulo es el primero de `03_simulation/` y no contiene código: contiene el
**vocabulario** que hace falta para poder escribir `simulation.py` con criterio y
defenderlo en el peer review.

La analogía es la de un tablero de ajedrez con piezas que se mueven por turnos. La
analogía **incorrecta** —la que casi todo el mundo empieza con— es la de "un
coche siguiendo una ruta": un GPS te dice por dónde ir, pero no cuándo puedes
acelerar.

Orden del documento:

- §1 por qué existe un motor de simulación y no un bucle de movimientos
- §2 qué es una simulación discreta
- §3 qué es el **estado**
- §4 qué es un **turno**
- §5 cómo evoluciona el estado
- §6 qué significa "mover simultáneamente"
- §7 el estado de **un dron**
- §8 el estado **global** de la simulación
- §9 qué **no** es estado
- §10 el mapa: qué está decidido, qué está abierto
- §11 cómo se prueba una simulación

---

## 0. Cómo leer este capítulo: tres etiquetas

Cada afirmación va etiquetada. Es lo que te va a permitir defender en la revisión
distinguiendo *"esto lo dice el enunciado"* de *"esto lo decidió Fulano porque le
parecía bien"*:

| Etiqueta | Significa |
|---|---|
| **[S]** | **Requisito del subject.** Si no lo cumples, el programa no es válido. No es negociable. |
| **[C]** | **Código que ya existe** en `fly/src/`. No hay que decidirlo, hay que respetarlo. |
| **[D]** | **Decisión nuestra de diseño.** Varias respuestas son defendibles. Habrá que elegir una y justificarla. |

Si en el peer review te preguntan *"¿por qué hiciste X?"*, la respuesta empieza por
decir a cuál de las tres categorías pertenece X. Esa es la diferencia entre una
decisión y un requisito.

---

## 1. Por qué existe un motor de simulación

Ya tienes routing: `PathFinder.shortest_path(start, end)` te dice **por qué zonas**
pasar y cuánto cuesta (`pathfinding.py`). Con eso, un solo dron ya se puede mover a
mano:

```python
ruta = PathFinder(graph).shortest_path(start, goal)
pos = 0
while pos < len(ruta) - 1:
    grafo.move_drone(dron, ruta[pos + 1])
    pos += 1
```

Funciona con **un** dron. En cuanto hay dos, el bucle se rompe por dentro:

- Si mueves a D1 y luego a D2, el resultado depende del **orden** en el que los
  recorriste. Con el mismo mapa y los mismos drones puedes obtener dos estados
  finales distintos.
- Si mueves a todos primero y compruebas después, no puedes: al mover a D1 ya has
  ocupado su sitio y D2 ya no puede entrar, cuando quizá D1 se iba a mover y dejar
  el sitio libre **ese mismo turno**.
- Y si un dron no puede avanzar, hay que decidir **qué hace**: esperar es una
  decisión, no un fallo.

Nada de eso es routing. Eso es **scheduling**: la asignación de turnos. Por eso
existe un módulo aparte.

```
   ¿por dónde?                ¿cuándo?
  ┌──────────────┐           ┌──────────────┐
  │ pathfinding  │  ─ruta─▶ │  simulation  │
  │  (Dijkstra)  │           │  (turno a    │
  │              │           │    turno)    │
  └──────────────┘           └──────────────┘
       §5 y §6 de esta guía      este capítulo
```

> El truco del enunciado (capítulo I) es exactamente este: *la rueda ya existe, pero
> entiende cómo funciona*. `networkx` te daría la ruta; no te daría el scheduling.

---

## 2. Qué es una simulación discreta

**Simulación discreta** = el tiempo no es continuo, es un **contador entero**. El
mundo solo existe en instantes concretos, y entre un instante y el siguiente no
pasa nada que nos interese.

En Fly-in el tiempo es el **turno**, y el turno es un entero que empieza en 1:

```
turno:      0        1        2        3
           (todo    (D1 y     (D1 y     (D1 y
            en       D2        D2        D2
            start)  avanzan)  avanzan)  llegan)
```

Tres propiedades que se siguen de "discreto" y que te van a servir:

| Propiedad | Qué significa aquí | Por qué importa |
|---|---|---|
| El estado solo cambia en los cortes | Entre turno 1 y turno 2 no hay estados intermedios | No hay que preocuparse por el orden *dentro* de un turno... salvo por el movimiento simultáneo (§6) |
| El estado discreto es **completo** | El estado del turno 2 se puede calcular sabiendo solo el del turno 1 | La simulación es una **función**: `estado(t+1) = f(estado(t))` |
| El tiempo es un dato, no una ley física | No hay "turno 3.5" | Se puede guardar, comparar y reproducir |

Que el estado sea completo es la propiedad que hace que la simulación sea
**determinista**: mismos drones + mismo mapa + misma regla → mismos turnos, siempre.
Y el determinismo es lo que hace que un test pueda afirmar *"turno 5: D1 está en
`waypoint2`"* y que eso siga siendo verdad mañana.

### 2.1 La fórmula

```
estado(t+1) = aplicar_todos_los_movimientos(estado(t))
```

Fíjate en el **`todos`**. Es una operación en bloque, no una secuencia. Esa es la
diferencia entre una simulación y un bucle, y es lo quedevelope §6.

---

## 3. Qué es un estado

**Estado** = *toda la información que hace falta para saber qué puede pasar en el
futuro*. Si hay un dato que no está en el estado y aun así influye en lo que va a
pasar después, ese dato está mal colocado: o falta en el estado, o no debería
influir.

Hay dos niveles, y conviene no confundirlos:

| Nivel | Qué es | Ejemplo en Fly-in |
|---|---|---|
| **Estado estático** (topología) | No cambia nunca durante la simulación | Las zonas, las conexiones, los costes, las capacidades declaradas |
| **Estado dinámico** | Cambia en cada turno | Quién está en cada zona, quién va en qué conexión, en qué turno estamos |

El proyecto ya lo tiene separado y esa separación es deliberada
(`sobre_mi_pryecto.md` §2.3):

- **Estático** vive en `Graph` (`models.py:161-216`): `zones`, `connections`, y el
  índice `_adjacency`. Es lo que consume `PathFinder`.
- **Dinámico** vive repartido entre `Zone.drones` (`models.py:50`), `Connection.drones`
  (`models.py:90`) y lo que añada la simulación.

> **[C] Dato importante que ya está resuelto:** la ocupación **no** es una tabla
> nueva que inventario la simulación. Ya está *dentro* de los objetos:
> `zone.drones` y `connection.drones`. La simulación **pregunta** a los objetos, no
> lleva la cuenta por su cuenta. Si inventaras un `dict[str, list[Drone]]` en
> `simulation.py`, tendrías dos fuentes de verdad y se desincronizarían — que es
> exactamente el bug que ya arreglaste una vez en `move_to` (`act.md` §2.1).

---

## 4. Qué es un turno

**Turno** = un corte del tiempo. Durante un turno, cada dron hace **exactamente una**
de estas tres cosas, y nada más:

```
turno t:
  ┌─ dron que avanza  ─▶  se mueve a la zona vecina          (o a la conexión)
  ├─ dron que espera  ─▶  se queda donde está
  └─ dron entregado ─▶  ya no cuenta: sale de la lista activa
```

Las tres son **acciones legítimas**. Un dron que espera no ha fallado: ha decidido
que este turno no puede moverse. Esa distinción importa porque un programa que
trata "esperar" como error se cuelga o aborta en cuanto aparece el primer cuello de
botella.

Y hay un cuarto caso, que **no** es una acción del dron sino una consecuencia de las
reglas: un dron **en tránsito** (mitad de un movimiento a una zona `restricted`,
§9 del capítulo siguiente). Ese dron no está quieto: está viajando.

> **[S] §VII.3 del subject:** *"At each turn, every drone may: move to an adjacent
> connected zone (if capacity allows); move to a connection towards a restricted
> zone...; stay in place."*
>
> Es una lista **cerrada**. No existe "retroceder", "esperar en una zona" con coste, ni
> cualquier otro verbo. Si inventas un cuarto verbo, estás inventando una regla.

### 4.1 Por qué el turno es la unidad y no el dron

Porque las reglas de §VII.3 son **colectivas**, no individuales:

> *"Drones moving out of a zone free up capacity for that same turn."*
> *"A zone must have available capacity for a drone to move into it (**after all
> drones moving out have freed up space**)."*

 Traducción: la regla es *"el turno"*, y el turno es de todos los drones a la vez. No
se puede aplicar dron a dron, porque el resultado dependería del orden. Eso está
demostrado empíricamente en `next.md` §1.2 y es el argumento que mejor se defiende:

```
Mapa:  start ── w1 ── w2 ── goal     (w1 con max_drones=1)
Turno 2: D1 está en w1 y quiere salir. D2 quiere entrar en w1.

  Orden A: primero D1 (saca), luego D2 (mete)   →  [True, True]   w1=1  w2=1
  Orden B: primero D2 (intenta meter), luego D1 →  [False, True]  w1=0  w2=1

  Mismo turno, mismos drones, misma topología → resultado DISTINTO.
```

Un resultado que depende del orden de iteración de un `for` no es una simulación.
Es una moneda al aire. De ahí sale la única decisión estructural de este módulo, y es
**[S]**, no una preferencia:

> **Un turno tiene dos fases.** (1) todos los drones declaran su intención;
> (2) se valida todo contra el estado **después** de aplicar las salidas, y se aplica
> todo a la vez.

---

## 5. Cómo evoluciona el estado

Un turno completo, de principio a fin:

```
  ESTADO t                                            ESTADO t+1
  ─────────                                           ──────────
  D1 en start ─┐
  D2 en start ─┼──▶  FASE 1: intenciones ──┐
  D3 en start ─┘    "D1 → w1"               │
                   "D2 → w1"                ├──▶ FASE 2: resolver ──▶ aplicar
                   "D3 espera"              │      (capacidad,       todo a la vez
                                           │       conexiones)
                                           │
                        ESTADO t INTERMEDIO: nadie se ha movido todavía
```

Lo importante del diagrama es el **estado intermedio**: entre la fase 1 y la fase 2
**nadie se mueve**. Todavía no. Las intenciones son solo declaraciones.

Ese estado intermedio es lo que hace que la regla de §VII.3 sea aplicable:

```
  Al validar "D2 quiere entrar en w1", lo que cuenta no es
      w1 ahora mismo (lleno con D1),  sino
      w1 después de que D1 se vaya      (vacío)          ✔ permitido
```

Sin estado intermedio, "después de que D1 se vaya" no existe como concepto y hay que
simularlo con el orden de iteración. Por eso la fase 1 no es un detalle
implementativo: es **lo que hace que la regla se pueda escribir**.

### 5.1 Las tres preguntas de la fase 2

En este orden, y el orden importa:

| # | Pregunta | Si la respuesta es "no" |
|---|---|---|
| 1 | ¿Existe conexión entre origen y destino? | el dron espera |
| 2 | ¿Cabe en el destino, contando el estado **post-salidas**? | el dron espera |
| 3 | ¿Cabe en la conexión, contando los que ya la usan este turno? | el dron espera |
| 4 | Si varios quieren la **misma** plaza, ¿quién se queda? | ← **decisión nuestra** (§D-1) |

Las tres primeras son **[S]** (o están ya en el código: `find_connection`,
`can_accept_drone`, `have_capacity`). La cuarta es la primera decisión de scheduling
del proyecto, y es la que vertebralá el capítulo de scheduling.

---

## 6. Qué significa "mover simultáneamente"

**[S] §VII.2:** *"Drones may move simultaneously, as long as all capacity
constraints are respected."*

Simultáneo significa que **en un mismo turno, todos los movimientos se ven entre
sí**. Concretamente:

| Cosa | ¿Es simultánea? |
|---|---|
| D1 entra en `w1` mientras D2 sale de `w1` | **Sí.** Y por §VII.3 es legal: la salida de D2 libera el sitio en ese mismo turno |
| D1 entra en `w1` y D3 entra en `w1` (`max_drones=1`) | **No.** Solo uno puede |
| D1 y D2 se intercambian: D1→`w2`, D2→`w1` | **Sí**, y es legal: cada uno entra en la zona que el otro vacía |
| Una cadena entera de rotaciones | **Sí**, en bloque |

El caso del intercambio es el que más cuesta al principio, porque parece un "choque
de cabezas". No lo es: **no están en la misma zona a la vez**. Al final del turno, D1
está en `w2` y D2 en `w1`, y ambos han ocupado una plaza que estaba libre cuando el
turno empezó.

```
   INICIO DEL TURNO              FIN DEL TURNO
   ┌───────────────┐             ┌───────────────┐
   │  w1: [D2]     │  ───────▶   │  w1: [D1]     │   D2 salió, D1 entró
   │  w2: [D1]     │             │  w2: [D2]     │   D1 salió, D2 entró
   └───────────────┘             └───────────────┘
        sin choque: en ningún momento coexisten en la misma zona
```

Y esto **no es una decisión de diseño**, es la lectura literal de §VII.3. Cualquier
sistema que mueva drones de uno en uno y rechace el intercambio por "el sitio estaba ocupado"
está aplicando una regla **más estricta** que el enunciado, y por tanto peor: gasta
turnos de más.

---

## 7. El estado de un dron

¿Qué necesita saber un dron para moverse en cada turno?

### 7.1 Lo que ya tiene **[C]**

```python
class Drone:                          # models.py:129
    def __init__(self, name, position, target):
        self.name: str          # "D1", "D2"...   → identidad y desempate
        self.position: Zone     # dónde estoy ahora  → el siguiente paso sale de aquí
        self.target: Zone       # a dónde voy        # (hoy nadie lo usa: ver §7.4)
```

Con `name` + `position` ya se puede mover un dron. `Graph.move_drone(drone, target)`
(`models.py:192`) solo necesita la posición actual.

### 7.2 Lo que un dron necesita y todavía no tiene **[D]**

Para ir "por su camino", el dron necesita saber **qué paso le toca**. Eso son tres
cosas, y **el subject no las pide**: son diseño nuestro.

| Concepto | Qué es | Dónde viviría |
|---|---|---|
| **Ruta** | La lista de zonas que debe recorrer | `PathFinder` la calcula (`pathfinding.py:69`); el dron necesita una **referencia** |
| **Progreso** | El índice dentro de esa ruta: "me toca la 3 de 7" | En el dron, si cada dron tiene su ruta |
| **Estado** | ¿en zona? ¿en tránsito? ¿entregado? | En el dron, o derivado de `position` |

Fíjate en el detalle de `PathFinder`: devuelve una **copia** de la ruta
(`pathfinding.py:79`, `list(route)`), precisamente porque el consumidor va a
recorrerla. Recorrerla con `route.pop(0)` la dejaría cortada y la siguiente consulta
devolvería una ruta mutilada. Eso está documentado en `ask&ques.md` C9.

### 7.3 Dos formas de asignar la ruta

| Forma | Cómo | Cuándo tiene sentido |
|---|---|---|
| **Ruta por dron** | Cada dron guarda la suya y avanza por ella | Los drones pueden ir por caminos distintos |
| **Ruta compartida** | Una sola ruta para todos, guardada por la simulación | Solo hay un camino, o quieres serializar |

El subject **no dice nada** de esto. §VII.1 dice *"Distribution of drones across
multiple paths"*, lo que implica que la primera opción es válida y que se espera
considerarla. Ver el capítulo de scheduling.

### 7.4 El problema del dron en tránsito

Un dron que entra en una zona `restricted` tarda **2 turnos**, y en el intermedio está
en la conexión, no en ninguna zona. Eso significa que `position` deja de ser siempre
una `Zone`:

```
   turno t      D1 en A                position = A          (una Zone)
   turno t+1    D1 en la conexión A–B  position = ???        (una Connection)
   turno t+2    D1 en B                position = B          (una Zone)
```

Y `Drone.position` está anotado como `Zone` (`models.py:134`). Hay tres formas de
resolverlo, y las tres son defendibles:

| Opción | Cómo | Costo |
|---|---|---|
| **A. Ensanchar el tipo** | `position: Zone \| Connection` | Cada consumidor necesita un `isinstance`; el invariante hay que redefinirlo |
| **B. Campo aparte** | `position: Zone` (el origen) + `transit: Connection \| None` | Dos sitios donde mirar el estado; menos invasiva |
| **C. Solo el contador** | `position: Zone` (el destino, reservado) + `turns_left: int` | Invasiva y confusa: durante el tránsito la zona está ocupada "por alguien que no está" |

Esta decisión está **[D]** y es de las que hay que tomar **antes** de escribir el
turno, porque condiciona el tipo de `position` y por tanto todo lo demás. Está en la
lista de preguntas finales.

### 7.5 `Drone.target`, hoy decorativo

`Drone.target` existe (`models.py:134`) y **nadie lo lee**. Puede sonar inútil, pero
es exactamente el sitio natural donde viviría "mi destino final", que es lo que
permite distinguir "voy por el camino corto" de "me han mandado a `goal` porque soy el
último". **[D]** Decidir si se usa, se rellena, o se elimina.

---

## 8. El estado global de la simulación

¿Qué necesita saber la simulación **entera**, por encima de cada dron?

| Dato | ¿Por qué? | Dónde vive **[C]** |
|---|---|---|
| **Los drones** | Quién existe | La lista que cree la simulación (`nb_drones` en `Graph.nb_drones`, `models.py:172`) |
| **Ocupación de las zonas** | Para validar `max_drones` | **`Zone.drones`** (`models.py:50`) — ya existe, no se duplica |
| **Ocupación de las conexiones** | Para validar `max_link_capacity` | **`Connection.drones`** (`models.py:90`) — ya existe, hoy sin poblar |
| **Turno actual** | Para el output (§VII.5) y las métricas | **[D]** contador en la simulación |
| **Drones entregados** | Para saber cuándo acaba | **[S]** se dejan de rastrear; **[D]** cómo se representa |
| **Turno escrito** | La salida obligatoria | **[D]** `step()` debería devolverlo, no imprimirlo (§10 del cap. 11) |
| **Turnos movidos por turno** | Métrica secundaria de §VII.6 | sale gratis de lo anterior |

### 8.1 "Drones entregados": tres representaciones

| Opción | Cómo | Ventaja | Inconveniente |
|---|---|---|---|
| **A. Lista activa** | `self.drones` solo contiene los que siguen en marcha | `is_finished()` es `not self.drones` | Pierdes el histórico |
| **B. Lista de entregados** | `self.delivered: list[Drone]` | Puedes mostrar cuántos van | Dos listas que mantener |
| **C. Marca en el dron** | `drone.delivered: bool` | El estado está donde el objeto | Un booleano más que mantener |

**[S]** El subject dice (§VII.5): *"Drones that reach the end zone are considered
delivered and are no longer tracked."* Lo que **no** dice es cómo se representa. Las
tres cumplen.

### 8.2 La ocupación de las conexiones: el punto que hay que entender

**[C] Dato verificado:** `Connection.drones` existe y `Connection.have_capacity()`
lo lee (`models.py:103-111`), pero **solo lo pueblan los drones en tránsito**. Un
cruce normal de 1 turno entra y sale del enlace dentro del mismo turno, así que nunca
aparece en esa lista.

```
   Turno 5:  D1 cruza a-b (1 turno)     D2 cruza a-b (1 turno)

   Conexión a-b con max_link_capacity=1

   Lo que Connection.drones ve:   [] []      →  have_capacity() = True, True
   Lo que el subject exige:       ✗  ✗       →  solo 1 dron por turno
```

Es decir: **`max_link_capacity` no se está aplicando**, y no es un bug de
`models.py`: es que la lista que existe solo modela una de las dos cosas que la
regla gobierna ("simultáneamente" incluye también a quien está durmiendo en el
enlace por un `restricted`).

Esto tiene una solución y es **[D]**: o un contador por turno, o una lista de
reservas `(turno, conexión) -> nº`. Está en las preguntas finales.

---

## 9. Qué NO es estado

Tres cosas que parece que deberían estar en el estado y **no** deben:

| No es estado | Por qué |
|---|---|
| La **topología** (`zones`, `connections`, `_adjacency`) | No cambia. Si la metieras en el estado, la simulación se ocuparía de algo que ya es fijo |
| Las **rutas cacheadas** de `PathFinder._cache` | Son una caché del algoritmo, no del mundo. Y por eso `shortest_path` puede ser una función pura |
| El **resultado** (los tokens ya impresos) | Es salida, no entrada. Si el estado guardara lo impreso, no podrías recalcular la simulación desde el principio |

La tercera tiene un nombre bonito: **separar el mundo de su historial**. El estado
es "cómo está el mundo ahora"; el historial es "lo que pasó". Y `[S]` §VII.5 dice que
cada turno **produce** una línea: producir no es *guardar*.

---

## 10. El mapa: qué está decidido, qué está abierto

### 10.1 Cerrado por el subject **[S]**

| Regla | Dónde |
|---|---|
| El turno es discreto y entero | §VII.3 |
| Tres verbos: mover, esperar, y estar en tránsito | §VII.3 |
| `blocked` no se entra nunca | §VI, §VII.3 |
| `normal`/`priority` = 1 turno, `restricted` = 2 | §VI, §VII.3 |
| Salir libera capacidad **en el mismo turno** | §VII.3 |
| Validar contra el estado **post-salidas** → turno de dos fases | §VII.3 |
| `max_drones` por defecto **1** | §VI, §VII.2 |
| `start` y `end` sin límite | §VII.2 |
| Dos drones no entran en la misma zona si no cabe | §VII.2 |
| `max_link_capacity` limita el cruce simultáneo | §VII.2 |
| Entregado = deja de rastrearse | §VII.5 |
| Termina cuando todos han llegado | §VII.5 |
| Salir de `end` no está prohibido explícitamente | — (pero es absurdo; ver cap. 09 §5.3) |

### 10.2 Cerrado por el código **[C]**

| Regla | Dónde |
|---|---|
| Los drones no salen de `end`... **hoy sí pueden** | `can_move` no lo comprueba (`models.py:178`) |
| `add_drone` es la única puerta de entrada a una zona | `models.py:72` |
| Una zona `blocked` devuelve `False` en `can_accept_drone` siempre | `models.py:59` |
| Las claves del grafo son `str` (nombre), ordenables | `sobre_mi_pryecto.md` §B8 |
| Las capacidades por defecto las pone el parser, no los modelos | `builders.py:38-47`, `:90-94` |

### 10.3 Abierto, y por tanto se decide **[D]**

| # | Decisión | Bloquea a |
|---|---|---|
| 1 | Cómo se representa el dron **en tránsito** (§7.4) | El tipo de `position`, el invariante, `validate()` |
| 2 | Cómo se modela la **capacidad del enlace** (§8.2) | Si `have_capacity()` se puede usar tal cual |
| 3 | **Reparto de rutas**: ¿una para todos o k distintas? | El número de turnos, y el tipo del scheduler |
| 4 | **Quién gana** cuando hay más demanda que oferta en una zona | El resultado de `validate()` |
| 5 | ¿Se **replanifica** cuando el siguiente paso está ocupado? | Si el scheduler es estático o dinámico |
| 6 | Qué hacer con un dron **sin ruta** (`None`) | Si el bucle puede colgarse |
| 7 | Qué hacer si un turno **no mueve a nadie** | Si el programa puede entrar en bucle infinito |
| 8 | La **forma** del turno: ¿objeto `Turn` con `validate()`, o fase 1 y fase 2 dentro de `step()`? | La estructura de `simulation.py` |

Las ocho están desarrolladas en `guide/03_simulation/03_scheduling.md` y son las
preguntas del final de este trabajo. **Ninguna está decidida todavía.**

---

## 11. Cómo se prueba una simulación

Una simulación es un objeto. Los objetos se testean sin imprimir nada. Tres
comprobaciones que no requieren ni una línea de `print`:

### 11.1 Determinismo

```
correr la simulación dos veces con el mismo mapa  →  misma secuencia de turnos
```

No es tautológico: si el resultado depende del orden de un `dict` o de un `set`, dos
ejecuciones pueden diferir. La simulación no debe depender de eso.

### 11.2 El invariante, después de **cada** movimiento

El invariante del proyecto (`models.py:137-158`):

> Un dron está en `zone.drones` **si y solo si** `drone.position is zona`.

Se comprobó 48 movimientos en 4 mapas sin una sola violación (`act.md` §3). Con el
tránsito hay que **redefinirlo**, porque durante el vuelo no está en ninguna zona:

> Si `position` es una `Zone`, el dron está en `position.drones`.
> Si `position` es una `Connection`, el dron está en `position.drones` y en ninguna zona.

Ese invariante redefinido es una **[D]** que viene arrastrada por la decisión 1 de
§10.3.

### 11.3 Ningún dron se pierde

Después de cada turno, la lista de drones debe seguir teniendo el mismo tamaño (salvo
los entregados). Es el test que detecta un `remove_drone` de más o un dron que
"desaparece" al entrar en tránsito.

---

## 12. Lo que NO entra en este capítulo

- **Cómo se validan los movimientos** → capítulo 09 (movimientos y capacidades)
- **Quién se mueve primero y por qué** → capítulo 10 (scheduling)
- **Cómo se escribe o se imprime nada** → capítulo 11 (output y visualización)
- **El código de `simulation.py`** → todavía no. Este capítulo es la teoría; el
  capítulo 10 cierra el diseño; el código viene después.

## 13. Verificación al terminar

1. Saber explicar, sin mirar el enunciado, la diferencia entre estado estático y
   dinámico, y por qué la ocupación no se duplica en la simulación.
2. Saber explicar por qué el turno tiene dos fases **desde el subject** (la cita de
   §VII.3), no desde preferencia propia.
3. Saber decir qué tres cosas le faltan a `Drone` para recorrer una ruta, y que
   ninguna es requisito del subject.
4. Tener una respuesta clara a *"¿qué pasa si un dron no puede moverse?"*: **espera**,
   que es una de las tres acciones del turno, no un error.
5. Saber señalar qué parte de `max_link_capacity` **no se está aplicando hoy** y por
   qué (`ask&ques.md` D19, y §8.2 de este capítulo).