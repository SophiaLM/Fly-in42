#!/usr/bin/env bash
# shellcheck shell=bash
# =============================================================================
#  lib/common.sh — funciones compartidas por run_valid.sh, run_errors.sh y
#  run_all.sh. No se ejecuta directamente: se carga con `source`.
#
#  Criterios (iguales para cualquier proyecto, no dependen del texto exacto):
#    mapa válido   : exit 0 · stderr vacío · sin traceback · stdout con una
#                    línea por turno y tokens D<n>-<zona>
#    mapa inválido : exit != 0 · mensaje en stderr · sin traceback ·
#                    stdout vacío
#
#  Variables de entorno (todas opcionales):
#    FLY_DIR      carpeta del proyecto a probar        (def: ../fly)
#    FLY_PYTHON   python a usar                        (def: $FLY_DIR/venv/bin/python3)
#    FLY_CMD      comando completo; sustituye a "$FLY_PYTHON -m src.main"
#                 (la ruta del mapa se añade como último argumento)
#    FLY_TIMEOUT  segundos máximos por mapa            (def: 10)
#    MAPS_DIR     mapas válidos                        (def: test/maps)
#    ERRORS_DIR   mapas inválidos                      (def: test/maps_errors)
#    DESC_FILE    descripciones de cada mapa           (def: test/descriptions.txt)
#    NO_COLOR     desactiva los colores
# =============================================================================

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ---------------------------------------------------------------- colores ----
if [ -n "${NO_COLOR:-}" ] || [ ! -t 1 ]; then
	PINK=''; STRONG=''; LILAC=''; GOLD=''; GREEN=''; RED=''; RESET=''
else
	PINK=$'\033[38;5;218m'
	STRONG=$'\033[38;5;204m'
	LILAC=$'\033[38;5;141m'
	GOLD=$'\033[38;5;215m'
	GREEN=$'\033[38;5;113m'
	RED=$'\033[38;5;196m'
	RESET=$'\033[0m'
fi
SEP_W=78
ESC=$'\033'
TAB=$'\t'

sep()  { printf '%s%s%s\n' "$LILAC" "$(printf '%*s' "$SEP_W" '' | tr ' ' '=')" "$RESET"; }
dash() { printf '%s%s%s\n' "$LILAC" "$(printf '%*s' "$SEP_W" '' | tr ' ' '-')" "$RESET"; }

die() {
	printf '%s[ERROR]%s %s\n' "$RED" "$RESET" "$1" >&2
	if [ -n "${2:-}" ]; then
		printf '  %s\n' "$2" >&2
	fi
	exit 2
}

abs_dir() { (cd "$1" 2>/dev/null && pwd); }

# ------------------------------------------------------------ argumentos -----
QUIET=0
parse_args() {
	local arg
	for arg in "$@"; do
		case "$arg" in
			-q|--quiet) QUIET=1 ;;
			-h|--help)  usage; exit 0 ;;
			*)
				printf 'opción desconocida: %s\n' "$arg" >&2
				usage >&2
				exit 2
				;;
		esac
	done
}

