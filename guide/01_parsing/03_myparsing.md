# 03. Mi parser

El paquete `fly/src/parser/` traduce el texto plano del mapa a un `Graph` validado,
o lanza un error claro (`MapParseError`) si algo no cuadra. Se reparte en 5 ficheros,
cada uno con una responsabilidad: `io.py` (leer y limpiar), `metadata.py` (prefijos y
metadatos), `validators.py` (valores sueltos), `builders.py` (construir objetos),
`exceptions.py` (la excepción propia).

---

## 1. La estructura en árbol: cómo fluye una línea

Todo el parseo es **una sola pasada, hacia delante** (las conexiones solo enlazan
zonas "previamente definidas" — esa regla del enunciado es lo que lo permite). El
árbol de llamadas de una línea `hub: roof1 3 4 [zone=restricted color=red]`:

```
parse_map_file(path)                         builders.py    — orquestador
├── read_lines(path)                         io.py          → list[(n_línea, texto)]
├── strip_noise(lines)                       io.py          → quita # y vacías
├── classify_line(line)                      metadata.py    → (prefijo, contenido)
├── split_metadata_block(body)               metadata.py    → (cuerpo, meta | None)
├── parse_metadata(meta)                     metadata.py    → dict[str, str]
└── parse_zone_line(body, meta, ...)         builders.py    — instancia Zone
    ├── parse_int_field(x/y)                 validators.py  — coordenadas (admite negativos)
    ├── parse_zone_type(zone=)               validators.py  — → ZoneType
    └── parse_positive_int(max_drones=)      validators.py  — solo si no es start/end
                                                        ↓
                                        Connection  ←  parse_connection_line
                                                        ↓
                                        Graph(zones, connections, nb_drones)
```

El tipo de dato cambia en cada escalón — texto → líneas → `(prefijo, cuerpo)` →
`(cuerpo, meta)` → `dict[str,str]` → objeto de dominio (`Zone`/`Connection`) → `Graph`:

| Etapa | Tipo en Python |
|---|---|
| Mapa en disco | fichero `.txt` |
| Leído | `list[tuple[int, str]]` (con número de línea) |
| Limpio | `list[tuple[int, str]]` sin `#` ni vacías |
| Clasificado | `tuple[str, str]` (prefijo, contenido) |
| Nombre + metadata | `tuple[str, str \| None]` |
| Metadata | `dict[str, str]` |
| Una zona / conexión | objeto `Zone` / `Connection` |
| El mapa completo | objeto `Graph` |

Cada función vive en un escalón y **no se salta pasos**: `parse_metadata` no sabe
nada de `Zone`, y `Zone` no sabe nada de cómo se parseó el texto que la originó.

## 2. Las funciones, una por una

### `exceptions.py` — la excepción propia

```python
class MapParseError(Exception):
    """Se lanza cuando el fichero de mapa viola el formato o validación."""
```

Nunca se usa `ValueError` a pelo por todo el parser; `main.py` captura
`MapParseError` **una sola vez**, imprime a stderr y sale con código distinto de cero.

### `io.py` — leer y limpiar

```python
def read_lines(path: str) -> list[tuple[int, str]]:
    """Único punto de E/S: lee con with open(...) y devuelve (n_línea, texto)."""
```
```python
def strip_noise(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Descarta comentarios (#) y líneas vacías conservando la numeración."""
```

### `metadata.py` — prefijos y metadatos

```python
def classify_line(line: str) -> tuple[str, str]:
    """Separa el prefijo (hub, connection...) del contenido; rechaza prefijos inválidos."""
```
```python
def split_metadata_block(body: str) -> tuple[str, str | None]:
    """Separa el cuerpo de su metadata opcional [...]; valida el ']' de cierre."""
```
```python
def parse_metadata(meta: str | None) -> dict[str, str]:
    """Convierte 'clave=valor' en dict; rechaza tokens sin '=' y claves duplicadas."""
```

### `validators.py` — valores sueltos

```python
def parse_zone_type(raw: str | None, line_no: int) -> ZoneType:
    """Mapea zone= al Enum; NORMAL si no aparece; error si el valor no es válido."""
```
```python
def parse_positive_int(raw: str, field_name: str, line_no: int) -> int:
    """Convierte a entero > 0 (max_drones, max_link_capacity, nb_drones)."""
```
```python
def parse_int_field(raw: str, field_name: str, line_no: int) -> int:
    """Convierte a entero SIN exigir positividad (coordenadas x, y)."""
```

