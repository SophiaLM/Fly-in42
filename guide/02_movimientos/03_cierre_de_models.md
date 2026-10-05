# 07. Lo que falta por escribir en `models.py`

Los pasos 01 a 04 dejaron `models.py` casi entero: las cuatro clases del dominio ya
existen y ya exponen comportamiento. Falta **cerrar una sola clase**, `Connection`,
a la que le quedan dos piezas que la simulación va a necesitar. Este paso se ocupa
solo de eso: de escribir, **dentro del modelo**, lo que todavía no está.

El reparto de responsabilidades es el que ya conoces (`00_primer_movimiento.md` §1):
el modelo expone **si algo es posible** (`can_accept_drone`, `have_capacity`) y
**cómo se ejecuta** (`add_drone`, `move_to`); decidir **cuándo** se ejecuta —turnos,
scheduling— es de `simulation.py`. Las dos piezas de este paso son "cómo se
ejecuta", por eso viven aquí y no en la simulación.

---

## 1. Punto de partida

`Zone` está completa: sabe si cabe un dron (`can_accept_drone`), meterlo
(`add_drone`) y sacarlo (`remove_drone`). `Connection` se quedó a medias: sabe
**preguntar** si tiene hueco (`have_capacity`), pero no tiene forma de **poblarse**
ni de **nombrarse**.

| | Tiene hoy | Le falta |
|---|---|---|
| Poblarse | `drones: list[Drone]`, `have_capacity()` | `add_drone` / `remove_drone` |
| Nombrarse | `a`, `b`, `other_zone()` | `label` |

Las dos piezas que faltan ya estaban **diseñadas** en el paso 04
(`00_primer_movimiento.md:31`): ahí se dijo que `Connection` necesitaría métodos
`add_drone`/`remove_drone` simétricos a los de `Zone`, y que la simulación
necesitaría el token de §VII.5. Este paso solo las ejecuta.

---

## 2. Pieza 1 — `Connection.add_drone` / `remove_drone`

### Qué falta y por qué importa

`have_capacity()` lee `self.drones`, pero **nadie llena esa lista**: no hay puerta de
entrada ni de salida. Por eso devuelve `True` siempre y `max_link_capacity` no se
aplica nunca. Es el único mecanismo de §VII.2 que sigue muerto, y el fallo es
silencioso: con un solo dron nadie choca, así que no se nota.

La lista existe para poder **contar cuántos drones están en tránsito** por el enlace.
Si nunca se llena, el contador no cuenta nada.

### Cómo escribirlos

Simétricos a los de `Zone`: misma forma, distinto predicado.

- `Zone.add_drone` valida `can_accept_drone()`, que incluye la regla de `BLOCKED` y
  `max_drones`.
- `Connection.add_drone` valida `have_capacity()`: `len(self.drones) < self.max_link_capacity`.

`remove_drone` es el mismo en las dos: `list.remove`, que quita la primera
coincidencia y lanza `ValueError` si el dron no estaba.

Que la mecánica se repita (`append`, `list.remove`, `ValueError` si no cabe) no es
duplicación: lo que cambia es la **regla**. Es exactamente la razón de que `Zone` y
`Connection` sean dos clases: comparten la forma, no la condición.

