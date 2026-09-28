# 02. Setup y herramientas

El entorno de trabajo de Fly-in: **Makefile**, **Flake8**, **Mypy** y el **entorno
virtual**. Son la infraestructura que hace que `make run` funcione en cualquier
máquina — incluida la de quien te revisa.

---

## 1. El árbol de archivos

Así está organizado tu proyecto (`fly/`):

```
fly/
├── Makefile          # los comandos
├── README.md
├── requirements.txt  # dependencias con versión exacta
├── mypy.ini          # config de mypy
├── src/
│   ├── main.py
│   ├── models.py             # Zone, Connection, Drone, Graph
│   ├── parser/               # io.py, metadata.py, validators.py, builders.py, exceptions.py
│   ├── pathfinding.py
│   ├── simulation.py
│   └── visualization.py
├── maps/             # ficheros de mapa de test
└── venv/             # entorno virtual (ignorado por git)
```

Cada fichero tiene **una** responsabilidad: parser lee el mapa, models define las
entidades, pathfinding calcula rutas, simulation mueve los drones. Un `main.py` de
800 líneas con todo mezclado es imposible de tipar limpio y de revisar.

---

## 2. Makefile — el recetario de comandos

Metáfora: un recetario. Escribes cada receta **una vez** y luego solo dices
`make <receta>` — nunca repites el comando a mano.

Tus recetas reales (`fly/Makefile`):

| Target | Hace | Cuándo |
|---|---|---|
| `make install` | `pip install -r requirements.txt` | en una máquina limpia |
| `make run ARGS="maps/easy/01.txt"` | `python3 -m src.main $(ARGS)` | ejecutar el programa |
| `make debug ARGS="maps/..."` | entra en `pdb` (el depurador) | cazar un bug |
| `make clean` | borra `__pycache__/`, `*.pyc`, `*:Zone.Identifier` y caches | cuando se llene de basura |
| `make status` | lista los archivos que hay que limpiar | antes de hacer `clean` |
| `make lint` | `flake8 .` + `mypy .` (flags relajadas) | chequeo rápido |
| `make lint-strict` | `flake8 .` + `mypy . --strict` | chequeo exigente |
| `make fclean` | `clean` + borra `*.egg-info`, coverage | limpieza total |

Dos detalles que importan:

- **`$(ARGS)`**: la variable te deja pasar el mapa *sin tocar el Makefile*:
  `make run ARGS="maps/easy/01.txt"`. Imprescindible porque la revisión se hace en
  la máquina de otro.
- **`clean` no toca `venv/`**: los `find` usan `-name venv -prune` para no recorrer
  los miles de `__pycache__` de las dependencias. Venv se borra solo con `fclean`.

---

## 3. Entorno virtual — tu maleta personal

Metáfora: cada proyecto lleva su propia maleta con sus herramientas y versiones,
sin mezclarse con los otros proyectos de tu casa (`~/.venv`, otros venvs, el Python
del sistema).

```bash
python3 -m venv venv   # crea la maleta dentro de fly/
source venv/bin/activate  # la despliega (empieza a usarla)
pip install flake8 mypy pytest
```

Lo que hace que la maleta sea **reproducible** es `requirements.txt` con versiones
exactas:

```
flake8==7.3.0
mypy==2.3.1
pytest==9.1.1
```

Así `make install` en una máquina limpia instala **exactamente** lo mismo que en la
tuya.

> Gotcha real del proyecto: si mueves el venv de carpeta, **hay que recrearlo**
> (`python3 -m venv venv`) — sus scripts guardan la ruta absoluta y se rompen al
> mudarse. Pasó cuando el venv global se rompió y tuvimos que crear uno dentro de
> `fly/`.

**¿Por qué no todas las dependencias del mundo?** Cuanto menos instalas, menos
superficie para que algo falle en la máquina de otro durante la revisión. El parser,
pathfinding y simulación de Fly-in son de **librería estándar** a propósito.

---

## 6. Exclusiones — lo que git *no* debe ver

`.gitignore` en la raíz evita commitear basura regenerable:

```
__pycache__/
*.py[cod]
.mypy_cache/
.pytest_cache/
venv/
.DS_Store
*:Zone.Identifier
```

- `*.pyc` / `__pycache__/` — bytecode de Python, se regenera solo.
- `.mypy_cache/` / `.pytest_cache/` — cachés de las herramientas.
- `venv/` — tu maleta personal, no se comparte entre personas.
- `*:Zone.Identifier` — basura de metadatos que dejan las descargas en Windows.

Si algo de esto aparece en `git status`, tu `.gitignore` no lo está cubriendo o
está fuera de las rutas ignoradas. `make clean` + `make status` son la comprobación
rápida.