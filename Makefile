update-environment:
	conda env update -f environment.yml

activate-environment:
	@echo conda activate fieldctl

bin-build:
	rm -rf dist build
	pyinstaller cli.py --name fieldctl --add-data binaries:binaries --add-data provision:provision -F
	chmod +x ./dist/fieldctl

remove-pycache:
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete