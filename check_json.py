import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kimun.settings')
django.setup()

from pacientes.models import ReporteAsignacionIA
import json

r = ReporteAsignacionIA.objects.last()
if r:
    print(json.dumps(r.datos_json, indent=2))
else:
    print("No records")
