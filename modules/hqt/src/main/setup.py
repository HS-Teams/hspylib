#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib-Hqt
      @file: setup.py
   @created: Tue, 18 Apr 2023
    @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: https://github.com/yorevs/hspylib
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib

   Reference: https://setuptools.pypa.io/en/latest/references/keywords.html
"""

import pathlib
import setuptools

HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# The version of the package
VERSION = (HERE / "hqt/.version").read_text().strip()

# The package requirements
REQUIREMENTS = list(filter(None, (HERE / "requirements.txt").read_text().splitlines()))

# This call to setup() does all the work
setuptools.setup(
    name="hspylib-hqt",
    version=VERSION,
    description="HsPyLib - QT framework extensions",
    author="Hugo Saporetti Junior",
    author_email="yorevs@hotmail.com",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/yorevs/hspylib",
    project_urls={"GitHub": "https://github.com/yorevs/hspylib", "PyPi": "https://pypi.org/project/hspylib-hqt/"},
    license="MIT",
    license_files="LICENSE.md",
    packages=setuptools.find_namespace_packages(include=["hqt", "hqt.*"]),
    package_dir={"": "."},
    include_package_data=True,
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Unix",
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Natural Language :: English",
        "Topic :: Terminals",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Intended Audience :: Developers",
    ],
    python_requires=">=3.10",
    install_requires=REQUIREMENTS,
    keywords="qt,ui,extensions,application,pyqt",
    platforms="Darwin,Linux",
)