# --------------------------------------------------------------- entorno -----
setup_env() {
	local user_cmd="${FLY_CMD:-}"

	FLY_DIR="$(abs_dir "${FLY_DIR:-$TEST_DIR/../fly}")"
	[ -n "$FLY_DIR" ] || die "carpeta del proyecto no encontrada" \
		"usa: FLY_DIR=/ruta/al/proyecto bash $0"

	MAPS_DIR="${MAPS_DIR:-$TEST_DIR/maps}"
	ERRORS_DIR="${ERRORS_DIR:-$TEST_DIR/maps_errors}"
	DESC_FILE="${DESC_FILE:-$TEST_DIR/descriptions.txt}"
	FLY_TIMEOUT="${FLY_TIMEOUT:-10}"

	if [ -n "$user_cmd" ]; then
		FLY_CMD="$user_cmd"
		read -r -a CMD_ARR <<<"$FLY_CMD"
	else
		FLY_PYTHON="${FLY_PYTHON:-$FLY_DIR/venv/bin/python3}"
		[ -x "$FLY_PYTHON" ] || die "python no encontrado: $FLY_PYTHON" \
			"usa: FLY_PYTHON=/ruta/a/python3 bash $0   (o FLY_CMD='...')"
		CMD_ARR=("$FLY_PYTHON" -m src.main)
		FLY_CMD="$FLY_PYTHON -m src.main"
	fi

	TIMEOUT_PREFIX=()
	if command -v timeout >/dev/null 2>&1; then
		TIMEOUT_PREFIX=(timeout "$FLY_TIMEOUT")
	elif command -v gtimeout >/dev/null 2>&1; then
		TIMEOUT_PREFIX=(gtimeout "$FLY_TIMEOUT")
	fi

	TMP_DIR="$(mktemp -d)"
	trap 'rm -rf "$TMP_DIR"' EXIT
	OUT_FILE="$TMP_DIR/stdout"
	ERR_FILE="$TMP_DIR/stderr"
	CLEAN_FILE="$TMP_DIR/stdout_clean"

	V_PASS=0; V_FAIL=0; E_PASS=0; E_FAIL=0
	RAN_VALID=0; RAN_ERRORS=0
}

# ------------------------------------------------------------- cabecera ------
print_header() {  # $1 = subtítulo, $2 = valid | errors | all
	sep
	printf '%s%s%s\n' "$PINK" '███████╗██╗     ██╗   ██╗      ██╗███╗   ██╗' "$RESET"
	printf '%s%s%s\n' "$PINK" '██╔════╝██║     ╚██╗ ██╔╝      ██║████╗  ██║' "$RESET"
	printf '%s%s%s\n' "$PINK" '█████╗  ██║      ╚████╔╝ ███║  ██║██╔██╗ ██║' "$RESET"
	printf '%s%s%s\n' "$PINK" '██╔══╝  ██║       ╚██╔╝        ██║██║╚██╗██║' "$RESET"
	printf '%s%s%s\n' "$PINK" '██║     ███████╗   ██║         ██║██║ ╚████║' "$RESET"
	printf '%s%s%s\n' "$PINK" '╚═╝     ╚══════╝   ╚═╝         ╚═╝╚═╝  ╚═══╝' "$RESET"
	printf '        %s%s%s\n' "$STRONG" "$1" "$RESET"
	sep
	echo
	printf '%s[+]%s TARGET   : %s <mapa>   (en %s)\n' "$GREEN" "$RESET" "$FLY_CMD" "$FLY_DIR"
	case "$2" in
		valid)  printf '%s[+]%s MAPS     : %s\n' "$GREEN" "$RESET" "$MAPS_DIR" ;;
		errors) printf '%s[+]%s MAPS     : %s\n' "$GREEN" "$RESET" "$ERRORS_DIR" ;;
		all)
			printf '%s[+]%s MAPS     : %s\n' "$GREEN" "$RESET" "$MAPS_DIR"
			printf '%s[+]%s            %s\n' "$GREEN" "$RESET" "$ERRORS_DIR"
			;;
	esac
	printf '%s[+]%s TIMEOUT  : %ss por mapa\n' "$GREEN" "$RESET" "$FLY_TIMEOUT"
	echo
}

section() {
	sep
	printf ' %s%s%s\n' "$PINK" "$1" "$RESET"
	sep
	echo
}

# --------------------------------------------------------- descripciones -----
describe() {  # $1 = clave del mapa, $2 = texto por defecto
	local key=$1 default=$2 found=""
	if [ -f "$DESC_FILE" ]; then
		found="$(awk -v k="$key" '
			/^[[:space:]]*#/ { next }
			{
				i = index($0, " = ")
				if (i == 0) next
				if (substr($0, 1, i - 1) == k) { print substr($0, i + 3); exit }
			}' "$DESC_FILE")"
	fi
	printf '%s' "${found:-$default}"
}

