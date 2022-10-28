from importlib.metadata import entry_points
from setuptools import setup
from setuptools import find_packages


VERSION = '0.1.0'

setup(
    name='Valuation Report Parser',  # package name
    version=VERSION,  # package version
    author="fengbing",
    author_email="fengbing@iquantex.com",
    description='Valuation report parse tool.',  # package description
    packages=find_packages(),
    entry_points={
        'console_scripts': ['vrp=app.run:main'],
    },
)
