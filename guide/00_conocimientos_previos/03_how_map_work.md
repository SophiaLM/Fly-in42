# 01. Cómo funcionan los mapas

Los mapas son **la entrada** de Fly-in: un fichero `.txt` que tu parser traduce a un
`Graph`. Están en `fly/maps/`, organizados por dificultad. Si entiendes bien qué
forma tienen y qué hay (y qué *no hay*) en ellos, sabrás exactamente qué validar.

---

## 1. Anatomía de un mapa — el formato

Un mapa real se ve así (`fly/maps/easy/01_linear_path.txt`):

```
# Easy Level 1: Simple linear path
nb_drones: 2

start_hub: start 0 0 [color=green]
hub: waypoint1 1 0 [color=blue]
hub: waypoint2 2 0 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-waypoint1
connection: waypoint1-waypoint2
connection: waypoint2-goal
```

Cuatro piezas con un prefijo antes de `:`:

**directivas_mapa:**
  **nb_drones:**
    declara: Cuántos drones creará la simulación (obligatoria y primera)
    ejemplo: "nb_drones: 2"

  **start_hub:**
    declara: La zona de salida (exactamente una)
    ejemplo: "start_hub: start 0 0 [color=green]"

  **hub:**
    declara: Una zona del medio
    ejemplo: "hub: waypoint1 1 0 [color=blue]"

  **end_hub:**
    declara: La zona de destino (exactamente una)
    ejemplo: "end_hub: goal 3 0 [color=red]"

  **connection:**
    declara: Un enlace bidireccional entre dos zonas nombre-nombre
    ejemplo: "connection: start-waypoint1"

Detalles del formato:

- **Metadata** `[clave=valor ...]`: lista opcional de pares separados por espacios,
  en **cualquier orden**. Los pares válidos son `zone`, `color`, `max_drones` (zona)
  y `max_link_capacity` (conexión). Todo es opcional y tiene un valor por defecto.
- **Comentarios** `#`: se ignoran. En los mapas del repo siempre van en línea propia.
- **Líneas vacías**: se ignoran.

## 2. Los tipos de zona y las capacidades

Cada zona tiene un tipo que cambia cuánto cuesta atravesarla. Esto es lo que decide
que el pathfinding necesite Dijkstra y no BFS:

+-------------+---------------+------------------------------------------+
| Tipo        | Coste         | Notas                                    |
+-------------+---------------+------------------------------------------+
| normal      | 1 turno       | Estándar                                 |
| priority    | 1 turno       | Igual de rápido, pero "preferente"       |
| restricted  | 2 turnos      | Lento, a veces inevitable                |
| blocked     | intransitable | Nunca se puede atravesar                 |
+-------------+---------------+------------------------------------------+

Dos metadatos de capacidad numérica:

- `max_drones=<n>` — límite de drones que caben en una zona.
- `max_link_capacity=<n>` — límite de drones simultáneos en una conexión.

Estas capacidades son la fuente de los "cuellos de botella" con los que juegan los
mapas más difíciles.

> **Regla rápida**: `priority` cuesta lo mismo que `normal` (1 turno) pero la
> simulación debe darle preferencia; `blocked` es el único que no se recorre nunca.
> Si tu algoritmo atraviesa `restricted` cuando existe alternativa normal, perderás
> puntos de optimización — no es un bug, pero sí un camino subóptimo.

## 3. Los mapas de prueba del repo

`fly/maps/README.md` describe una colección propia de 10 mapas en 4 niveles:

🟢 easy:
  cantidad: 3
  objetivo: Navegación básica
  tests:
    - 01_linear_path
    - 02_simple_fork
    - 03_basic_capacity

🟡 medium:
  cantidad: 3
  objetivo: Robustez del algoritmo
  detalles: callejones sin salida, bucles, zonas priority

🔴 hard:
  cantidad: 3
  objetivo: Estrés
  detalles: laberintos, capacidades extremas, 03_ultimate_challenge

⚫ challenger:
  cantidad: 1
  objetivo: Investigación
  tests:
    - 01_the_impossible_dream (casi irresoluble)

> ⚠️ **Aviso del README**: el mapa *Challenger* está diseñado para empujar los
> límites algorítmicos y puede que **no sea solucionable** por la mayoría de
> implementaciones. Úsalo para investigación, no para validar.

**Tipos de reto que cubren**: callejones sin salida (backtracking), bucles (evitar
infinitos), cuellos de botella por capacidad (`max_drones` y `max_link_capacity`),
optimización por tipo de zona, y topología compleja (múltiples caminos, puntos de
convergencia). Los benchmarks del README: Easy < 10 turnos, Medium 10–30, Hard 30+,
y un récord de **45 turnos** para *The Impossible Dream*.

## 4. Qué tener en cuenta al parsearlos

Los mapas oficiales **no te preparan para el error** — son todos válidos por diseño.
Todo el trabajo de validación es tuyo. Divide lo que los mapas reales ejercitan de lo que **nunca** ejercitan (y que por tanto debes probar con mapas propios):

**reglas_mapas_repo**:
  **siempre_tienen**:
    - Coordenadas enteras (incluida alguna negativa)
    - restricted y priority con frecuencia
    - max_drones / max_link_capacity entre 1 y 8
    - Comentarios # (siempre en línea propia)
    - Metadata SIEMPRE en el mismo orden: [zone, color, max_drones]
    - Toda zona con al menos [color=...]
    - Exactamente un start_hub y un end_hub
    - Nombres de zona y conexiones siempre válidos

  **nunca_tienen_pruebalo_tu**:
    - Una zone=blocked (no aparece en ningún mapa de 42)
    - Nombre de zona duplicado
    - Conexión a una zona inexistente
    - Conexión duplicada (a-b y luego b-a)
    - Orden de claves distinto ([max_drones=2 color=red])
    - Zona sin metadata (hub: foo 3 3 a secas)
    - max_drones en el start_hub (se acepta pero se ignora)
    - Nombre con guion, espacio o mal tipado
    - Fichero vacío, sin nb_drones:, o nb_drones: 0

Consecuencia práctica: la fila más peligrosa es **`zone=blocked` — cero apariciones**.
Si tu pathfinding la atraviesa por error, los 10 mapas de prueba jamás te lo dirán;
solo lo descubrirás con un mapa propio o el día de la revisión entre pares.

> **Gotcha real**: no asumas el orden de la metadata. Los 11 mapas de 42 usan
> *siempre* `[zone=... color=... max_drones=...]`. Si tu código depende de ese orden
> de forma implícita, pasará todos los mapas oficiales y fallará con uno reordenado
> en la revisión. Los tokens se parsean como un `dict` sin orden.