# =============================================================================
#  formato.py — NÚCLEO COMPARTIDO DE LA SUITE DE PRUEBAS DE ERRORES
# -----------------------------------------------------------------------------
#  Versión liviana del test_framework.h del tester de codexion: colores,
#  layout, ejecución del programa FLY-IN y evaluación de "fallo esperado".
#  Los modulos de test/funtions/ importan estas funciones.
# =============================================================================

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- colores ----
PINK = "\033[38;5;218m"
STRONG = "\033[38;5;204m"
LILAC = "\033[38;5;141m"
GOLD = "\033[38;5;215m"
GREEN = "\033[38;5;113m"
RED = "\033[38;5;196m"
RESET = "\033[0m"

SEP_W = 78

# ------------------------------------------------------------- rutas del proyecto ----
FUNTIONS = Path(__file__).resolve().parent     # fly_in/test/funtions
ROOT = FUNTIONS.parent.parent                  # fly_in/
FLY = ROOT / "fly"
MAPS = ROOT / "test" / "maps_fake"
PYTHON = Path(os.environ.get("FLY_PYTHON", FLY / "venv" / "bin" / "python3"))


def sep() -> None:
    print(f"{LILAC}{'=' * SEP_W}{RESET}")


def dash() -> None:
    print(f"{LILAC}{'-' * SEP_W}{RESET}")


def section(title: str) -> None:
    dash()
    print(f" {PINK}{title}{RESET}")
    dash()
    print("")


def run_program(map_name: str) -> tuple[int, str]:
    """Ejecuta el programa contra un mapa de maps_fake y devuelve (exit, stderr)."""
    if not PYTHON.is_file():
        print(f"{RED}[ERROR]{RESET} python no encontrado: {PYTHON}", file=sys.stderr)
        sys.exit(2)
    proc = subprocess.run(
        [str(PYTHON), "-m", "src.main", str(MAPS / map_name)],
        cwd=str(FLY),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stderr


def _evaluate(rc: int, err: str) -> tuple[bool, str, str]:
    """PASS si el programa falla (exit != 0) con algo en stderr. Devuelve (ok, got, warn)."""
    if rc == 0:
        return False, "exit=0: el programa ACEPTÓ un mapa inválido (debería fallar)", ""
    if not err.strip():
        return False, f"exit={rc} pero sin mensaje de error a stderr", ""
    if "Traceback" in err:
        exc = next(
            (l.strip() for l in err.splitlines()
             if l and not l.startswith(" ") and not l.startswith("Traceback")),
            "(sin detalle de excepción)",
        )
        warn = "Excepción sin capturar (traceback) en vez de un error limpio 'error: ...'"
        return True, f"exit={rc} (falla), última excepción: {exc}", warn
    first = next((l.strip() for l in err.splitlines() if l.strip()), "")
    return True, f"exit={rc}, {first}", ""


class Results:
    """Acumula PASS/FAIL de una sección e imprime cada test (estilo tf_result)."""

    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0

    def test(
        self,
        test_id: int,
        name: str,
        map_name: str,
        expected: str,
    ) -> bool:
        """Ejecuta el programa sobre map_name y valida que falle cuando debe."""
        rc, err = run_program(map_name)
        ok, got, warn = _evaluate(rc, err)

        state = " OK " if ok else "FAIL"
        color = GREEN if ok else RED
        print(f"  {color}[{state}]{RESET}  TEST {test_id:02d}:")
        print(f"          ARGUMENT:    python3 -m src.main test/maps_fake/{map_name}")
        print(f"          DESCRIPTION: {name}")
        print(f"          |-- EXPECTED : {expected}")
        print(f"          |-- GOT      : {got}")
        if warn:
            print(f"          {GOLD}[WARN]{RESET} {warn}")
        print("")

        if ok:
            self.passed += 1
        else:
            self.failed += 1
        return ok

    def summary(self, label: str) -> None:
        total = self.passed + self.failed
        print(f"  [SECTION SUMMARY] : {GREEN}{self.passed}{RESET}/{total} Passed — {label}")
        print(f"  [TOTALS]          : PASS={self.passed} | FAIL={self.failed}")