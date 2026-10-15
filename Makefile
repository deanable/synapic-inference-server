.PHONY: test run build clean

test:
	python -m pytest -q

run:
	python src/Synapic.Inference/service.py

build:
	python -m PyInstaller --clean src/Synapic.Inference/synapic-inference.spec

clean:
	rm -rf build dist .pytest_cache
