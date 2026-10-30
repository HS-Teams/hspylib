#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib
      @file: setup.py
   @created: Tue, 4 May 2021
    @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: https://github.com/yorevs/hspylib
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib
"""

import pathlib
import setuptools

HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# The version of the package
VERSION = (HERE / "hspylib/.version").read_text().strip()

# The package requirements
REQUIREMENTS = list(filter(None, (HERE / "requirements.txt").read_text().splitlines()))

# This call to setup() does all the work
setuptools.setup(
    name="hspylib",
    version=VERSION,
    description="HsPyLib - Core python library",
    author="Hugo Saporetti Junior",
    author_email="yorevs@hotmail.com",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/yorevs/hspylib",
    project_urls={"GitHub": "https://github.com/yorevs/hspylib", "PyPi": "https://pypi.org/project/hspylib/"},
    license="MIT",
    license_files="LICENSE.md",
    packages=setuptools.find_namespace_packages(include=["hspylib", "hspylib.*"]),
    package_dir={"": "."},
    include_package_data=True,
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Unix",
        "Development Status :: 4 - Beta",
        "Natural Language :: English",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Intended Audience :: Developers",
    ],
    python_requires=">=3.10",
    install_requires=REQUIREMENTS,
    keywords="python,library,solid,patterns,development,integration,application,framework",
    platforms="Darwin,Linux",
)
