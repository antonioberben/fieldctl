from setuptools import setup

# This file is used to build the package in your local in order to create the autocomplete files

setup(
    name='fieldctl',
    version='0.1.0',
    py_modules=['fieldctl'],
    install_requires=[
        'Click',
    ],
    entry_points={
        'console_scripts': [
            'fieldctl = cli:cli',
        ],
    },
)