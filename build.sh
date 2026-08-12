#!/bin/bash
pip install -r requirements-deploy.txt
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py shell -c "exec(open('seed_curso_adulto_mayor.py', encoding='utf-8').read())"
python manage.py shell -c "exec(open('seed_eval_final.py', encoding='utf-8').read())"
