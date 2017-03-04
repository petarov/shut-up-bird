# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='Shut Up Bird',
    version='1.0.0',
    description='Archives and removes your Twitter posts',
    long_description=readme,
    author='Petar Petrov',
    author_email='',
    url='',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)
