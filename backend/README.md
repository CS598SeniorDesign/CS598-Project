# Backend

This document provides guidance on running the backend

## Table of Contents

- [Backend](#backend)
  - [Table of Contents](#table-of-contents)
  - [Setup a python virtual environment](#setup-a-python-virtual-environment)
  - [Start Django](#start-django)
  - [Maintaining requirements](#maintaining-requirements)
    - [Adding requirements](#adding-requirements)
    - [Removing a package](#removing-a-package)
    - [Check for outdated packages](#check-for-outdated-packages)
    - [Upgrading packages](#upgrading-packages)

## Setup a python virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install pip-tools
pip-sync dev.txt
```

## Start Django

```bash
pip install pip-tools
pip-sync dev.txt
```

## Maintaining requirements

Requirements files can be found in the requirements directory.

The `base.txt` file contains libraries, packages, etc that are applicable to development and production environments.

`dev.txt` contains developement environment specific libraries and packages and `prod.in` contains production environment specifics.

### Adding requirements

To add new packages to requirements files

```bash
cd backend/
echo "newpackage" >> requirements/base.in # or /dev.in or /prod.in
pip-compile requirements/base.in -o requirements/base.txt # or /dev.in or /prod.in
pip-sync requirements/dev.txt
```

***NOTE: .txt files in the requirements directory should not be directly edited. Add new packages to the appropriate .in file and then compile the .txt file. If base.in is edited, all of the .txt files need to be recompiled***

### Removing a package

To remove a package, delete it from the appropriate .in file and then recompile all necessary .txt files

### Check for outdated packages

`pip list --outdated`

### Upgrading packages

- Single package: `pip-compile requirements/base.in -o requirements/base.txt --upgrade-package packagetoupgrade`
- All packages: `pip-compile requirements/base.in -o requirements/base.txt --upgrade`
