from django.utils import timezone
from reportes.models import RegistroSesionArt33
from cursos.models import InscripcionCurso, ClaseCompletado
from evaluaciones.models import IntentoEvaluacion

def check_curso_completed(usuario, curso):
    from certificados.models import Certificado
    # 1. Verificar si todas las clases están completadas
    total_clases = curso.clases.count()
    clases_completadas = ClaseCompletado.objects.filter(usuario=usuario, clase__curso=curso).count()
    if total_clases > 0 and clases_completadas < total_clases:
        return False, "Faltan clases por completar"

    # 2. Verificar si todas las evaluaciones están aprobadas
    total_evals = curso.evaluaciones.count()
    if total_evals > 0:
        aprobadas = IntentoEvaluacion.objects.filter(
            evaluacion__curso=curso,
            usuario=usuario,
            aprobado=True
        ).values('evaluacion').distinct().count()
        if aprobadas < total_evals:
            return False, "Faltan evaluaciones por aprobar"

    # 3. Verificar tiempo invertido
    tiempo_invertido_minutos = get_tiempo_invertido_minutos(usuario, curso)
            
    if curso.duracion_minutos and tiempo_invertido_minutos < curso.duracion_minutos:
        minutos_faltantes = curso.duracion_minutos - tiempo_invertido_minutos
        return False, f"Has completado el material, pero te faltan {minutos_faltantes} minutos de estudio exigidos por el curso. ¡Repasa un poco más el contenido!"

    # Si pasa todo, marcamos como completado y generamos certificado
    inscripcion = InscripcionCurso.objects.filter(usuario=usuario, curso=curso).first()
    if inscripcion and inscripcion.estado != 'completado':
        inscripcion.estado = 'completado'
        inscripcion.save()
        
    Certificado.objects.get_or_create(
        usuario=usuario,
        curso=curso,
        defaults={'estado': 'pendiente'}
    )
    
    return True, "Curso completado exitosamente"

def get_contenido_unificado(curso):
    clases = list(curso.clases.all())
    evaluaciones = list(curso.evaluaciones.all())
    contenido = clases + evaluaciones
    contenido.sort(key=lambda x: getattr(x, 'orden', 0))
    return contenido

def get_tiempo_invertido_minutos(usuario, curso):
    tiempo_invertido = 0
    sesiones = RegistroSesionArt33.objects.filter(
        usuario=usuario,
        modulo_visitado=curso.titulo
    )
    for sesion in sesiones:
        if sesion.fecha_salida and sesion.fecha_entrada:
            tiempo_invertido += int((sesion.fecha_salida - sesion.fecha_entrada).total_seconds() / 60)
    return tiempo_invertido

def is_item_completado(usuario, item):
    is_clase = hasattr(item, 'contenido')
    if is_clase:
        from cursos.models import ClaseCompletado
        return ClaseCompletado.objects.filter(usuario=usuario, clase=item).exists()
    else:
        from evaluaciones.models import IntentoEvaluacion
        ultimo_intento = IntentoEvaluacion.objects.filter(
            usuario=usuario, evaluacion=item
        ).order_by('-fecha_intento').first()
        return bool(ultimo_intento and ultimo_intento.aprobado)

def can_access_item(usuario, curso, orden, simular_estudiante=False):
    if usuario.rol != 'colaborador' and not simular_estudiante:
        return True # Admin y Docentes pueden ver todo
        
    contenido = get_contenido_unificado(curso)
    for obj in contenido:
        obj_orden = getattr(obj, 'orden', 0)
        if obj_orden < orden:
            if not is_item_completado(usuario, obj):
                return False
    return True

def get_next_uncompleted_item(usuario, curso, simular_estudiante=False):
    if usuario.rol != 'colaborador' and not simular_estudiante:
        return None
        
    contenido = get_contenido_unificado(curso)
    for obj in contenido:
        if not is_item_completado(usuario, obj):
            return obj
    return None

def get_adjacent_items(curso, orden):
    contenido = get_contenido_unificado(curso)
    item_anterior = None
    item_siguiente = None
    
    anteriores = [x for x in contenido if getattr(x, 'orden', 0) < orden]
    if anteriores:
        item_anterior = anteriores[-1]
        
    siguientes = [x for x in contenido if getattr(x, 'orden', 0) > orden]
    if siguientes:
        item_siguiente = siguientes[0]
        
    return item_anterior, item_siguiente
