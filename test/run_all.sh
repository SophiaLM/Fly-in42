#!/usr/bin/env bash
# =============================================================================
#  run_all.sh — prueba TODOS los mapas: primero los válidos y luego los
#  inválidos
#
#  Uso:  bash test/run_all.sh [-q]
# =============================================================================

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
	cat <<'EOF'
Uso: bash test/run_all.sh [-q] [-h]

  -q, --quiet   una línea por mapa (detalle solo si falla)
  -h, --help    esta ayuda

Variables opcionales: FLY_DIR, FLY_PYTHON, FLY_CMD, FLY_TIMEOUT, MAPS_DIR,
ERRORS_DIR, DESC_FILE, NO_COLOR (ver test/lib/common.sh).
EOF
}

# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

parse_args "$@"
setup_env
print_header "SUITE COMPLETA: VÁLIDOS + INVÁLIDOS" all
run_valid_suite
run_error_suite
print_results
finish
