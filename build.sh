#!/bin/bash
pip install -r requirements-deploy.txt
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py seed_demo_profesor
