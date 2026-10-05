# 11. Output y visualización: cómo se ve la simulación

Los capítulos 08, 09 y 10 deciden **qué pasa**. Este decide **cómo se cuenta**. Y
aunque parece la parte fácil, es donde se concentran tres de los requisitos
**obligatorios** del subject: el formato de salida (§VII.5), los colores (§VI) y las
métricas (§VII.6).

La diferencia con todo lo anterior: aquí casi todo está **cerrado**. Quedan dos o tres
decisiones **[D]** y ninguna afecta al diseño del scheduler. Por eso este capítulo es
el más corto de los tres.

---

## 1. El formato de salida es literal **[S]**

**[S] §VII.5**, las siete reglas:

> - Each simulation turn is represented by a line.
> - A line must list all the drone movements that occur during that turn,
>   space-separated.
> - Each movement must follow the format: `D<ID>-<zone>`, or `D<ID>-<connection>` in
>   case of drones still in flight toward restricted zones.
> - Drones that do not move in a given turn are omitted from that line.
> - Drones that reach the end zone are considered delivered and are no longer tracked.
> - The simulation ends when all drones have reached the end zone.

Y el ejemplo que da el subject:

```
D1-roof1 D2-corridorA
D1-roof2 D2-tunnelB
D1-goal D2-goal
```

### 1.1 Lo que se deduce de esas siete frases

| Frase | Consecuencia de diseño |
|---|---|
| "Each turn is a line" | **Una** línea por turno, sin más. No hay líneas de encabezado ni separadores |
| "space-separated" | Separador es **un espacio**, nada de `,` ni `;` |
| `D<ID>-<zone>` | El destino, **no** el origen. `D1-goal`, nunca `start-D1` |
| `D<ID>-<connection>` | Solo para drones **en vuelo** hacia `restricted` |
| "Drones that do not move... are omitted" | **No** se imprimen los que esperan. Una línea vacía es legal |
| "no longer tracked" | El dron entregado **desaparece**, y no vuelve a aparecer |
| "ends when all... reached" | La última línea es la del turno en que llega el **último** |

### 1.2 El destino, no el origen

Este es el error más fácil de cometer y el más visible en el peer review. La línea
`D1-waypoint1` significa "D1 ha acabado en `waypoint1`". Es una línea de **destino**.

```
   Estado t     Estado t+1

   D1 en start   D1 en w1   ──▶  la línea dice:  D1-w1
                            ──▶  NO dice:  start-D1     ✘
```

La razón de fondo: es lo que hace que la salida sea **compacta**. Si se escribiera el
origen, `D1-start` en el turno 1 sería información que ya se sabe (todos empiezan
así), y el formato "D1-a-b" necesitaría guiones extra. Con destino, cada token es
justo un cambio de posición.

### 1.3 Una línea por turno, incluso vacía

Si en el turno 5 nadie se mueve, la línea del turno 5 es una línea vacía. No se salta:

```
turno 3:  D1-w2 D2-w1
turno 4:  D1-goal D2-w2
turno 5:  D2-goal
turno 6:                              ← vacía. No se imprime
```

Aquí hay un matiz que conviene tener claro **[D]**: **si** se llega al turno 6, la
simulación **ya debería haber terminado** en el 5 (todos entregados). Una línea vacía
solo aparece si alguien sigue esperando, lo que por §9 del cap. 09 significa que hay
un dron bloqueado → y entonces el bucle no debería continuar. Así que en la práctica,
una línea vacía **no debería existir nunca** en una simulación que termina bien. Si
aparece, es un síntoma, no un caso normal.

> 💡 **Por qué importa distinction:** un revisor que ve una línea vacía no sabe si es
> "nadie se movió" o "el programa imprimió un hueco por un bug". Como el subject no
> pide líneas vacías y una simulación terminada no las produce, **lo más limpio es no
> emitirlas** y tratar el turno sin progreso como final. Eso es lo que pasa en §5.

### 1.4 El formato del dron en vuelo **[S] + [D]**

El subject dice `D<ID>-<connection>` para los drones en vuelo hacia `restricted`. Pero
**no dice cuál de las dos conexiones** ni con qué formato exacto. Y aquí aparece el
problema: una conexión no tiene nombre propio en el mapa.

