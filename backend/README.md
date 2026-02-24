# Backend

This document provides guidance on running the backend

## Table of Contents

- [Backend](#backend)
  - [Table of Contents](#table-of-contents)
  - [Setup a python virtual environment](#setup-a-python-virtual-environment)
  - [Django](#django)
    - [Starting a Django server](#starting-a-django-server)
    - [Creating a new app](#creating-a-new-app)
    - [Updating Django models and schema](#updating-django-models-and-schema)
  - [Requirements](#requirements)
    - [Maintaining requirements](#maintaining-requirements)
    - [Adding requirements](#adding-requirements)
    - [Removing a package](#removing-a-package)
    - [Check for outdated packages](#check-for-outdated-packages)
    - [Upgrading packages](#upgrading-packages)

## Setup a python virtual environment

```bash
python -m venv .venv
source .venv/bin/activate # Linux/Mac
#.venv\Scripts\activate   # Windows
pip install pip-tools
pip-sync dev.txt
```

## Django

### Starting a Django server

```bash
cd backend
python manage.py migrate # This makes sure that your database is up to date with current schemas
python manage.py runserver # This will run the django server on localhost port 8000
# python manage.py runserver 8001 # This will run the django server on localhost port 8001
```

### Creating a new app

- Run in the backend directory:
    `python manage.py startapp appname`
- Add the app to `INSTALLED_APPS` in config/settings.py
- Create a urls.py file in your new app
- Add your app urls to config/urls.py

### Updating Django models and schema

When Django models are created or changed in any way, the schema for the database also needs to be updated. This is done through migrations.

Each app will have a migrations directory that contains all of the migrations which can be applied to existing and new databases. It is important to maintain the order of the migrations in each app as there may be dependencies that exist between the files.

```bash
cd backend
python manage.py makemigrations # Check for new migrations in all apps in the project
# python manage.py makemigrations app # Check for new migrations in a specific app in the project
python manage.py migrate
```

## Requirements

### Maintaining requirements

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
