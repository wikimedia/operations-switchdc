#!/usr/bin/env python
"""Package configuration."""

from setuptools import find_packages, setup

test_requires = ['docker>=2.0', 'mock', 'nose']

setup(
    author='Riccardo Coccioli',
    author_email='rcoccioli@wikimedia.org',
    description='Datacenter switchover automation',
    entry_points={
        'console_scripts': [
            'switchdc = switchdc.switch:main',
        ],
    },
    extras_require={'test': test_requires},
    install_requires=['pyyaml',  'redis', 'requests', 'dnspython'],
    test_requires=test_requires,
    name='switchdc',
    packages=find_packages(),
    version='0.0.1',
    zip_safe=False,
)
