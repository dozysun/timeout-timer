"""Setuptools entry point."""
import os

from setuptools import setup

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3 :: Only'
]


def long_description():
    with open(os.path.abspath(os.path.join(os.path.dirname(__file__), 'README.rst'))) as f:
        return f.read()


setup(
    name='timeout-timer',
    version='0.2.0',
    description='Timeout timer use signal or thread module, support nested loop',
    long_description=long_description(),
    author='dozysun',
    author_email='dozysun@gmail.com',
    url='https://github.com/dozysun/timeout-timer',
    packages=['timeout_timer'],
    install_requires=[],
    classifiers=CLASSIFIERS)
