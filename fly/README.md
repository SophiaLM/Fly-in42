*This project has been created as part of the 42 curriculum by sophluna.*

# Fly-in

## Description

**Fly-in** is a discrete-time drone traffic simulator written in Python. It reads a map of connected zones, computes routes for a fleet of drones, and moves every drone from the `start_hub` to the `end_hub` in as few turns as possible, while respecting zone capacities, connection capacities, restricted zones and blocked zones.

### Goal

A correct, terminating, deadlock-free simulation where:

- every drone reaches the `end_hub`, and n
one is lost or duplicated;
- a zone never holds more than its `max_drones`, and a connection never carries more than its `max_link_capacity` in one turn;
- entering a `restricted` zone takes exactly 2 turns, and the drone cannot wait on the connection for a free slot;
- `blocked` zones are never entered, and `priority` zones are preferred between routes of equal length;
- the run ends by itself in the minimum number of turns (the **makespan**), and it can never hang.

### Overview

The project contains two different problems, and keeping them apart is what makes the solution simple:

| Problem | Question | Solved by |
|---|---|---|
| **Routing** | Which zones does each drone cross? | `PathFinder`: Dijkstra on the static graph |
| **Scheduling** | Who moves this turn and who waits? | `Simulation`: two-phase turn resolution |

The shortest path for each drone is not automatically the best plan for the fleet. Drones sharing one narrow gate queue behind each other, so routing already decides most of the makespan. That is why the fleet is spread over several equally short routes.

## Instructions

### Requirements

- Python 3.10 or newer (PEP 604 `X | Y` annotations).
- `make`.
- **No runtime dependencies**: only the standard library is used (no `networkx`, no `graphlib`). `flake8`, `mypy` and `pytest` are listed in `requirements.txt` for development only.

### Install

```
cd fly
make install
```

This creates `./venv` (using `uv` when available) and installs the development tools.

### Run

```
make run ARGS=../test/maps/easy/01_linear_path.txt
```

or, without `make`:

```
venv/bin/python3 -m src.main ../test/maps/easy/01_linear_path.txt
```

Turns are written to **stdout** and errors to **stderr**, so the output can be piped or redirected safely.

| Exit code | Meaning |
|---|---|
| `0` | Every drone was delivered |
| `1` | Invalid or unreadable map, no route to the end hub, or a simulation that cannot progress |

To run every official map and print its number of turns (one output line per turn):

```
for f in ../test/maps/*/*.txt; do
  echo "$f: $(venv/bin/python3 -m src.main "$f" | wc -l)"
done
```

### Other targets

`make compile`, `make lint`, `make lint-strict`, `make debug`, `make status`, `make clean`, `make fclean`, `make help`.

### Input format

A map is a text file. The first non-comment line is `nb_drones`, followed by zone and connection declarations. `#` starts a comment and blank lines are ignored.

- Directives: `nb_drones`, `start_hub`, `end_hub`, `hub`, `connection`.
- Zone: `<name> <x> <y> [key=value ...]`. Connection: `<zoneA>-<zoneB> [max_link_capacity=N]`.
- Zone types: `normal` (1 turn), `priority` (1 turn, preferred), `restricted` (2 turns), `blocked` (never entered).
- Defaults: `max_drones=1`, `max_link_capacity=1`, `zone=normal`. `max_drones` is ignored on `start_hub` and `end_hub`.
- Exactly one `start_hub` and one `end_hub`; zone names are unique and cannot contain `-`.
- Connections are undirected: `a-b` and `b-a` are the same edge. Unknown metadata keys are ignored.
- Any violation raises a `MapParseError` with the **line number**, printed as `error: ...` with exit code `1`.

## Example

Input (`nb_drones: 4`, a one-slot bottleneck followed by a wide zone):

```
nb_drones: 4

start_hub: start 0 0 [color=green]
hub: bottleneck 1 0 [color=red max_drones=1]
hub: wide_area 2 0 [color=blue max_drones=4]
end_hub: goal 3 0 [color=red]

connection: start-bottleneck [max_link_capacity=1]
connection: bottleneck-wide_area [max_link_capacity=1]
connection: wide_area-goal [max_link_capacity=2]
```

Expected output (6 turns, one line per turn):

```
D1-bottleneck
D1-wide_area D2-bottleneck
D1-goal D2-wide_area D3-bottleneck
D2-goal D3-wide_area D4-bottleneck
D3-goal D4-wide_area
D4-goal
```

