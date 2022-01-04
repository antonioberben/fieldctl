update-environment:
	conda env update -f environment.yml

activate-environment:
	@echo conda activate fieldctl

bin-build:
	rm -rf dist build
	pyinstaller cli.py --name fieldctl --add-data provision:provision -F
	chmod +x ./dist/fieldctl

remove-pycache:
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete
	
download-release:
	wget -O fieldctl https://github.com/antonioberben/fieldctl/releases/download/$$FIELD_VERSION/fieldctl-darwin-amd64
	chmod +x fieldctl