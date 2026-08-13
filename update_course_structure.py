from cursos.models import Curso, Modulo, Clase
from evaluaciones.models import Evaluacion

curso = Curso.objects.filter(titulo__icontains="Cuidado Integral del Adulto Mayor").first()
if curso:
    # 1. Crear módulos
    m1, _ = Modulo.objects.get_or_create(curso=curso, titulo="Fundamentos del Cuidado y Buen Trato", defaults={'orden': 1})
    m2, _ = Modulo.objects.get_or_create(curso=curso, titulo="Cuidados Físicos y Vida Diaria", defaults={'orden': 2})
    m3, _ = Modulo.objects.get_or_create(curso=curso, titulo="Salud Mental y Cuidado Especializado", defaults={'orden': 3})

    # 2. Asignar clases y limpiar títulos
    c1 = Clase.objects.filter(curso=curso, titulo__icontains="Psicología del Envejecimiento").first()
    if c1:
        c1.modulo = m1
        c1.titulo = "Clase 1: Psicología del Envejecimiento y Trato Digno"
        c1.orden = 1
        c1.save()

    c2 = Clase.objects.filter(curso=curso, titulo__icontains="Fomento de la Autonomía").first()
    if c2:
        c2.modulo = m1
        c2.titulo = "Clase 2: Fomento de la Autonomía vs Asistencialismo"
        c2.orden = 2
        c2.save()

    e1 = Evaluacion.objects.filter(curso=curso, titulo__icontains="Conocimientos Básicos").first()
    if e1:
        e1.modulo = m1
        e1.titulo = "Evaluación Intermedia: Conocimientos Básicos de Cuidado"
        e1.orden = 3
        e1.save()

    c3 = Clase.objects.filter(curso=curso, titulo__icontains="Movilidad y Prevención").first()
    if c3:
        c3.modulo = m2
        c3.titulo = "Clase 3: Movilidad y Prevención de Caídas"
        c3.orden = 1
        c3.save()

    c4 = Clase.objects.filter(curso=curso, titulo__icontains="Alimentación e Higiene").first()
    if c4:
        c4.modulo = m2
        c4.titulo = "Clase 4: Alimentación e Higiene Personal"
        c4.orden = 2
        c4.save()

    c5 = Clase.objects.filter(curso=curso, titulo__icontains="Salud Mental, Alzheimer").first()
    if c5:
        c5.modulo = m3
        c5.titulo = "Clase 5: Salud Mental, Alzheimer y Demencia"
        c5.orden = 1
        c5.save()

    e2 = Evaluacion.objects.filter(curso=curso, titulo__icontains="Certificación de Cuidados").first()
    if e2:
        e2.modulo = m3
        e2.titulo = "Evaluación Final: Certificación de Cuidados"
        e2.orden = 2
        e2.save()

    print("Estructura de módulos actualizada con éxito.")
else:
    print("No se encontró el curso.")