How to read it: each token is `D<id>-<destination>`, the zone the drone **ended in** that turn. Drones that wait are not printed, and delivered drones disappear. `D2`, `D3` and `D4` are held at `start` because `bottleneck` can hold only one drone.

A drone in flight towards a `restricted` zone is printed as `D<id>-<connection>` using the connection exactly as written in the map, for example `D1-loop_b-exit_point`.

## Algorithm choices and implementation

### Data model: one source of truth

`src/models.py` defines `Zone`, `Connection`, `Drone` and `Graph`. State is split in two:

| State | Where | Used by |
|---|---|---|
| Static (topology, costs, declared capacities) | `Graph.zones`, `Graph.connections`, adjacency index | `PathFinder` |
| Dynamic (who is where, who is in flight) | `Zone.drones`, `Connection.drones` | `Simulation` |

The simulation asks these objects instead of keeping its own occupancy table, so two copies of the truth can never drift apart. `Drone.move_to` keeps the invariant `drone in zone.drones` ⟺ `drone.position is zone` (it adds before it removes, so an over-capacity add fails before anything changes), and `blocked` is enforced inside `Zone.can_accept_drone`. A drone in transit has its own `transit` field: it belongs to a connection and to no zone.

### Parsing: a single forward pass

`src/parser/` is split by responsibility (`io`, `metadata`, `validators`, `builders`, plus `MapParseError`). Connections may only reference zones already defined, so one pass in file order is enough to build the `Graph`.

The graph is an **adjacency list**, not a matrix: the largest map has 54 zones and 70 edges, so a 54 × 54 matrix would store 2916 slots for 70 real edges.

### Routing: Dijkstra with a cost pair

- **Why Dijkstra**: all costs are positive integers, so it is optimal. BFS ignores costs, A\* has no honest heuristic (coordinates are unrelated to movement cost), and Bellman-Ford is slower for a weaker problem.
- **Edge cost** is the cost of the destination zone (`normal` and `priority` = 1, `restricted` = 2). `blocked` zones are filtered when neighbours are queried, so they are never candidates.
- **Priority zones**: the path cost is a pair `(turns, preference)`. `turns` always dominates, so a priority zone can never make a route longer; among routes of equal length, the one crossing more priority zones wins. This rule lives only in `PathFinder._step_cost`.
- **Determinism**: the heap key is `(cost, zone_name)`, so ties break the same way on every run and machine.
- **Caching**: routes are cached per origin, including the "no route" result.
- **Complexity**: `O((V + E) log V)` time per query and `O(V + E)` memory.

### Fleet routing: equal-cost routes, round-robin

`PathFinder.alternative_routes()` collects several loop-free routes and keeps only those with the minimum cost. `Simulation` then assigns them round-robin (`routes[(i - 1) % len(routes)]`). One shortest path would force the whole fleet through the same gates in single file; spreading it over equal-length routes lets drones travel in parallel and meet only at real bottlenecks. On the challenger map this took the result from **67 turns to 43**. It helps nothing where one `restricted` gate with `max_drones=1` already serialises the fleet (`medium/02_circular_loop`, `hard/02_capacity_hell`).

### Turns in two phases

The subject says that drones leaving a zone free up capacity for the same turn. That is a collective rule: applied drone by drone, the result would depend on iteration order. So each turn has two phases:

1. `collect_intents()`: every active drone declares what it wants. Nobody moves yet.
2. `resolve()`: all intents are validated against the state **after departures** and applied together.

When several drones contest the same slot, the lowest numeric drone id wins, so no hash or insertion order ever affects the result. A drone leaving a zone while another enters it in the same turn is legal.

### Restricted zones and link capacity

- **No waiting on a connection**: the destination slot is **reserved at departure**. The drone then occupies the connection for one turn and arrives on the next, so it never has to wait in mid-flight.
- **Link capacity** is a per-turn budget tracked in a `(turn, connection) -> count` reservation table. Old entries are purged each turn so the table stays bounded.

### Static scheduler: wait, do not replan

Routes are assigned once at startup. A drone that cannot move simply waits. A dynamic scheduler would be more powerful, but it makes the simulation order-dependent and harder to reason about, and measurements showed that routing, not scheduling, was the real bottleneck. A turn costs `O(D log D)` to order intents, so a whole run costs `O(T · D log D)`.

### Safety guards

