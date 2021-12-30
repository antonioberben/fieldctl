update-environment:
	conda env update -f environment.yml

activate-environment:
	@echo conda activate fieldctl

bin-build:
	rm -rf dist build
	pyinstaller cli.py --add-data binaries:binaries --add-data provision:provision -F
	chmod +x ./dist/cli

bin-mv:
	cp ./dist/cli /usr/local/bin/solofectl

remove-pycache:
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete