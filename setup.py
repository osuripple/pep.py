"""Cython build file"""
from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize

setup(
    name = "pep.pyx modules",
    ext_modules = cythonize([
        Extension("helpers.packetHelper", ["helpers/packetHelper.pyx"]),
    ],
    nthreads = 4),
)