# ------------------------------------------------------ ejecutar un mapa -----
run_map() {  # $1 = ruta absoluta del mapa  ->  RC, OUT_FILE, ERR_FILE
	local map=$1
	(
		cd "$FLY_DIR" &&
		${TIMEOUT_PREFIX[@]+"${TIMEOUT_PREFIX[@]}"} "${CMD_ARR[@]}" "$map"
	) >"$OUT_FILE" 2>"$ERR_FILE" </dev/null
	RC=$?
}

first_line() { head -n 1 "$1" | tr -d '\r' | cut -c1-100; }

# ------------------------------------------------------------ resultados -----
DETAIL=""; FAIL_DETAIL=""; MAP_FAILED=0

reset_checks() { DETAIL=""; FAIL_DETAIL=""; MAP_FAILED=0; }

pass_check() {
	DETAIL+="$(printf '  %s✓%s %s' "$GREEN" "$RESET" "$1")"$'\n'
}

fail_check() {
	local line
	line="$(printf '  %s✗%s %s' "$RED" "$RESET" "$1")"
	DETAIL+="$line"$'\n'
	FAIL_DETAIL+="$line"$'\n'
	MAP_FAILED=1
}

timed_out() {
	[ "$RC" -eq 124 ] && [ "${#TIMEOUT_PREFIX[@]}" -gt 0 ]
}

# ---- criterios compartidos ---------------------------------------------------
check_no_traceback() {
	if grep -q 'Traceback (most recent call last)' "$OUT_FILE" "$ERR_FILE"; then
		local exc
		exc="$(grep -v '^[[:space:]]' "$ERR_FILE" | tail -n 1 | cut -c1-100)"
		fail_check "traceback detectado: $exc"
	else
		pass_check "sin traceback"
	fi
}

# ---- criterios de mapas válidos ----------------------------------------------
check_exit_zero() {
	if timed_out; then
		fail_check "timeout: más de ${FLY_TIMEOUT}s sin terminar"
	elif [ "$RC" -eq 0 ]; then
		pass_check "exit code: 0"
	else
		fail_check "exit code: $RC (esperado 0)"
	fi
}

check_stderr_empty() {
	if [ -s "$ERR_FILE" ]; then
		fail_check "stderr no vacío: $(first_line "$ERR_FILE")"
	else
		pass_check "stderr vacío"
	fi
}

check_stdout_format() {
	local lines bad
	sed "s/${ESC}\[[0-9;]*m//g" "$OUT_FILE" >"$CLEAN_FILE"
	lines="$(awk 'END { print NR }' "$CLEAN_FILE")"
	if [ "$lines" -eq 0 ]; then
		fail_check "stdout vacío (se esperaba al menos un turno)"
		return
	fi
	bad="$(awk '
		NF == 0 { print NR ": (línea vacía)"; exit }
		{
			for (i = 1; i <= NF; i++)
				if ($i !~ /^D[0-9]+-[^ ]+$/) { print NR ": " $0; exit }
		}' "$CLEAN_FILE" | cut -c1-100)"
	if [ -n "$bad" ]; then
		fail_check "stdout, formato inválido en la línea $bad"
	else
		pass_check "stdout: $lines líneas (turnos), todos los tokens D<n>-<zona>"
	fi
}

# ---- criterios de mapas inválidos --------------------------------------------
check_exit_nonzero() {
	if timed_out; then
		fail_check "timeout: más de ${FLY_TIMEOUT}s sin terminar"
	elif [ "$RC" -eq 0 ]; then
		fail_check "exit code: 0 (el mapa fue aceptado)"
	else
		pass_check "exit code: $RC"
	fi
}

