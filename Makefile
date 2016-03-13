.PHONY: test fasttest run lint pep8 eslint manage report_failed_tests

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

# Gunicorn settings
GUNICORN_NAME ?= myezh
GUNICORN_WORKERS ?= $(shell python -c "import multiprocessing; print(multiprocessing.cpu_count() * 2 + 1);")
LOGS_DIR ?= ./logs
SERVER_HOST ?= 0.0.0.0
SERVER_PORT ?= 8008

# Other settings
DJANGO_SERVER ?= runserver
DJANGO_SHELL ?= shell_plus

# Setup bootstrapper & Gunicorn args
has_bootstrapper = $(shell python -m bootstrapper --version 2>&1 | grep -v "No module")
ifeq ($(LEVEL),development)
	bootstrapper_args = -d
	gunicorn_args = --reload
	requirements = -r requirements.txt -r requirements-dev.txt
else
	gunicorn_args = --access-logfile=$(LOGS_DIR)/gunicorn.access.log \
	--error-logfile=$(LOGS_DIR)/gunicorn.error.log
	requirements = -r requirements.txt
endif

# Enable to install packages from non-HTTPS private PyPI
PIP_TRUSTED_HOST ?= pypi.ezhome.io


# Clean from temporary files
clean:
	find ./$(PROJECT)/ $(ENV) -name "*.pyc" -o -type d -empty -exec rm -rf {} +

# Easy testing
test: clean pep8
	$(COVERAGE) run --branch ./$(PROJECT)/manage.py test $(TEST_ARGS)
	$(COVERAGE) report

# Fast testing
fasttest:
	REUSE_DB=1 $(MAKE) test

# Run server
run:
	python manage.py runserver $(SERVER_HOST):$(SERVER_PORT)

install: install-github-key install-py install-static

install-github-key:
	ssh-keygen -H -F github.com > /dev/null || ssh-keyscan -H github.com >> ~/.ssh/known_hosts

install-py:
ifneq ($(has_bootstrapper),)
	PIP_TRUSTED_HOST=$(PIP_TRUSTED_HOST) python -m bootstrapper -e $(ENV)/ $(bootstrapper_args)
else
	[ ! -d "$(ENV)/" ] && virtualenv $(ENV)/ || :
	PIP_TRUSTED_HOST=$(PIP_TRUSTED_HOST) $(ENV)/bin/pip install $(requirements)
endif

install-static:
	npm install
# 	bower install
# ifneq ($(CIRCLECI),)
# 	-bower update
# else
# 	bower update
# endif

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

# Wrapper around manage command
manage:
	$(PYTHON) ./$(PROJECT)/manage.py $(COMMAND)

# Development Server
devserver: clean
	COMMAND="$(DJANGO_SERVER) $(SERVER_HOST):$(SERVER_PORT)" $(MAKE) manage

# Production Server
server: clean pep8
	LEVEL=$(LEVEL) PYTHONPATH=$(PROJECT) $(GUNICORN) -b $(SERVER_HOST):$(SERVER_PORT) -w $(GUNICORN_WORKERS) -n $(GUNICORN_NAME) -t 60 --graceful-timeout 60 $(gunicorn_args) $(GUNICORN_ARGS) $(PROJECT).wsgi:application

# Reporting of failed cases:
jira_check_tests:
	ezh-jira-test-checker run_check $(COMMAND_ARGS)
