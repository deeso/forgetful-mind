#!/usr/bin/env python
from setuptools import setup, find_packages
# import os


# data_files = [(d, [os.path.join(d, f) for f in files])
#               for d, folders, files in os.walk(os.path.join('src', 'config'))]

DESC ='Inline Mongo DB capture'
setup(name='forgetful-mind',
      version='1.0',
      description=DESC,
      author='adam pridgen',
      author_email='dso@thecoverofnight.com',
      install_requires=['kombu', 'pymongo', 'toml', 'spoton-johny'],
      packages=find_packages('src'),
      package_dir={'': 'src'},
      dependency_links=[
        "https://github.com/deeso/spoton-johny/tarball/master#egg=spoton-johny-1.0.0"
      ]
)
