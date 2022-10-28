import imp
from setuptools import setup
from setuptools import find_packages
from run import __version__


setup(
    name='Valuation Report Parser',  # package name
    version=__version__,  # package version
    author="fengbing",
    author_email="fengbing@iquantex.com",
    description='Valuation report parse tool.',  # package description
    py_modules=["run"],
    packages=find_packages(),
    entry_points={
        'console_scripts': ['vrp=run:main'],
    },
)