check_stderr_message() {
	if [ -s "$ERR_FILE" ]; then
		pass_check "stderr: $(first_line "$ERR_FILE")"
	else
		fail_check "stderr vacío (falta el mensaje de error)"
	fi
}

check_stdout_empty() {
	if [ -s "$OUT_FILE" ]; then
		fail_check "stdout no vacío: $(first_line "$OUT_FILE")"
	else
		pass_check "stdout vacío"
	fi
}

# ------------------------------------------------------------ un mapa --------
print_expected() {  # $1 = valid | error
	printf '%sOutput esperado:%s\n' "$GOLD" "$RESET"
	if [ "$1" = valid ]; then
		printf '  %s·%s exit code 0\n' "$LILAC" "$RESET"
		printf '  %s·%s stderr vacío\n' "$LILAC" "$RESET"
		printf '  %s·%s sin traceback\n' "$LILAC" "$RESET"
		printf '  %s·%s stdout: una línea por turno, cada token D<n>-<zona>\n' "$LILAC" "$RESET"
	else
		printf '  %s·%s exit code distinto de 0\n' "$LILAC" "$RESET"
		printf '  %s·%s mensaje de error en stderr\n' "$LILAC" "$RESET"
		printf '  %s·%s sin traceback\n' "$LILAC" "$RESET"
		printf '  %s·%s stdout vacío\n' "$LILAC" "$RESET"
	fi
}

run_one() {  # $1 = valid | error, $2 = ruta absoluta, $3 = nombre a mostrar
	local kind=$1 map=$2 key=$3 default desc

	reset_checks
	run_map "$map"

	if [ "$kind" = valid ]; then
		default="Mapa válido: debe simularse hasta entregar los drones"
		check_exit_zero
		check_stderr_empty
		check_no_traceback
		check_stdout_format
	else
		default="Mapa inválido: debe rechazarse con un error controlado"
		check_exit_nonzero
		check_stderr_message
		check_no_traceback
		check_stdout_empty
	fi
	desc="$(describe "$key" "$default")"

	if [ "$QUIET" -eq 1 ]; then
		if [ "$MAP_FAILED" -eq 0 ]; then
			printf '  %s[PASS]%s %s\n' "$GREEN" "$RESET" "$key"
		else
			printf '  %s[FAIL]%s %s — %s\n' "$RED" "$RESET" "$key" "$desc"
			printf '%s' "$FAIL_DETAIL"
		fi
	else
		printf '%sMapa:%s %s\n' "$GOLD" "$RESET" "$key"
		printf '%sPrueba:%s %s\n' "$GOLD" "$RESET" "$desc"
		print_expected "$kind"
		printf '%sOutput obtenido:%s\n' "$GOLD" "$RESET"
		printf '%s' "$DETAIL"
		if [ "$MAP_FAILED" -eq 0 ]; then
			printf '  %s[PASS]%s\n' "$GREEN" "$RESET"
		else
			printf '  %s[FAIL]%s\n' "$RED" "$RESET"
		fi
		dash
	fi

	if [ "$kind" = valid ]; then
		if [ "$MAP_FAILED" -eq 0 ]; then V_PASS=$((V_PASS + 1)); else V_FAIL=$((V_FAIL + 1)); fi
	else
		if [ "$MAP_FAILED" -eq 0 ]; then E_PASS=$((E_PASS + 1)); else E_FAIL=$((E_FAIL + 1)); fi
	fi
}

# ------------------------------------------------------------- listados ------
# Orden de los válidos: easy, medium, hard, otras carpetas, challenger.
list_valid_maps() {
	find "$MAPS_DIR" -type f -name '*.txt' | awk -F/ '
		{
			d = $(NF - 1)
			r = (d == "easy") ? 1 : (d == "medium") ? 2 : (d == "hard") ? 3 : (d == "challenger") ? 5 : 4
			print r "\t" $0
		}' | sort -t "$TAB" -k1,1n -k2,2 | cut -f2-
}

