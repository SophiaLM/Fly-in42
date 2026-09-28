"""TEST 01 — Mapa con bytes no UTF-8 (encoding_invalido.txt)."""

from __future__ import annotations

from formato import Results, section


def main() -> int:
    section("1. ENCODING — MAPA CON BYTES NO UTF-8")

    results = Results()
    results.test(
        1,
        "Encoding inválido: bytes 0xFF 0xFE 0x80 ilegibles",
        "encoding_invalido.txt",
        "exit != 0 y mensaje de error a stderr",
    )
    results.summary("encoding")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())