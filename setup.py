# -*- coding: utf-8 -*-
"""
Setup for pycaz

@author: khan
"""

import setuptools

setuptools.setup(
    name='bandsos',
    author='Jamal Khan',
    author_email='4151009+jamal919@users.noreply.github.com',
    description='BandSOS platform for storm surge modelling',
    packages=setuptools.find_packages(),
    license='GPL v3',
    setup_requires=['setuptools-git-versioning', 'setuptools_scm'],
    setuptools_git_versioning={
        "enabled": True,
        "template": "{tag}",
        "dev_template": "{tag}.post{ccount}+git.{sha}",
        "dirty_template": "{tag}.post{ccount}+git.{sha}.dirty",
        "starting_version": "0.1"
    },
    use_scm_version=True,
    python_requires='>=3.7',
    install_requires=[
        'numpy',
        'scipy',
        'matplotlib',
        'pandas',
        'xarray',
        'utide',
        'cmocean',
        'rioxarray'
    ],
    include_package_data=True,
    url="https://github.com/jamal919/bandsos",
    long_description=open('README.md').read()
)