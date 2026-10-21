PYTHON ?= python3

.DEFAULT_GOAL := test

.PHONY: test

test:
	PYTHONPATH=$(CURDIR) $(PYTHON) -m unittest discover -s terminal_games/tests -v
