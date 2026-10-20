PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python

.DEFAULT_GOAL := run

.PHONY: setup run test clean

setup: $(VENV_PYTHON)

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

run: setup
	$(VENV_PYTHON) main.py

test: setup
	@if [ -d tests ]; then $(VENV_PYTHON) -m unittest discover -s tests -v; else echo "No tests yet."; fi

clean:
	rm -rf $(VENV) __pycache__ tests/__pycache__
