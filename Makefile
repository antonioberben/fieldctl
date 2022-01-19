update-environment:
	conda env update -f environment.yml

activate-environment:
	@echo conda activate fieldctl

bin-build:
	./calculate-version.sh
	rm -rf dist build
	pyinstaller cli.py --name fieldctl --add-data provision:provision --add-data version.txt:version.txt -F
	chmod +x ./dist/fieldctl

remove-pycache:
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete
	
download-release:
	wget -O fieldctl https://github.com/antonioberben/fieldctl/releases/download/$$FIELD_VERSION/fieldctl-darwin-amd64
	chmod +x fieldctl

generate-automcomplete-files:
	pip install --editable .
	_FIELDCTL_COMPLETE=zsh_source fieldctl > autocomplete/fieldctl-complete.zsh
	bash -c "_FIELDCTL_COMPLETE=bash_source fieldctl > autocomplete/fieldctl-complete.bash"
	fish -c "_FIELDCTL_COMPLETE=fish_source fieldctl > autocomplete/fieldctl-complete.fish"
	pip uninstall fieldctl