### `builders.py` — construir objetos y orquestar

```python
def parse_zone_line(body, meta, is_start, is_end, line_no) -> Zone:
    """Única encargada de instanciar Zone: aridad, guiones, coords, tipo, max_drones."""
```
```python
def parse_connection_line(body, meta, zones, seen, line_no) -> Connection:
    """Construye Connection: valida extremos existentes, duplicados y capacidad."""
```
```python
def parse_map_file(path: str) -> Graph:
    """Orquestador: nb_drones primero, bucle de líneas, invariantes start/end al final."""
```

`parse_map_file` es deliberadamente corto: lee, comprueba que la primera línea sea
`nb_drones`, recorre el resto clasificando zona vs conexión, y al terminar verifica
las invariantes **globales** — exactamente un `start_hub` y un `end_hub` — que solo
se pueden saber tras haberse leído *todo* el fichero.

## 3. Tricuñuelas a tener en cuenta

1. **Coordenadas ≠ enteros positivos.** `x`/`y` admiten negativos y cero
   (los mapas reales usan `y=-1`); `max_drones`/`max_link_capacity` deben ser > 0.
   Por eso existen dos funciones hermanas (`parse_int_field` vs
   `parse_positive_int`) — no uses la misma para ambas.

2. **El espacio en el nombre no se detecta "buscando espacios".** El `split()` ya
   separó la línea, así que un nombre con espacio llega como dos tokens: detecta la
   **aridad equivocada** (`len(tokens) != 3`) en `parse_zone_line`
   (`builders.py:21`), no el carácter espacio.

3. **El guion en el nombre rompe las conexiones.** `connection: a-b-c` es ambiguo.
   El parchís de `partition("-")` usa el *primer* guion, por eso los nombres de zona
   tienen prohibido el guion desde el origen (`builders.py:27`).

4. **`max_drones` en `start_hub`/`end_hub`: aceptar y descartar, no es error.**
   Regla explícita del enunciado — se ignora en hubs pero se valida en el resto
   (`builders.py:38`).

5. **Conexión duplicada en ambos sentidos.** `a-b` y luego `b-a` son lo mismo: se
   guarda el par **ordenado alfabéticamente** en un `set` y una sola comprobación
   detecta ambos duplicados (`builders.py:74`).

6. **No asumas el orden de la metadata.** Los mapas oficiales usan siempre
   `zone→color→max_drones`, pero es pura coincidencia de formato. El `dict` las
   trata sin orden — un mapa `[max_drones=2 color=red]` debe pasar igual.

7. **`zone=blocked` no aparece en ningún mapa oficial.** Si el pathfinding la
   atraviesa por error, ninguna prueba real te lo dirá: necesitas un mapa propio.

8. **Traduce `ValueError` → `MapParseError` con número de línea.** Un error genérico
   de dominio interno se envuelve con contexto de línea; nunca lo dejes escapar hasta
   `main.py` con una traza fea (regla: excepción no capturada = "no funcional").

9. **Un `#` "trailing" al final de una directiva se comporta como error de aridad.**
   `strip_noise` solo descarta líneas *completas* de comentario; un `hub: foo 3 3 # c`
   comentaría a `split()` como cuarto token y fallará el `len(tokens) != 3`. Decide
   y documenta qué hacer si alguien lo prueba.

10. **Corchetes mal cerrados.** `split_metadata_block` exige que la línea termine en
    `]` — `[zone=normal` sin cerrar es error (`metadata.py:30`), no se asume nada.

11. **`partition` en vez de `split("=", 1)`.** Devuelve `(clave, "=", valor)` — tres
    posiciones explícitas, sin depender de contar elementos (`metadata.py:47`).

12. **Primera línea significativa = `nb_drones`.** Si la primera línea "real" (tras
    limpiar comentarios/vacías) no es `nb_drones`, error. Fichero vacío o solo
    comentarios también es error (`builders.py:100`).

13. **Los nombres duplicados se detectan dentro del bucle; start/end al final.** El
    nombre único es información local (se ve al llegar la zona), "exactamente un
    start y un end" es global (solo se sabe al terminar el fichero) — cada chequeo
    vive donde su información está disponible.