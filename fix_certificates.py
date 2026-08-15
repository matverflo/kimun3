import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kimun.settings')
django.setup()

from cursos.models import InscripcionCurso
from certificados.models import Certificado

def run():
    inscripciones_completadas = InscripcionCurso.objects.filter(estado='completado')
    creados = 0

    for insc in inscripciones_completadas:
        cert, created = Certificado.objects.get_or_create(
            usuario=insc.usuario,
            curso=insc.curso,
            defaults={'estado': 'aprobado'}
        )
        if created:
            creados += 1

    print(f"Se crearon {creados} certificados para inscripciones completadas.")

if __name__ == '__main__':
    run()
