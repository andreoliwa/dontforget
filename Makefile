APP_NAME = dontforget
BIN_DIR = $(HOME)/.local/bin

help: # Display this help
	@echo 'Choose one of the following targets:'
	@egrep '^[a-z0-9 ./-]*:.*#' $(lastword $(MAKEFILE_LIST)) | sed -E -e 's/:.+# */@ /g' -e 's/ .+@/@/g' | sort | awk -F@ '{printf "  \033[1;34m%-10s\033[0m %s\n", $$1, $$2}'
.PHONY: help

install: # Install the project on ~/.local/bin using pipx
ifeq ($(strip $(shell echo $(PATH) | grep $(BIN_DIR) -o)),)
	@echo "The directory $(BIN_DIR) should be in the PATH for this to work. Change your .bashrc or similar file."
	@exit -1
endif
	poetry install

	pipx uninstall dontforget
	pipx install --verbose .
.PHONY: install

update: # Update the project
	poetry update
.PHONY: pre-commit

pre-commit: # Install pre-commit hooks
	pre-commit install --install-hooks
	pre-commit install --hook-type commit-msg
	pre-commit gc
.PHONY: pre-commit

build: # Build the project; all these commands below should work (there is no test coverage... ¯\_(ツ)_/¯).
	clear
	pre-commit run --all-files
	poetry run python -m pytest
	poetry run pipe ls
	poetry run pipe run weekly
.PHONY: build
