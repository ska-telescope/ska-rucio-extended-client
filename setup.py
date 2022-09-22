#!/usr/bin/env python

import glob

from setuptools import setup

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

data_files = [
    ('etc', 'etc'),
]
scripts = glob.glob('bin/rucio*')

setup(
    name='rucio_extended_client',
    version='0.1.0',
    description='',
    url='https://gitlab.com/ska-telescope/src/ska-rucio-extended-client',
    author='rob barnsley',
    author_email='rob.barnsley@skao.int',
    packages=['rucio_extended_client'],
    package_dir={'': 'src'},
    data_files=data_files,
    scripts=scripts,
    include_package_data=True,
    install_requires=requirements,
    classifiers=[]
)