PYTHON ?= python3
GAME_DIRS := $(patsubst %/Makefile,%,$(wildcard */Makefile))

.DEFAULT_GOAL := test

.PHONY: test

test:
	@set -e; for game in $(GAME_DIRS); do $(MAKE) -C $$game test; done