```
   Mapa:    connection: corridorA-tunnelB

   Subject: D1-<connection>
   Pregunta: ¿<connection> es "corridorA-tunnelB" o "tunnelB" o "1"?
```

**[C] Dato útil: `Connection.label` ya existe** (`models.py:123-126`):

```python
@property
def label(self) -> str:
    """Etiqueta de la conexion: "A-B" con los nombres de las zonas."""
    return f"{self.a.name}-{self.b.name}"
```

Así que la decisión es casi forzada: **usar `connection.label`**, que produce
`corridorA-tunnelB` exactamente como se escribe en el fichero del mapa. Es la opción
más fiel y ya está implementada, lo que es una victoria.

⚠️ **La trampa:** el resultado es `D1-corridorA-tunnelB`, con **dos guiones**. Choca
visualmente con el `D<ID>-<zone>` de un solo guion. Dos mitigaciones posibles, ambas
**[D]**:

| Opción | Ejemplo | Ventaja | Inconveniente |
|---|---|---|---|
| **A. Tal cual** | `D1-corridorA-tunnelB` | Literal, sin inventar nada | Ambiguo de leer |
| **B. Separador visible** | `D1-corridorA->tunnelB` | Se distingue el rango de un vistazo | Ya no es el formato del subject |
| **C. Sin cambios + leyenda** | `D1-corridorA-tunnelB` + una nota al principio | Formato intacto y se explica | La nota es ruido en el output |

**Recomendación:** A, y si molesta, C. La razón es que el formato del subject es
`D<ID>-<connection>` donde `<connection>` es el nombre de la conexión, y el nombre de
la conexión en el fichero es `corridorA-tunnelB`. Inventar un separador nuevo es
justo el tipo de decisión que un revisor señala como "no era del enunciado".

### 1.5 Los drones que esperan no se imprimen **[S]**

Es explícito: *"Drones that do not move in a given turn are omitted from that line."*
Un dron quieto no aparece, y **no** hay forma de distinguir "esperando" de "todavía no
existe" en la salida. Eso está bien, y hay que entender por qué:

```
   Turno 1:  D1-w1                        ← D2 no aparece: existe pero espera
   Turno 2:  D1-w2 D2-w1                  ← D2 ya se mueve
```

El output es una lista de **sucesos**, no un **estado**. Es el mismo principio que §9
del cap. 08: el estado y el historial son cosas distintas.

**Consecuencia para el capítulo 10:** el output **no permite depurar el scheduling**.
Si dos drones compiten por una plaza y uno pierde, en el output solo se ve que uno se
movió y el otro no aparece. Para ver *por qué* hay que instrumentar aparte (o leer el
estado). Es un recordatorio útil: el output del subject es para el **revisor**, no para
quien depura.

---

## 2. Los colores: obligatorios, pero el subject no dice cómo **[S] + [D]**

**[S] §VI**, dos requisitos:

> - Colors are optional and can be used for visual representation (terminal output or
>   graphical display).
> - When colors are specified, the implementation should provide visual feedback through
>   colored terminal output or graphical representation.

El mapa trae colores por zona, y el parser ya los lee **[C]**:

```
   hub: gate1 1 0 [color=orange max_drones=1]
                 └──────┬──────┘
                        └── Zone.color (models.py:49), opcional
```

### 2.1 El problema: `color=orange` no es un color ANSI

El dato del mapa es un **nombre de color en HTML/CSS**. El terminal espera **códigos
ANSI**. No hay traducción automática:

```
   El mapa dice:  color=orange
   El terminal necesita:  \x1b[38;5;208m   (o 31m para rojo)
   ¿Quién traduce?   →  una tabla, y es decisión nuestra
```

**No hay que inventar nada raro**, pero sí hace falta un mapa:

| Color del mapa | ANSI (foreground) | Notas |
|---|---|---|
| `green` | `32` | |
| `blue` | `34` | |
| `yellow` | `33` | |
| `orange` | `38;5;208` | No existe en los 8 colores básicos |
| `red` | `31` | |
| `cyan` | `36` | |
| `purple` | `35` | El subject usa `purple` en `hard/03` |
| `gray`/`grey` | `90` | |

