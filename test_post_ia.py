import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kimun.settings')
django.setup()

from django.test import Client
from pacientes.models import Paciente
from usuarios.models import Usuario

client = Client()

admin = Usuario.objects.filter(is_superuser=True).first()
client.force_login(admin)

paciente = Paciente.objects.first()
colaborador = Usuario.objects.filter(rol='colaborador').first()

print(f"Paciente: {paciente.id}")
print(f"Colaborador a asignar: {colaborador.id}")

response = client.post(f'/pacientes/expediente/paciente/{paciente.id}/sugerencia-ia/', {'colaborador_id': colaborador.id})
print(f"Response status: {response.status_code}")

if colaborador in paciente.colaboradores.all():
    print("Success: Colaborador was added!")
else:
    print("Failure: Colaborador was NOT added.")
