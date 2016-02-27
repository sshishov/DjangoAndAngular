.PHONY: test fasttest run lint pep8 eslint

# Project settings
LEVEL ?= development
PROJECT = src

# Virtual environment settings
ENV ?= ./venv
VENV = $(shell python -c "import sys; print(int(hasattr(sys, 'real_prefix')));")

# Python commands
ifeq ($(VENV),1)
	ANSIBLE_PLAYBOOK = ansible-playbook
	COVERAGE = coverage
	FLAKE8 = flake8
	GUNICORN = gunicorn
	PYTHON = python
else
	ANSIBLE_PLAYBOOK = $(ENV)/bin/ansible-playbook
	COVERAGE = ${ENV}/bin/coverage
	FLAKE8 = $(ENV)/bin/flake8
	GUNICORN = $(ENV)/bin/gunicorn
	PYTHON = $(ENV)/bin/python
endif

SERVER_HOST ?= 0.0.0.0
SERVER_PORT ?= 8000

# Easy testing
test:
	python manage.py test

# Fast testing
fasttest:
	REUSE_DB=1 $(MAKE) test

# Run server
run:
	python manage.py runserver $(SERVER_HOST):$(SERVER_PORT)

# Linter
lint: pep8

# PEP8 code style
pep8:
ifeq ($(LEVEL),development)
	$(FLAKE8) --statistics ./$(PROJECT)/
endif

# JavaScript linter
eslint:
ifeq ($(LEVEL),development)
	npm run lint
endif
