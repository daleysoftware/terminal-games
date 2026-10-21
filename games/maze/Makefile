PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
export PYTHONPATH := $(abspath ../../lib):$(PYTHONPATH)

.DEFAULT_GOAL := test

.PHONY: setup run test clean

setup: $(VENV_PYTHON)

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

run: setup
	$(VENV_PYTHON) main.py

test: setup
	$(VENV_PYTHON) -m unittest discover -s tests -v

clean:
	rm -rf $(VENV) __pycache__ tests/__pycache__
