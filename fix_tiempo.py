import os
import django
import random
import datetime
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kimun.settings')
django.setup()

from cursos.models import InscripcionCurso
from reportes.models import RegistroSesionArt33

def run():
    inscripciones = InscripcionCurso.objects.filter(estado__in=['en_progreso', 'completado'])
    creados = 0

    for insc in inscripciones:
        # Check if they already have time logged
        tiene_tiempo = RegistroSesionArt33.objects.filter(
            usuario=insc.usuario,
            modulo_visitado=insc.curso.titulo
        ).exists()

        if not tiene_tiempo:
            fecha_inicio = insc.fecha_inicio_real or (timezone.now() - datetime.timedelta(days=random.randint(1, 10)))
            minutos_a_simular = random.randint(120, 600) if insc.estado == 'completado' else random.randint(10, 100)
            fecha_salida = fecha_inicio + datetime.timedelta(minutes=minutos_a_simular)
            
            RegistroSesionArt33.objects.create(
                usuario=insc.usuario,
                fecha_entrada=fecha_inicio,
                fecha_salida=fecha_salida,
                modulo_visitado=insc.curso.titulo,
                direccion_ip="127.0.0.1"
            )
            creados += 1

    print(f"Se crearon {creados} registros de tiempo (Art 33) para inscripciones existentes.")

if __name__ == '__main__':
    run()
