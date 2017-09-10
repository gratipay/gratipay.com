python := "$(shell { command -v python2.7 || command -v python; } 2>/dev/null)"

# Set the relative path to installed binaries under the project virtualenv.
# NOTE: Creating a virtualenv on Windows places binaries in the 'Scripts' directory.
bin_dir := $(shell $(python) -c 'import sys; bin = "Scripts" if sys.platform == "win32" else "bin"; print(bin)')
env_bin := env/$(bin_dir)
venv := "./vendor/virtualenv-15.1.0.py"
doc_env_files := defaults.env,docs/doc.env,docs/local.env
test_env_files := defaults.env,local.env,tests/defaults.env,tests/local.env
pip := $(env_bin)/pip
honcho := $(env_bin)/honcho
honcho_run := $(honcho) run -e defaults.env,local.env
py_test := $(honcho) run -e $(test_env_files) $(env_bin)/py.test --tb=native --capture=sys

ifdef ARGS
	py_test_args = $(ARGS)
else
	py_test_args = tests deploy
endif


# Basic building and cleaning.

env: requirements.txt requirements.dev.txt setup.py
	$(python) $(venv) \
				--prompt="[gratipay] " \
				--extra-search-dir=./vendor/ \
				--always-copy \
				./env/
	$(pip) install --no-index -r requirements.txt
	$(pip) install --no-index -r requirements.dev.txt
	touch env

clean:
	rm -rf env *.egg *.egg-info
	find . -name \*.pyc -delete


# Schema-related

schema: env
	$(honcho_run) ./recreate-schema.sh 2>&1 | tee make-schema.log
	@echo 'P.S. Log is in make-schema.log'

test-schema: env
	$(honcho) run -e $(test_env_files) ./recreate-schema.sh 2>&1 | tee make-test-schema.log
	@echo 'P.S. Log is in make-test-schema.log'

fake:
	$(honcho_run) $(env_bin)/fake-data


# Launching a server

run: env
	PATH=$(env_bin):$(PATH) $(honcho_run) web

bgrun: env
	PATH=$(env_bin):$(PATH) $(honcho_run) web > /dev/null 2>&1 &

stop:
	pkill gunicorn


# Testing and linting

test:
	@$(MAKE) --no-print-directory flake
	$(py_test) $(py_test_args)

retest: env
	@$(MAKE) --no-print-directory flake
	$(py_test) --lf $(py_test_args)

flake: env
	$(env_bin)/pyflakes *.py bin gratipay tests deploy


# Internationalization

transifexrc:
	@echo '[https://www.transifex.com]' > .transifexrc
	@echo 'hostname = https://www.transifex.com' >> .transifexrc
	@echo "password = $$TRANSIFEX_PASS" >> .transifexrc
	@echo 'token = ' >> .transifexrc
	@echo "username = $$TRANSIFEX_USER" >> .transifexrc

tx:
	@if [ ! -x $(env_bin)/tx ]; then $(env_bin)/pip install transifex-client; fi

i18n: env tx
	$(env_bin)/pybabel extract -F .babel_extract --no-wrap -o i18n/core.pot emails gratipay templates www

i18n_upload: i18n
	$(env_bin)/tx push -s
	rm i18n/*.pot

i18n_download: env tx
	$(env_bin)/tx pull -a -f --mode=reviewed --minimum-perc=50
	@for f in i18n/*/*.po; do \
	    sed -E -e '/^"POT?-[^-]+-Date: /d' \
	           -e '/^"Last-Translator: /d' \
	           -e '/^#: /d' "$$f" >"$$f.new"; \
	    mv "$$f.new" "$$f"; \
	done


# Docs

doc: env
	$(honcho) run -e $(doc_env_files) make -C docs rst html

docserve:
	cd docs/_build/html && ../../../$(env_bin)/python -m SimpleHTTPServer
