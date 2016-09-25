# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='Shut That Bird Up',
    version='1.0.0',
    description='Archives and removes your Twitter tweets.',
    long_description=readme,
    author='Petar Petrov',
    author_email='',
    url='',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)
