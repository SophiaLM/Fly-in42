#!/usr/bin/env bash
# =============================================================================
#  test_errors.sh — ORQUESTADOR DE PRUEBAS DE ERRORES DE PARSING (FLY-IN)
# -----------------------------------------------------------------------------
#  Ejecuta los modulos de test/funtions/ contra los mapas inválidos de
#  test/maps_fake/ y comprueba que el programa falla (exit != 0) cuando debe.
#  Muestra los errores en orden, con el formato de test/reference.md.
#
#  Uso:  bash test/test_errors.sh
#        FLY_PYTHON=/ruta/a/python3 bash test/test_errors.sh   # override
# =============================================================================

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FUN="$SCRIPT_DIR/funtions"
FLY="$SCRIPT_DIR/../fly"

# ---------------------------------------------------------------- colores ----
PINK='\033[38;5;218m'
STRONG='\033[38;5;204m'
LILAC='\033[38;5;141m'
GOLD='\033[38;5;215m'
GREEN='\033[38;5;113m'
RED='\033[38;5;196m'
RESET='\033[0m'
SEP_W=78

sep()  { echo -e "${LILAC}$(printf '%*s' "$SEP_W" '' | tr ' ' '=')${RESET}"; }
dash() { echo -e "${LILAC}$(printf '%*s' "$SEP_W" '' | tr ' ' '-')${RESET}"; }

# ---------------------------------------------------------- modulos a correr ---
# Orden de ejecucion = orden de los mapas en maps_fake (tests 01 a 05).
MODULES=(errores_encoding errores_nb_drones errores_zone)

# Python del proyecto: FLY_PYTHON si se exportó, si no el venv de fly/.
if [ -z "${FLY_PYTHON:-}" ]; then
	FLY_PYTHON="$FLY/venv/bin/python3"
fi
export FLY_PYTHON

if [ ! -x "$FLY_PYTHON" ]; then
	echo -e "${RED}[ERROR]${RESET} python no encontrado: $FLY_PYTHON" >&2
	echo "  usa: FLY_PYTHON=/ruta/a/python3 bash $0" >&2
	exit 2
fi

# =================================================================== CABECERA ===
echo -e "${LILAC}$(printf '%*s' "$SEP_W" '' | tr ' ' '=')${RESET}"

echo -e "${PINK}███████╗██╗     ██╗   ██╗      ██╗███╗   ██╗${RESET}"
echo -e "${PINK}██╔════╝██║     ╚██╗ ██╔╝      ██║████╗  ██║${RESET}"
echo -e "${PINK}█████╗  ██║      ╚████╔╝ ███║  ██║██╔██╗ ██║${RESET}"
echo -e "${PINK}██╔══╝  ██║       ╚██╔╝        ██║██║╚██╗██║${RESET}"
echo -e "${PINK}██║     ███████╗   ██║         ██║██║ ╚████║${RESET}"
echo -e "${PINK}╚═╝     ╚══════╝   ╚═╝         ╚═╝╚═╝  ╚═══╝${RESET}"
echo -e "        ${STRONG}SUITE DE ERRORES DE PARSING${RESET}"

echo -e "${LILAC}$(printf '%*s' "$SEP_W" '' | tr ' ' '=')${RESET}"
echo ""
echo -e "${GREEN}[+]${RESET} TARGET   : python3 -m src.main <mapa>"
echo -e "${GREEN}[+]${RESET} MAPS     : test/maps_fake/"
echo -e "${GREEN}[+]${RESET} COVERAGE : encoding / nb_drones / zone"
echo ""

# =================================================================== EJECUTAR ===
GP=0; GF=0
for m in "${MODULES[@]}"; do
	if [ ! -f "$FUN/$m.py" ]; then
		echo -e "${RED}[ERROR]${RESET} módulo no encontrado: $FUN/$m.py" >&2
		exit 1
	fi
	output=$("$FLY_PYTHON" -u "$FUN/$m.py" 2>&1)
	rc=$?
	echo "$output"
	if [ "$rc" -ne 0 ]; then
		echo -e "${RED}[WARN]${RESET} módulo $m salió con rc=$rc"
	fi
	totals=$(printf '%s\n' "$output" | sed -n 's/^  \[TOTALS\]          : PASS=\([0-9]*\) | FAIL=\([0-9]*\)$/\1 \2/p')
	read -r p f <<<"$totals"
	GP=$((GP + ${p:-0}))
	GF=$((GF + ${f:-0}))
	echo ""
done

# ================================================================== RESULTADO ===
sep
echo -e " ${PINK}FINAL TEST RESULTS${RESET}"
sep
echo ""
echo "  TOTAL TESTS RAN : [ $((GP + GF)) ]"
echo -e "  PASSED          : [ ${GREEN}${GP}${RESET} ]"
echo -e "  FAILED          : [ ${RED}${GF}${RESET} ]"
if [ $((GP + GF)) -gt 0 ]; then
	rate=$(awk -v p="$GP" -v f="$GF" 'BEGIN{ printf "%.1f%%", p*100/(p+f) }')
else
	rate="-"
fi
echo -e "  SUCCESS RATE    : [ ${GOLD}${rate}${RESET} ]"
echo ""
if [ "$GF" -gt 0 ]; then
	echo -e "  ${RED}STATUS          : Algún mapa inválido fue aceptado o falló sin mensaje de error.${RESET}"
	exit 1
else
	echo -e "  ${GREEN}STATUS          : Ninguno falló — Todos los mapas inválidos fueron rechazados correctamente.${RESET}"
	echo ""
	echo -e "  ${LILAC}NOTA: Las advertencias [WARN] indican un fallo capturado vía traceback${RESET} "
	echo -e "        ${LILAC}en lugar de un mensaje de error formateado (stderr).${RESET}"
	echo ""
	exit 0
fi