**Y una decisión [D] importante: ¿de qué se pinta?** El mapa colorea **zonas**, y el
output habla de **movimientos**. Tres opciones:

| Opción | Ejemplo | Qué resalta | Conveniente |
|---|---|---|---|
| **A. Colorear el token del movimiento** | `\x1b[34mD1-w1\x1b[0m` | De qué zona salió | Simple, y se parece al ejemplo del subject |
| **B. Colorear el id del dron** | `\x1b[1mD1\x1b[0m-w1` | Qué dron es | Poco útil: los colores son de zona, no de dron |
| **C. Colorear por el tipo de zona** | `normal`→sin color, `restricted`→rojo | Dónde están los peligros | Coherente con `zone=` pero no con `color=` |

**Recomendación: A**, por la razón de que el dato que el mapa da es `color=`, y A es la
que lo usa. Y una regla de seguridad que el peer review va a agradecer:

> **Si `NO_COLOR` está definido, o la salida no es un terminal, no se emiten códigos
> ANSI.** Los colores son decoración; si rompen la legibilidad de un log o de un
> `grep`, son un defecto.

Esto no lo pide el subject, pero es la decisión de la que más se agradece en una revisión
de código real.

### 2.2 Los códigos ANSI son `\x1b[...m` y se reinician con `\x1b[0m`

Un detalle que, si se olvida, mancha **toda** la salida a partir de ese punto:

```
   correcto:   \x1b[32mD1-hall\x1b[0m D2-corridor
               └──── verde ────┘  └── reset ──┘

   roto:       \x1b[32mD1-hall D2-corridor
               └──── verde hasta el final de la terminal ──────┘
```

El reset (`\x1b[0m`) va **siempre** después del texto coloreado. Es el error nº1 de
quien escribe colores a la primera.

---

## 3. Las métricas: obligatorias de mostrar, no de calcular **[S] opcional**

**[S] §VII.6** las llama *no obligatorias pero animadas*:

> The number of drones moved per turn (efficiency of path allocation).
> The average number of turns per drone.
> ...
> These secondary metrics are not mandatory to compute automatically, but learners are
> encouraged to display them in their simulation output or documentation.

Traducción honesta: **no son obligatorias**, pero mostrarlas es casi gratis y es lo que
distingue un trabajo de un trabajo. Y el makespan, que **sí** es obligatorio (es la
métrica principal), cae solo.

### 3.1 Las cuatro cosas que merece la pena mostrar

| Métrica | Cómo se calcula | Coste |
|---|---|---|
| **Turnos totales** (= makespan) | `len(turnos)` | Ya lo tienes: son las líneas que has impreso |
| **Eficiencia** (drones/turno) | `total_movimientos / makespan` | Un contador |
| **Media de turnos por dron** | `suma(turno_de_llegada) / D` | Un contador por dron |
| **Comparación con el objetivo** | El objetivo de §VII.7 del mapa | Una constante |

### 3.2 La cuarta es la que se defense en el peer review

El subject da un objetivo por mapa (§VII.7):

| Mapa | Objetivo |
|---|---|
| `easy/01_linear_path` | ≤ 6 |
| `easy/02_simple_fork` | ≤ 8 |
| `hard/02_capacity_hell` | ≤ 35 |
| `challenger/01_the_impossible_dream` | referencia: 45 |

Mostrar `"10 turns (target ≤ 8)"` convierte un número en una **evaluación**. Y cuando
el objetivo **no** se cumple, mostrarlo igualmente es lo correcto: es información
honesta, y esconderla es lo que se ve mal.

### 3.3 La media de turnos por dron tiene un matiz

`media = total_turnos_de_llegada / nb_drones`. Para el challenger (25 drones, objetivo
45), una media de ~30 con makespan 45 significa "la mayoría va bien, pero hay una cola
final". Esa lectura **apunta directamente al problema del cap. 10**: la cola es un
problema de scheduling, no de routing. La métrica secundaria no es decorativa: es la
herramienta de diagnóstico.

```
   makespan 45, media 30, 25 drones
     → 15 drones tardaron ≤ 30, y el último tardó 45
     → los 15 turnos de retraso están EN UNA COLA
     → mirar el cuello de botella, no las rutas
```

