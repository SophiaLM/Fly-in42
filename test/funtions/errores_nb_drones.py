"""TEST 02-04 — nb_drones inválido (cero, negativo, no entero)."""

from __future__ import annotations

from formato import Results, section


def main() -> int:
    section("2. NB_DRONES — CANTIDAD DE DRONES INVÁLIDA")

    results = Results()
    results.test(
        2,
        "nb_drones = 0 (no positivo)",
        "nb_drones_cero.txt",
        "exit != 0 y mensaje de error a stderr",
    )
    results.test(
        3,
        "nb_drones = -3 (negativo)",
        "nb_drones_negativo.txt",
        "exit != 0 y mensaje de error a stderr",
    )
    results.test(
        4,
        "nb_drones = abc (no entero)",
        "nb_drones_no_entero.txt",
        "exit != 0 y mensaje de error a stderr",
    )
    results.summary("nb_drones")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())