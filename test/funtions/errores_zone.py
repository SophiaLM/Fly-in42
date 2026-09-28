"""TEST 05 — Tipo de zona inválido (zone_invalida.txt)."""

from __future__ import annotations

from formato import Results, section


def main() -> int:
    section("3. ZONES — TIPO DE ZONA INVÁLIDO")

    results = Results()
    results.test(
        5,
        "zone=volcano (no está en normal/blocked/restricted/priority)",
        "zone_invalida.txt",
        "exit != 0 y mensaje de error a stderr",
    )
    results.summary("zone")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())