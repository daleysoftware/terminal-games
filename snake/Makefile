PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python

.DEFAULT_GOAL := run

.PHONY: setup run clean

setup: $(VENV_PYTHON)

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

run: setup
	$(VENV_PYTHON) main.py

clean:
	rm -rf $(VENV) __pycache__
