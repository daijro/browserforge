
lint_fix:
	PYTHONUTF8=1 docconvert --in-place --config docconvert_config.json --output google browserforge
	PYTHONUTF8=1 docconvert --in-place --config docconvert_config.json --output google tests
	docformatter --config pyproject.toml --black --in-place --recursive browserforge/ tests/|| echo ""
	poetry run black browserforge/ tests/
	poetry run isort browserforge/ tests/

lint:
	poetry check
	poetry run mypy browserforge/ tests/
	poetry run flake8 browserforge/ tests/
