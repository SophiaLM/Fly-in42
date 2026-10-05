# Guía de Fly-in — índice y progresión

Documentación **personal** de este proyecto. No es el enunciado: el enunciado es
[`subject.md`](subject.md) y es la autoridad única cuando hay cualquier duda.

La guía está ordenada como el proyecto se construye, no como el proyecto se lee:

```
   mapas ──▶ parser ──▶ modelos ──▶ pathfinding ──▶ simulación ──▶ output
                                 ╰──────── routing ────────╯
                                      simulación = scheduling
```

## Cómo leer esta guía

| Si quieres… | empieza por |
|---|---|
| Saber qué hay que saber antes de tocar nada | [01 · Conceptos teóricos](00_conocimientos_previos/01_conceptos_teoricos.md) |
| Que `make run` funcione en otra máquina | [02 · Setup y herramientas](00_conocimientos_previos/02_setup_y_herramientas.md) |
| Entender el fichero de entrada | [01 · Cómo funcionan los mapas](00_conocimientos_previos/03_how_map_work.md) |
| Saber qué hay ya implementado | [02 · Modelos actuales](01_parsing/02_basic_models.md) |
| Entender el parser que ya está escrito | [03 · Mi parser](01_parsing/03_myparsing.md) |

## El recorrido completo

### Bloque 0 — Antes de codificar

| # | Capítulo | Qué resuelve |
|---|---|---|
| 01 | [Conceptos teóricos](00_conocimientos_previos/01_conceptos_teoricos.md) | Grafos, OOP, tipado y las reglas pedagógicas del proyecto |
| 02 | [Setup y herramientas](00_conocimientos_previos/02_setup_y_herramientas.md) | `Makefile`, `flake8`, `mypy`, venv |
| 01b | [Cómo funcionan los mapas](00_conocimientos_previos/03_how_map_work.md) | El formato de entrada y qué hay que validar |

### Bloque 1 — Parsing ✅ hecho

| # | Capítulo | Qué resuelve |
|---|---|---|
| 02b | [Modelos actuales](01_parsing/02_basic_models.md) | `Zone`, `Connection`, `Drone`, `Graph`, `ZoneType` |
| 03 | [Mi parser](01_parsing/03_myparsing.md) | `parse_map_file()` y los errores claros |

### Bloque 2 — Routing ✅ hecho

Del mapa a la ruta más barata por zona.

| # | Capítulo | Qué resuelve |
|---|---|---|
| 04 | [Primer movimiento](02_movimientos/00_primer_movimiento.md) | Mover un dron de *a* a *b*, y por qué `can_move()` es una pregunta |
| 05 | [Dijkstra](02_movimientos/01_dijkstra.md) | Por qué Dijkstra y no BFS, y el desempate por `priority` |
| 06 | [Completando `pathfinding.py`](02_movimientos/02_pathfinding.md) | `PathFinder`, la caché y el coste `(turnos, preferencia)` |
| 07 | [Lo que falta en `models.py`](02_movimientos/03_cierre_de_models.md) | El invariante de ocupación, `label`, y el cierre del bloque |

### Bloque 3 — Simulación 🔶 en curso

De la ruta más barata al **cuándo** puede cada dron recorrerla. Es el bloque que
contiene **todas** las decisiones de diseño que aún no están tomadas.

| # | Capítulo | Qué resuelve |
|---|---|---|
| 08 | [Simulación discreta](03_simulation/01_discretizacion.md) | Qué es un estado, qué es un turno, y el problema del dron en tránsito |
| 09 | [Movimientos y capacidades](03_simulation/02_movimientos_y_capacidades.md) | **Normativo**: cada regla del subject traducida a código |
| 10 | [Scheduling](03_simulation/03_scheduling.md) | **Las decisiones abiertas**: 10 estrategias comparadas, sin elegir ninguna |
| 11 | [Output y visualización](04_visualization/01_output_y_visualization.md) | El formato literal de §VII.5, los colores y las métricas |

### Bloque 4 — Verificación 🔲 pendiente

Tests, benchmarks y documentación final. Es lo que hace que el resultado sea
defendible, y es lo que §IX del subject exige en el peer review.

## Documentos de referencia

No son capítulos: son material de trabajo que se consulta mientras se lee otro.

| Documento | Qué es |
|---|---|
| [`subject.md`](subject.md) | El enunciado oficial. La autoridad cuando hay conflicto |
| [`next.md`](next.md) | Diagnóstico del estado del proyecto (⚠️ **parcialmente obsoleto**: sus hallazgos de parser/modelos ya están resueltos) |
| [`ask&ques.md`](ask&ques.md) | Compilación de preguntas de peer review, con las respuestas que ya están defendidas |

## El estado real del proyecto

| Pieza | Estado |
|---|---|
| Parser (`fly/src/parser/`) | ✅ Completo, con validación y errores claros |
| Modelos (`fly/src/models.py`) | ✅ Completo: invariante, `label`, capacidades |
| Pathfinding (`fly/src/pathfinding.py`) | ✅ Completo: Dijkstra, `priority`, caché |
| `main.py` | 🟡 Parsea y resume; falta el bucle de simulación |
| `simulation.py` | ⬜ **Vacío** — a escribir después de decidir el scheduling |
| `visualization.py` | ⬜ **Vacío** — y §2 del cap. 11 explica si hace falta |

## Las tres decisiones que bloquean la implementación

Todo lo demás ya está resuelto por el subject o por el código. Esto es lo que queda,
y está desarrollado en el [capítulo 10](03_simulation/03_scheduling.md):

1. **Reparto de rutas**: ¿una ruta para todos, o *k* rutas repartidas?
   Es lo que más mueve el número de turnos.
2. **Prioridad y desempate**: ¿a quién se le concede la plaza cuando hay más demanda
   que oferta? Con `max_drones=1` en casi todo el mapa, **el desempate importa más que
   la prioridad**.
3. **Representación del dron en tránsito**: ¿`position` se ensancha, o un campo
   aparte? Fija el tipo de `position` y el invariante de ocupación.

Y las que dependen de ellas:

4. Cómo se modela la capacidad del enlace (`max_link_capacity` **no se aplica hoy**).
5. Si se replanifica cuando el siguiente paso está ocupado.
6. Qué hace el scheduler cuando no puede avanzar nadie.

> ⚠️ **Ninguna de estas está decidida**, y por diseño: la [decisión del proyecto](next.md)
> es que las decisiones de scheduling se toman **con argumentos**, no por defecto.
> El capítulo 10 las presenta y las compara; la elección es del autor.