Esto es coherente con la idea que ya sigue el proyecto (tell, don't ask): no
preguntas a la conexión "¿cabe?" para luego mutar la lista tú mismo; le pides que
meta al dron y es ella la que valida y decide.

### Por qué `Connection` necesita lista propia

No puede reutilizar la de una zona, porque la ocupación de un enlace es un estado
más. En un movimiento hacia una zona `restricted` el dron pasa un turno entero
**dentro del enlace**, sin estar en la zona de origen ni en la de destino
(`sobre_mi_pryecto.md` §5.2). El invariante de ocupación del paso 04 habla de una
zona a la vez; este tercer estado no cabe en ninguna, así que necesita su propia
lista.

### Qué NO se decide aquí

Cómo se modela esa capacidad —contador que se reinicia cada turno, lista de vuelo o
tabla de reservas— es una decisión de `simulation.py`, no del modelo. Los métodos
son iguales en los tres casos, así que se pueden escribir ahora sin bloquear nada.

### Cómo comprobar que quedó bien

Con una conexión de `max_link_capacity=1`:

```
have_capacity()   →  True
add_drone(d1)     →  have_capacity()  →  False
remove_drone(d1)  →  have_capacity()  →  True
```

Y que `remove_drone` de un dron que no está lanza `ValueError`, igual que en `Zone`.

---

## 3. Pieza 2 — `Connection.label`

### Qué falta y por qué importa

§VII.5 obliga a imprimir cada movimiento como `D<ID>-<zone>` y, cuando el dron está
en vuelo, `D<ID>-<connection>`. El segundo token necesita un **nombre para la
conexión**, y `Connection` no lo tiene. Sin él no se puede construir el token:
`f"{drone.name}-{???}"` no compila.

### Cómo escribirlo

Una propiedad `label` que devuelva los dos nombres de zona unidos por `-`:

```python
@property
def label(self) -> str:
    ...
```

El parser ya prohíbe los `-` en los nombres de zona (`builders.py:28-31`), así que
el token `a-b` no es ambiguo: no se puede confundir con un nombre de zona ni con
`a-b-c`.

### La decisión del formato

Los mapas escriben cada conexión en un orden concreto, y **no es el alfabético**: 61
de las 180 líneas `connection:` van al revés (`waypoint2-goal`, `start-junction`…).
Por eso las dos opciones no dan el mismo resultado:

| Opción | Formato | Coincide con el fichero del mapa |
|---|---|---|
| **Orden natural** | `f"{self.a.name}-{self.b.name}"`, tal cual los guardó el parser | **180 de 180** |
| **Orden alfabético** | `"-".join(sorted((self.a.name, self.b.name)))` | 119 de 180 |

El orden natural hace que el token sea **literalmente** la línea del mapa: quien lee
el token encuentra el mismo texto en el fichero. El alfabético da un nombre canónico
(el mismo desde los dos lados del enlace), útil solo si alguna vez hay que comparar
o agrupar etiquetas.

La decisión se puede tomar ahora o al escribir el `print`; el atributo se escribe
igual en los dos casos. Lo único que conviene fijar es el criterio:

- Si el token se compara **contra el fichero del mapa** → orden natural.
- Si el token se usa como **clave o para agrupar** → orden alfabético.

### Qué NO se decide aquí

Dónde se imprime el token y el formato final de la línea de salida son del paso de
§VII.5, no del modelo. Aquí solo se deja el nombre disponible.

### Cómo comprobar que quedó bien

Imprimir el `label` de todas las conexiones de un mapa y compararlo con las líneas
`connection:` del fichero: con orden natural coinciden todas; con orden alfabético,
el mismo enlace da el mismo nombre desde los dos extremos.

---

## 4. Lo que NO entra en este paso

- **El ensanchado de `Drone.position`** a `Zone | Connection`. Es un cambio en
  `models.py`, sí, pero depende de cómo se modele el tránsito, que es una decisión
  de la simulación. No es cerrar la base: es abrir el tránsito.
- **El turno de dos fases**, la reserva del hueco de destino, el scheduling y el
  `print` de los tokens. Todo eso es `simulation.py`.
- **El resto de la API**: `Zone`, `Drone` y `Graph` ya estaban cerrados en los pasos
  anteriores. Aquí solo se añaden dos piezas a `Connection`.

---

## 5. Verificación al terminar

1. `make lint` en verde (los métodos nuevos con su docstring PEP 257, como el
   resto).
2. Los 10 mapas siguen parseando.
3. La prueba manual de capacidad de §2: `True` → `add_drone` → `False` →
   `remove_drone` → `True`.

---

## 6. Y ahora, ¿qué sigue?

Con esto el **routing** está cerrado: cada dron sabe qué ruta es la más barata por
zona. Lo que falta es la otra mitad del problema, y no es "más código" sino otro
problema distinto:

```
   Ruta (routing)          vs.   Momento (scheduling)
   ───────────────               ──────────────────────
   ¿por dónde?                      ¿cuándo?
   Dijkstra                         el bucle de turnos
   función pura                     depende del estado
   cacheable                        caduca cada turno
```

El paso siguiente es el bloque de simulación, que empieza por
**[08 · Simulación discreta](../03_simulation/01_discretizacion.md)**: qué es un
estado, qué es un turno, y por qué el dron en tránsito rompe el invariante de
ocupación que este mismo capítulo cerró.

Y la advertencia que hay que tener presente al entrar ahí: el capítulo
**[10 · Scheduling](../03_simulation/03_scheduling.md)** contiene **decisiones que
todavía no están tomadas** (reparto de rutas, prioridad, desempate). El diseño de la
simulación depende de ellas, así que conviene leerlo **antes** de escribir
`simulation.py`, no después.