list_error_maps() {
	find "$ERRORS_DIR" -maxdepth 1 -type f -name '*.txt' | sort
}

# --------------------------------------------------------------- suites ------
run_valid_suite() {
	local map total=0
	MAPS_DIR="$(abs_dir "$MAPS_DIR")"
	[ -n "$MAPS_DIR" ] || die "carpeta de mapas válidos no encontrada" \
		"usa: MAPS_DIR=/ruta/a/maps bash $0"
	RAN_VALID=1

	section "MAPAS VÁLIDOS"
	while IFS= read -r map; do
		[ -n "$map" ] || continue
		total=$((total + 1))
		run_one valid "$map" "${map#"$MAPS_DIR"/}"
	done < <(list_valid_maps)
	if [ "$total" -eq 0 ]; then
		printf '%s[WARN]%s no se encontró ningún .txt en %s\n' "$RED" "$RESET" "$MAPS_DIR"
	fi
	echo
}

run_error_suite() {
	local map total=0
	ERRORS_DIR="$(abs_dir "$ERRORS_DIR")"
	[ -n "$ERRORS_DIR" ] || die "carpeta de mapas inválidos no encontrada" \
		"usa: ERRORS_DIR=/ruta/a/maps_errors bash $0"
	RAN_ERRORS=1

	section "MAPAS INVÁLIDOS"
	while IFS= read -r map; do
		[ -n "$map" ] || continue
		total=$((total + 1))
		run_one error "$map" "$(basename "$map")"
	done < <(list_error_maps)
	if [ "$total" -eq 0 ]; then
		printf '%s[WARN]%s no se encontró ningún .txt en %s\n' "$RED" "$RESET" "$ERRORS_DIR"
	fi
	echo
}

# ------------------------------------------------------------- resumen -------
print_results() {
	local pass=0 fail=0 rate

	sep
	printf ' %sFINAL TEST RESULTS%s\n' "$PINK" "$RESET"
	sep
	echo
	if [ "$RAN_VALID" -eq 1 ]; then
		printf '  %-16s: %s / %s pasan\n' "MAPAS VÁLIDOS" "$V_PASS" "$((V_PASS + V_FAIL))"
		pass=$((pass + V_PASS)); fail=$((fail + V_FAIL))
	fi
	if [ "$RAN_ERRORS" -eq 1 ]; then
		printf '  %-16s: %s / %s pasan\n' "MAPAS INVÁLIDOS" "$E_PASS" "$((E_PASS + E_FAIL))"
		pass=$((pass + E_PASS)); fail=$((fail + E_FAIL))
	fi
	echo
	printf '  TOTAL TESTS RAN : [ %s ]\n' "$((pass + fail))"
	printf '  PASSED          : [ %s%s%s ]\n' "$GREEN" "$pass" "$RESET"
	printf '  FAILED          : [ %s%s%s ]\n' "$RED" "$fail" "$RESET"
	if [ $((pass + fail)) -gt 0 ]; then
		rate="$(awk -v p="$pass" -v f="$fail" 'BEGIN { printf "%.1f%%", p * 100 / (p + f) }')"
	else
		rate="-"
	fi
	printf '  SUCCESS RATE    : [ %s%s%s ]\n' "$GOLD" "$rate" "$RESET"
	echo
	if [ "$fail" -gt 0 ]; then
		printf '  %sSTATUS          : Algún mapa no cumplió los criterios (revisa los [FAIL] de arriba).%s\n' "$RED" "$RESET"
	else
		printf '  %sSTATUS          : Todos los mapas se comportaron como se esperaba.%s\n' "$GREEN" "$RESET"
	fi
	echo

	FINAL_FAILS="$fail"
}

finish() {
	if [ "${FINAL_FAILS:-0}" -gt 0 ]; then
		exit 1
	fi
	exit 0
}