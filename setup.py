from setuptools import setup

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