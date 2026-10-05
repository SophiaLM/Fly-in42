NAME = FLYIN

VENV       = venv
PYTHON     = $(VENV)/bin/python3
PIP        = $(VENV)/bin/pip

TEST_DIR    = ../test
FLY_PYTHON ?= $(abspath $(PYTHON))

PASTEL_PINK = \033[38;5;218m
PINK        = \033[38;5;218m
STRONG_PINK = \033[38;5;204m
LILAC       = \033[38;5;141m
RESET       = \033[0m

install: ## Crea el venv (si hace falta) e instala dependencias
	@if [ -d "$(VENV)/bin" ]; then \
		echo "$(PINK)Virtual environment ready $(RESET) $(STRONG_PINK)($(VENV))$(RESET)"; \
	else \
		echo "$(PINK)Creating virtual environment...$(RESET)"; \
		if [ -n "$(UV)" ]; then \
			uv venv $(VENV); \
		else \
			python3 -m venv $(VENV); \
		fi; \
		echo "$(PINK)Virtual environment created in $(RESET) $(STRONG_PINK)./$(VENV)$(RESET)"; \
	fi
	@echo "$(PINK)Installing dependencies...$(RESET)"
	@if [ -n "$(UV)" ]; then \
		uv pip install -r requirements.txt --python $(PYTHON); \
	else \
		$(PYTHON) -m pip install --upgrade pip --quiet; \
		$(PYTHON) -m pip install -r requirements.txt --quiet; \
	fi
	@echo "$(STRONG_PINK)Environment and dependencies ready!$(RESET)"
	@echo ""
	@echo " $(PINK)███████$(RESET)$(STRONG_PINK)╗$(RESET)$(PINK)██$(RESET)$(STRONG_PINK)╗$(RESET)  $(PINK)██$(RESET)$(STRONG_PINK)╗$(RESET)   $(PINK)██$(RESET)$(STRONG_PINK)╗$(RESET)      $(PINK)██$(RESET)$(STRONG_PINK)╗$(RESET)  $(PINK)███$(RESET)$(STRONG_PINK)╗$(RESET)   $(PINK)██$(RESET)$(STRONG_PINK)╗$(RESET)"
	@echo " $(PINK)██$(RESET)$(STRONG_PINK)╔════╝$(RESET)$(PINK)██$(RESET)$(STRONG_PINK)║$(RESET)  $(STRONG_PINK)╚$(RESET)$(PINK)██$(RESET)$(STRONG_PINK)╗$(RESET) $(PINK)██$(RESET)$(STRONG_PINK)╔╝$(RESET)      $(PINK)██$(RESET)$(STRONG_PINK)║$(RESET)  $(PINK)████$(RESET)$(STRONG_PINK)╗$(RESET)  $(PINK)██$(RESET)$(STRONG_PINK)║$(RESET)"
	@echo " $(PINK)█████$(RESET)$(STRONG_PINK)╗$(RESET)  $(PINK)██$(RESET)$(STRONG_PINK)║$(RESET)   $(STRONG_PINK)╚$(RESET)$(PINK)████$(RESET)$(STRONG_PINK)╔╝$(RESET) $(PINK)█████╗$(RESET)$(PINK)██$(RESET)$(STRONG_PINK)║$(RESET)  $(PINK)██$(RESET)$(STRONG_PINK)╔$(RESET)$(PINK)██$(RESET)$(STRONG_PINK)╗$(RESET) $(PINK)██$(RESET)$(STRONG_PINK)║$(RESET)"
	@echo " $(PINK)██$(RESET)$(STRONG_PINK)╔══╝$(RESET)  $(PINK)██$(RESET)$(STRONG_PINK)║$(RESET)    $(STRONG_PINK)╚$(RESET)$(PINK)██$(RESET)$(STRONG_PINK)╔╝$(RESET)  $(STRONG_PINK)╚════╝$(RESET)$(PINK)██$(RESET)$(STRONG_PINK)║$(RESET)  $(PINK)██$(RESET)$(STRONG_PINK)║$(RESET)$(STRONG_PINK)╚$(RESET)$(PINK)██$(RESET)$(STRONG_PINK)╗$(RESET)$(PINK)██$(RESET)$(STRONG_PINK)║$(RESET)"
	@echo " $(PINK)██$(RESET)$(STRONG_PINK)║$(RESET)     $(PINK)███████$(RESET)$(STRONG_PINK)╗$(RESET)$(PINK)██$(RESET)$(STRONG_PINK)║$(RESET)         $(PINK)██$(RESET)$(STRONG_PINK)║$(RESET)  $(PINK)██$(RESET)$(STRONG_PINK)║$(RESET) $(STRONG_PINK)╚$(RESET)$(PINK)████$(RESET)$(STRONG_PINK)║$(RESET)"
	@echo " $(STRONG_PINK)╚═╝$(RESET)     $(STRONG_PINK)╚══════╝╚═╝         ╚═╝  ╚═╝  ╚═══╝$(RESET)"
	@echo ""
	@echo "$(STRONG_PINK)Python Binary :$(RESET) $(PYTHON)"
	@echo "$(STRONG_PINK)Python Version:$(RESET) $$($(PYTHON) --version)"
	@echo "$(STRONG_PINK)Virtual Env   :$(RESET) $$(if [ -d "venv" ]; then echo "Active 🟢$(RESET)"; else echo "$(STRONG_PINK)Missing 🔴$(RESET)"; fi)"

run: ## Ejecuta la aplicación principal (src/main.py)
	@$(PYTHON) -m src.main $(ARGS)

compile: ## Verifica y pre-compila los archivos .py a bytecode
	@$(PYTHON) -m py_compile $(shell find src -type f -name "*.py" 2>/dev/null)

lint: ## Ejecuta flake8 y mypy para analizar el código
	@$(PYTHON) -m flake8 . --exclude venv
	@$(PYTHON) -m mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs --exclude venv

test-all: _check-venv ## Prueba mapas válidos e inválidos
	@FLY_DIR="$(CURDIR)" FLY_PYTHON="$(FLY_PYTHON)" bash $(TEST_DIR)/run_all.sh $(ARGS)

test-valid: _check-venv ## Prueba solo los mapas válidos
	@FLY_DIR="$(CURDIR)" FLY_PYTHON="$(FLY_PYTHON)" bash $(TEST_DIR)/run_valid.sh $(ARGS)

test-errors: _check-venv ## Prueba solo los mapas inválidos
	@FLY_DIR="$(CURDIR)" FLY_PYTHON="$(FLY_PYTHON)" bash $(TEST_DIR)/run_errors.sh $(ARGS)

_check-venv:
	@test -x "$(PYTHON)" || { echo "$(STRONG_PINK)venv not found: run 'make install' first$(RESET)"; exit 2; }

clean:
	@echo "$(PINK)Cleaning up bytecode and caches...$(RESET)"
	@find . -name venv -prune -o -type d \( -name "__pycache__" -o -name ".mypy_cache" -o -name ".pytest_cache" \) -exec echo "$(LILAC)  [rm dir]  $(RESET) {}" \; -exec rm -rf {} +
	@find . -name venv -prune -o -type f \( -name "*.pyc" -o -name "*.pyo" -o -name "*:Zone.Identifier" \) -exec echo "$(STRONG_PINK)  [rm file] $(RESET) {}" \; -exec rm -f {} +
	@rm -rf .coverage htmlcov
	@echo "$(STRONG_PINK)✨ Everything is super clean!$(RESET)"

fclean: clean ## Limpieza profunda (incluye venv, reportes y archivos de compilación)
	@echo "$(PINK)Performing full cleanup (fclean)...$(RESET)"
	@if [ -d "venv" ]; then \
		echo "$(PINK)  [rm venv] $(RESET) Removing virtual environment ./venv..."; \
		rm -rf venv; \
	fi
	@find . -maxdepth 2 -type d -name "*.egg-info" -exec echo "$(LILAC)  [rm egg]  $(RESET) {}" \; -exec rm -rf {} +
	@if [ -f "coverage.xml" ]; then \
		echo "$(PINK)  [rm file] $(RESET) coverage.xml"; \
		rm -f coverage.xml; \
	fi
	@rm -rf .coverage htmlcov .ruff_cache
	@echo "$(STRONG_PINK)💥 Full cleanup completed! Virtualenv and build artifacts obliterated.$(RESET)"

debug:
	@$(PYTHON) -m pdb src/main.py $(ARGS)

status:
	@find . -name venv -prune -o -type d -name "__pycache__" -print
	@find . -name venv -prune -o -type f \( -name "*.pyc" -o -name "*:Zone.Identifier" \) -print
	@ls -d .mypy_cache .pytest_cache .coverage htmlcov 2>/dev/null || true

lint-strict:
	@$(PYTHON) -m flake8 . --exclude venv
	@$(PYTHON) -m mypy . --strict --exclude venv

help:
	@echo "$(STRONG_PINK)┌────────────────────────────────────────────────────────┐$(RESET)"
	@echo "$(STRONG_PINK)│               $(PINK)$(NAME) - COMMAND CENTER$(STRONG_PINK)                   │$(RESET)"
	@echo "$(STRONG_PINK)└────────────────────────────────────────────────────────┘$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(LILAC)❯ %-14s$(RESET) %s\n", $$1, $$2}'
	@echo ""

.PHONY: help install run compile debug clean status lint lint-strict fclean test-all test-valid test-errors _check-venv