---

## 4. La visualización: qué se puede hacer y qué **[D]**

**[S] §III.2** menciona dos cosas posibles: *"Colored terminal output showing drone
movements and zone states"* y *"graphical representation"*. No exige ninguna de las
dos específicamente; el output de §VII.5 sí es obligatorio.

Hay tres niveles, y cada uno cuesta más que el anterior:

### 4.1 Nivel 0 — Solo el output **[S] obligatorio**

```
D1-w1 D2-junction
D1-path_a D2-path_b
D1-goal D2-goal

3 turns | 6 moves | 2.0 drones/turn | target ≤ 6
```

Es lo mínimo exigido y **cumple el subject**. Todo lo demás es decoración.

### 4.2 Nivel 1 — El mapa en ASCII, una vez **[D]**

Un esquema estático del grafo **antes** de empezar, para que el revisor vea de qué mapa
se trata. Se puede hacer con las coordenadas que el mapa ya trae (`x`, `y`), así que es
directamente derivable del parser **[C]**:

```
   start ── j ── path_a ── goal
             ╲
              ╲ path_b ──╯

   drones: 4   |   j: max 2   |   goal: sin límite
   objetivo: ≤ 8 turnos
```

**Aviso importante:** los mapas tienen coordenadas reales y valores como `-1`, `3`, `7`,
así que un ASCII-art "bonito" sale mal con facilidad. Y `hard/03` tiene 40+ zonas: un
dibujo lineal de eso es ilegible. La opción honesta es **no dibujar el mapa**, o
dibujar solo la **topología** (qué se conecta con qué) sin posiciones.

### 4.3 Nivel 2 — Animación por turno **[D]**

Un estado del mapa después de cada turno, con los drones en su zona. Es lo más
impresionante y lo que más problemas da:

```
   Turno 3
   [start]  ( )
   [junction]  (D1)
   [path_a]  (D2)
   [goal]  (D1→)
```

Tres avisos, todos aprendidos de los mapas reales:

| Aviso | Por qué |
|---|---|
| **Los drones en tránsito no están en ninguna zona** | Un `restricted` en vuelo no aparece en ninguna casilla: hay que dibujarlo "entre" dos zonas |
| **25 drones en un mapa de 54 zonas** | La animación necesita un layout que no existe en los datos del mapa |
| **Un turno puede no mover a nadie** | Y entonces la animación no muestra nada: hay que indicar "sin movimiento" |

Y hay una razón de fondo para el skepticism: **una animación no es verificable**. Un
revisor no puede comprobar nada mirando 45 fotogramas. El output de texto **sí** es
comprobable. Si el tiempo es limitado, el output de texto es la inversión.

### 4.4 Lo que no hay que hacer

| Tentación | Por qué no |
|---|---|
| Un fichero de salida a disco extra | El subject pide salida por pantalla (o eso es lo esperable); un fichero extra es ruido |
| Un formato "bonito" con bordes ASCII | Choca con el formato literal `D<ID>-<zone>` de §VII.5 |
| Animación aunque el output no esté completo | El peor orden posible: lo obligatorio sin hacer y lo decorativo hecho |

---

## 5. La forma del output: imprimir desde `Simulation` o devolverlo **[D]**

Esta es una decisión de arquitectura pequeña pero con consecuencias grandes, y es la
única de este capítulo que de verdad importa.

### 5.1 Las dos opciones

| | **Imprimir desde `Simulation`** | **`step()` devuelve la línea** |
|---|---|---|
| `Simulation.step()` | `None` | `str` (o un objeto `Turn`) |
| Quién imprime | La simulación | `main.py` |
| Testear un turno | Hay que capturar `stdout` | Se compara el `str` devuelto |
| El output se puede guardar | No, ya se perdió | Sí, `lines.append(...)` |
| El output se puede inspeccionar **antes** de imprimir | No | Sí |
| Riesgo | La simulación queda atada al terminal | Nadie imprime si `main` no lo hace |

### 5.2 La razón decisive: testeabilidad **[D]**

Un test que verifica el formato de salida de un turno **no debería capturar
`stdout`**. Con `step()` devolviendo la línea, el test es:

```python
sim = Simulation(graph)
primera = sim.step()
assert primera == "D1-waypoint1"
```

Sin capturar nada, sin comparar "aquí empieza" y "aquí acaba", sin depender de cómo se
formatea el mensaje de error. Y el mismo diseño da el bonus: `main.py` puede recoger
las líneas, decidir si las imprime con color, o las guarda.

**Recomendación: `step()` devuelve el turno, `main.py` imprime.** Es el mismo patrón
"tell, don't ask" que ya se aplicó en `Drone.move_to` (`act.md` §"Dueño del
invariante"), aplicado ahora a la salida.

### 5.3 Y el orden de impresión

Si `step()` devuelve la línea, hay una pregunta sutil: **¿en qué orden van los tokens
dentro de la línea?** El subject no lo dice:

```
   Turno 2:   D1-w2 D2-w1          orden: por id de dron              ← recomendado
   Turno 2:   D2-w1 D1-w2          orden: el que entra primero en su zona
   Turno 2:   D2-w1 D1-w2          orden: el que se mueve primero
```

**[D]**, y la recomendación es **por `id` de dron** (`D1` antes que `D2` antes que
`D10`). Es el único orden que no depende del estado, así que es el único que hace el
output **comparable entre ejecuciones** — que es lo que el cap. 08 §11.1 pide para el
test de determinismo. Con el orden de salida de la simulación, dos ejecuciones del mismo
mapa podrían dar las mismas líneas en distinto orden y el test de determinismo
fallaría sin que hubiera ningún bug de verdad.

Cuidado con `D10`: ordenar por `int(id[1:])` y no por el string, o `D10` sale antes que
`D2`.

---

## 6. Lo que entra en `main.py` **[D]**

Hoy `main.py` hace una cosa (ya verificado):

```
   $ python -m src.main test/maps/easy/01_linear_path.txt
   test/maps/easy/01_linear_path.txt: 2 drones, 4 zones, 3 connections
```

El flujo completo tendrá que ser:

```
   1. parsear el mapa            ← ya hecho, devuelve Graph o lanza MapParseError
   2. crear los drones           ← nb_drones en start
   3. bucle: turn = sim.step()   ← hasta que step() devuelva None
   4. imprimir cada línea
   5. imprimir el resumen (turnos, eficiencia, media, objetivo)
```

Los puntos donde este capítulo **no** decide nada y hay que mirar el cap. 09:

| Punto | Dónde está |
|---|---|
| Qué hacer si un dron no tiene ruta (`None`) | cap. 09 §9.3 |
| Cuándo para el bucle | cap. 09 §10 |
| El tope de turnos | cap. 09 §9.3 |

Y el manejo de errores que **ya está resuelto** **[C]**:

```python
   except MapParseError as exc:      →  print(f"error: {exc}", file=sys.stderr)
   except (OSError, UnicodeDecodeError) →  print(f"error: {exc}", file=sys.stderr)
   return 1
```

Eso ya está bien, y es el patrón que hay que mantener: **`error:` en `stderr`, código de
salida 1**. Es lo que pide §VIII.1 del subject.

---

## 7. Lo que NO entra en este capítulo

- **La lógica de la simulación** → capítulos 08, 09 y 10.
- **Las decisiones de scheduling** → capítulo 10. Este capítulo solo las cuenta.
- **Un parser de argumentos** (varios mapas, flags). El subject no lo pide; `main.py`
  ya toma exactamente un argumento y funciona.
- **Tests de formato.** Van en el capítulo de tests, no aquí.

## 8. Verificación al terminar

1. Saber escribir de memoria la línea de un turno con dos drones en movimiento, y
   saber decir por qué es el **destino** y no el origen.
2. Saber qué se imprime con un dron esperando, y por qué no se imprime.
3. Saber qué imprime un dron en vuelo hacia un `restricted`, y qué formato exacto
   produce `Connection.label`.
4. Saber por qué hay que resetear el color ANSI, y qué pasa si se olvida.
5. Saber decir qué métrica es obligatoria (el makespan) y cuáles no lo son.
6. Saber explicar por qué `step()` debería devolver el turno en vez de imprimirlo.
7. Saber por qué los tokens de una línea se ordenan por id de dron, y qué se rompe si
   no.