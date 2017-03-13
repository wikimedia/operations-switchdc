#!/usr/bin/env python
"""Package configuration."""

from setuptools import find_packages, setup

setup(
    author='Riccardo Coccioli',
    author_email='rcoccioli@wikimedia.org',
    description='Datacenter switchover automation',
    entry_points={
        'console_scripts': [
            'switchdc = switchdc.switch:main',
        ],
    },
    install_requires=['pyyaml'],
    name='switchdc',
    packages=find_packages(),
    version='0.0.1',
    zip_safe=False,
)
