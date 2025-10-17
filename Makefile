APP_NAME = dontforget
BIN_DIR = $(HOME)/.local/bin
SDKROOT = /Library/Developer/CommandLineTools/SDKs/MacOSX10.15.sdk
CFLAGS = "-isysroot /Library/Developer/CommandLineTools/SDKs/MacOSX10.15.sdk"

.PHONY: help
help: # Display this help
	@cat Makefile | egrep '^[a-z0-9 ./-]*:.*#' | sed -E -e 's/:.+# */@ /g' -e 's/ .+@/@/g' | sort | awk -F@ '{printf "\033[1;34m%-15s\033[0m %s\n", $$1, $$2}'

.PHONY: build
build: # Build the project; all these commands below should work (there is no test coverage... ¯\_(ツ)_/¯).
	clear
	pre-commit run --all-files
	#poetry run python -m pytest
	poetry run dontforget pipe ls
	poetry run dontforget pipe run vila

.PHONY: dev
dev: # Setup the development environment
	pyenv local 3.13.8
	poetry env use python3.13
	poetry install

.PHONY: install
install: # Install the project on ~/.local/bin using pipx
ifeq ($(strip $(shell echo $(PATH) | grep $(BIN_DIR) -o)),)
	@echo "The directory $(BIN_DIR) should be in the PATH for this to work. Change your .bashrc or similar file."
	@exit -1
endif
	$(MAKE) dev
	-$(MAKE) uninstall
	pipx install --python python3.13 -e .

.PHONY: uninstall
uninstall: # Uninstall the project from ~/.local/bin using pipx
	-pipx uninstall dontforget

.PHONY: clib
clib: # Force a reinstall of the clib dependency; use when developing locally.
	poetry run pip uninstall --yes clib
	poetry install --no-root
