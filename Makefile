.PHONY: Makefile

BIN_DIR = $(HOME)/.local/bin

help: # Display this help
	@echo 'Choose one of the following targets:'
	@cat $(MAKEFILE_LIST) | egrep '^[a-z0-9 ./-]*:.*#' | sed -E -e 's/:.+# */@ /g' -e 's/ .+@/@/g' | sort | awk -F@ '{printf "  \033[1;34m%-10s\033[0m %s\n", $$1, $$2}'
.PHONY: help

install: # Install the project on ~/.local/bin
ifeq ($(strip $(shell echo $(PATH) | grep $(BIN_DIR) -o)),)
	@echo "The directory $(BIN_DIR) should be in the PATH for this to work. Change your .bashrc or similar file."
	@exit -1
endif
	poetry install

	mkdir -p $(BIN_DIR)
	rm -f $(BIN_DIR)/dontforget
	echo "#!/usr/bin/env bash" > $(BIN_DIR)/dontforget
	echo "cd $(PWD)" >> $(BIN_DIR)/dontforget
	echo "poetry run dontforget \$$*" >> $(BIN_DIR)/dontforget
	chmod +x $(BIN_DIR)/dontforget

	@echo "The script was created in:"
	@which dontforget

setup: # Install dev dependencies
	pre-commit install --install-hooks
	pre-commit install --hook-type commit-msg

build: # Build the project
	clear
	pre-commit run --all-files
	# TODO: tests failing because they can't connect to Postgres
#	poetry run pytest
