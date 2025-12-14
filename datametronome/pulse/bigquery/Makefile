.PHONY: install test lint format clean build publish

install:
	pip install -e .
	pip install -r requirements-test.txt

test:
	pytest tests/ -v

lint:
	black --check metronome_pulse_bigquery/
	isort --check-only metronome_pulse_bigquery/
	mypy metronome_pulse_bigquery/

format:
	black metronome_pulse_bigquery/
	isort metronome_pulse_bigquery/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

publish: build
	python -m twine upload dist/*
