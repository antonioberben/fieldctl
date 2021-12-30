# mesh tester

## Contribute

Note: Files named __init__.py are used to mark directories on disk as Python package directories.

## Build teh environment

With conda:
```bash
conda env create -f environment.yml
```

Pytest tutorial
https://semaphoreci.com/community/tutorials/testing-python-applications-with-pytest


Create binery
pyinstaller main.py --add-binary vcluster:. -F