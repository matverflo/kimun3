#!/bin/bash
pip install -r requirements-deploy.txt
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py seed_empleados
python manage.py seed_pacientes
python manage.py seed_cursos
python manage.py seed_inscripciones