- **Unreachable end hub**: if any drone has no route, the run aborts before the first turn with an `error:` message and exit code `1`.
- **Stall guard**: `Simulation` counts consecutive turns without any movement, reservation or delivery and raises if it exceeds `MAX_TURNS_WITHOUT_PROGRESS`. A correct run never reaches it; a scheduler bug fails loudly instead of looping forever.
- **Blocked start hub**: rejected with a `SimulationError` instead of crashing inside the loop.
- **Delivered drones** are retired in the same turn they land, so output lines always equal the turns played.

## Visual representation

The map declares a colour per zone (`color=green`, `color=gold`, ...). These are CSS-style names, so they are translated into ANSI 256-colour codes through a table (`NAMED_COLORS`). A name that is not in the table falls back to a deterministic hash (`zlib.crc32`), so the same map always shows the same colours.

How it helps the user:

- Colours from the map make it easier to follow where drones are in a long run without reading every zone name.
- `D10` is sorted after `D9`, and tokens always appear in the same order, so the output stays readable and comparable between runs.
- Colours appear **only when they can be seen**: they are disabled when `NO_COLOR` is set ([no-color.org](https://no-color.org/)) and when stdout is not a terminal. Redirecting to a file or piping into another program gives plain text without escape codes, ready to diff or parse.

The output itself follows the subject: one line per turn, no headers, separators or padding.

## Performance

Measured on the ten official maps.

| Map | Drones | Turns | Target |
|---|---|---|---|
| `easy/01_linear_path` | 2 | **4** | ≤ 6 |
| `easy/02_simple_fork` | 4 | **4** | ≤ 8 |
| `easy/03_basic_capacity` | 4 | **4** | ≤ 6 |
| `medium/01_dead_end_trap` | 5 | **8** | ≤ 12 |
| `medium/02_circular_loop` | 6 | **15** | ≤ 15 |
| `medium/03_priority_puzzle` | 5 | **8** | ≤ 12 |
| `hard/01_maze_nightmare` | 8 | **13** | ≤ 30 |
| `hard/02_capacity_hell` | 12 | **16** | ≤ 35 |
| `hard/03_ultimate_challenge` | 15 | **26** | ≤ 45 |
| `challenger/01_the_impossible_dream` | 25 | **43** | record: 45 |

Each run is also checked for: all drones delivered, no capacity exceeded, no `blocked` zone entered, every restricted transit taking exactly 2 turns, and every drone following its assigned route.

## Project layout

```
fly/
├── Makefile              # install / run / compile / lint / clean targets
├── requirements.txt      # development tools (flake8, mypy, pytest)
├── mypy.ini              # strict typing configuration
└── src/
    ├── main.py           # CLI entry point: parse -> simulate -> print
    ├── models.py         # Zone, Connection, Drone, Graph, ZoneType
    ├── parser/           # io / metadata / validators / builders / exceptions
    ├── pathfinding.py    # PathFinder: Dijkstra + alternative_routes
    ├── simulation.py     # Simulation: intents, resolution, reservations, turn loop
    └── visualization.py  # format_turn, colour table, NO_COLOR / TTY handling
```

## Resources

### References

- [The Algorithm Design Manual](https://www.algorist.com/), Steven Skiena: shortest paths and graph algorithms.
- [Introduction to Algorithms](https://mitpress.mit.edu/9780262046305/introduction-to-algorithms/), Cormen, Leiserson, Rivest and Stein: Dijkstra and its `O((V + E) log V)` bound.
- [`heapq` documentation](https://docs.python.org/3/library/heapq.html): the priority queue used by Dijkstra.
- [`zlib.crc32` documentation](https://docs.python.org/3/library/zlib.html#zlib.crc32): deterministic fallback for unknown colour names.
- [NetworkX pathfinding docs](https://networkx.org/documentation/stable/reference/algorithms/pathfinding.html): read only to compare strategies; the library is **not** used.
- [no-color.org](https://no-color.org/): the `NO_COLOR` convention.
- [Effective Python](https://effectivepython.com/): items on cohesion and defensive copies, applied to the model layer.
- The 42 subject (chapters VI to VIII): zone types, output format and README requirements.

### Use of AI

AI was used as an assistant, while the design decisions and the code are my own:

- **Concept tutoring**: discrete-time simulation, collective vs. per-drone rules, why the subject forces two-phase turns, and reservation tables.
- **Design review**: static vs. dynamic state, adjacency list vs. matrix, deterministic tiebreaks, and the `(turns, preference)` cost pair.
- **Debugging support**: an off-by-one that kept a delivered drone active one extra turn, a non-deterministic result caused by resolving drones one at a time, and capacity accounting during restricted transits.
- **Documentation and study material**: drafts of the project notes, the Q&A study file and this README, reviewed and corrected against the code.