PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python

.PHONY: setup run test

setup: $(VENV_PYTHON)

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

run: setup
	$(VENV_PYTHON) main.py

test: setup
	$(VENV_PYTHON) -m unittest discover -s tests -v
