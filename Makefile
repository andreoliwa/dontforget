.PHONY: Makefile

BIN_DIR = ~/.local/bin

help:
	@echo 'Choose one of the following targets:'
	@cat $(MAKEFILE_LIST) | egrep '^[a-z0-9 ./-]*:.*#' | sed -E -e 's/:.+# */@ /g' -e 's/ .+@/@/g' | sort | awk -F@ '{printf "  \033[1;34m%-10s\033[0m %s\n", $$1, $$2}'
.PHONY: help

install:
	poetry install
	@echo "The directory $(BIN_DIR) should be in the PATH for this to work. If not, change your .bashrc or similar file:"
	@echo PATH=$(PATH)

	mkdir -p $(BIN_DIR)
	rm -f $(BIN_DIR)/dontforget
	echo "#!/usr/bin/env bash" > $(BIN_DIR)/dontforget
	echo "cd $(PWD)" >> $(BIN_DIR)/dontforget
	echo "poetry run dontforget" >> $(BIN_DIR)/dontforget
	chmod +x $(BIN_DIR)/dontforget

	@echo "The script was created in:"
	@which dontforget

dev:
	clear
	pre-commit run --all-files
	pytest
