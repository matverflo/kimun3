from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Max
from django.utils import timezone
from .models import Curso, Material, InscripcionCurso, Categoria, Clase, ClaseCompletado
from .forms import CursoForm, MaterialForm, CategoriaForm, ClaseForm
from usuarios.decorators import admin_required, docente_or_admin_required, course_owner_or_admin


@login_required
def curso_list(request):
    if request.user.rol == 'colaborador':
        return redirect('usuarios:mis_cursos')
    query = request.GET.get('q', '')
    estado_filter = request.GET.get('estado', '')
    categoria_filter = request.GET.get('categoria', '')
    
    if request.user.rol in ['admin', 'docente']:
        cursos = Curso.objects.select_related('docente_creador', 'categoria')
    else:
        cursos = Curso.objects.filter(estado='publicado').select_related('categoria')
    
    if query:
        cursos = cursos.filter(titulo__icontains=query)
    
    if estado_filter:
        cursos = cursos.filter(estado=estado_filter)
    
    if categoria_filter:
        cursos = cursos.filter(categoria_id=categoria_filter)
    
    cursos = cursos.order_by('-fecha_creacion')
    
    paginator = Paginator(cursos, 15)
    page_number = request.GET.get('page', 1)
    cursos_page = paginator.get_page(page_number)
    
    return render(request, 'cursos/curso_list.html', {
        'cursos': cursos_page,
        'page_obj': cursos_page,
        'is_docente': request.user.rol in ['admin', 'docente'],
        'query': query,
        'estado_filter': estado_filter,
        'categoria_filter': categoria_filter,
        'categorias': Categoria.objects.all(),
        'now': timezone.now()
    })


@login_required
@docente_or_admin_required
def curso_create(request):
    if request.method == 'POST':
        form = CursoForm(request.POST, user=request.user)
        if form.is_valid():
            curso = form.save(commit=False)
            if request.user.rol == 'docente':
                curso.docente_creador = request.user
            else:
                curso.docente_creador = form.cleaned_data['docente_creador']
            curso.save()
            messages.success(request, f'Curso "{curso.titulo}" creado exitosamente.')
            return redirect('cursos:curso_detail', pk=curso.id)
    else:
        form = CursoForm(initial={'estado': 'borrador'}, user=request.user)

    return render(request, 'cursos/curso_form.html', {
        'accion': 'crear',
        'curso': None,
        'form': form,
        'categorias': Categoria.objects.all()
    })


@login_required
@course_owner_or_admin
def curso_edit(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    
    if request.method == 'POST':
        form = CursoForm(request.POST, instance=curso)
        if form.is_valid():
            curso = form.save()
            messages.success(request, f'Curso "{curso.titulo}" actualizado.')
            return redirect('cursos:curso_detail', pk=curso.id)
    else:
        form = CursoForm(instance=curso)
    
    return render(request, 'cursos/curso_form.html', {
        'accion': 'editar',
        'curso': curso,
        'form': form,
        'categorias': Categoria.objects.all()
    })


@login_required
def curso_detail(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    
    session_key = f'modo_estudiante_curso_{curso.id}'
    if 'vista' in request.GET and request.user.rol in ['admin', 'docente']:
        request.session[session_key] = (request.GET.get('vista') == 'estudiante')
        if request.session[session_key]:
            InscripcionCurso.objects.get_or_create(usuario=request.user, curso=curso, defaults={'estado': 'asignado'})
        return redirect('cursos:curso_detail', pk=curso.id)
    
    # Si es borrador, solo lo ve el creador, admin, o usuarios inscritos
    if curso.estado == 'borrador':
        is_enrolled = InscripcionCurso.objects.filter(usuario=request.user, curso=curso).exists()
        if not is_enrolled:
            if request.user.rol not in ['admin', 'docente']:
                return HttpResponseForbidden('Este curso no está disponible.')
            if request.user.rol == 'docente' and curso.docente_creador != request.user:
                return HttpResponseForbidden('Este curso no está disponible.')
    
    materiales = curso.materiales.all()
    clases = curso.clases.all()
    evaluaciones = curso.evaluaciones.all()
    tareas = curso.tareas.all().order_by('fecha_limite')
    
    if request.user.rol == 'colaborador':
        from tareas.models import EntregaTarea
        entregas = EntregaTarea.objects.filter(tarea__curso=curso, estudiante=request.user)
        entregas_dict = {e.tarea_id: e for e in entregas}
        for tarea in tareas:
            tarea.user_entrega = entregas_dict.get(tarea.id)
            
    simular_estudiante = request.session.get(session_key, False) and request.user.rol in ['admin', 'docente']
    es_colaborador = request.user.rol == 'colaborador' or simular_estudiante
    
    contenido_unificado = list(clases) + list(evaluaciones)
    contenido_unificado.sort(key=lambda x: getattr(x, 'orden', 0))

    from cursos.utils import can_access_item, get_next_uncompleted_item
    
    contenido_con_estado = []
    clases_completadas_count = 0
    
    next_uncompleted = get_next_uncompleted_item(request.user, curso, simular_estudiante)
    
    for obj in contenido_unificado:
        completado = False
        bloqueado = False
        is_clase = hasattr(obj, 'contenido')
        
        if es_colaborador:
            if is_clase:
                if not simular_estudiante:
                    completado = ClaseCompletado.objects.filter(usuario=request.user, clase=obj).exists()
                if completado:
                    clases_completadas_count += 1
            else:
                from evaluaciones.models import IntentoEvaluacion
                if not simular_estudiante:
                    ultimo_intento = IntentoEvaluacion.objects.filter(
                        usuario=request.user, evaluacion=obj
                    ).order_by('-fecha_intento').first()
                    if ultimo_intento and ultimo_intento.aprobado:
                        completado = True
                    
            bloqueado = not can_access_item(request.user, curso, obj.orden, simular_estudiante)
                    
        contenido_con_estado.append({
            'item': obj,
            'is_clase': is_clase,
            'completado': completado,
            'bloqueado': bloqueado,
            'orden': obj.orden
        })
    
    clases_progress = 0
    progreso_general = 0
    total_items = clases.count() + curso.evaluaciones.count()
    items_completados = clases_completadas_count
    
    inscripcion = None
    evaluaciones_pendientes = 0
    evaluaciones_aprobadas = 0
    total_evals = curso.evaluaciones.count()
    tiempo_invertido_minutos = 0
    tiempo_progress = 0
    
    if es_colaborador:
        inscripcion = InscripcionCurso.objects.filter(usuario=request.user, curso=curso).first()
        
        if total_evals > 0 and not simular_estudiante:
            from evaluaciones.models import IntentoEvaluacion
            evaluaciones_aprobadas = IntentoEvaluacion.objects.filter(
                evaluacion__curso=curso,
                usuario=request.user,
                aprobado=True
            ).values('evaluacion').distinct().count()
            evaluaciones_pendientes = total_evals - evaluaciones_aprobadas
            
        items_completados += evaluaciones_aprobadas
        if total_items > 0:
            progreso_general = int((items_completados / total_items) * 100)
            
            if progreso_general == 100 and inscripcion and inscripcion.estado != 'completado' and not simular_estudiante:
                from cursos.utils import check_curso_completed
                check_curso_completed(request.user, curso)
                inscripcion.refresh_from_db()
            
        from reportes.models import RegistroSesionArt33
        if not simular_estudiante:
            sesiones = RegistroSesionArt33.objects.filter(
                usuario=request.user,
                modulo_visitado=curso.titulo
            )
            for sesion in sesiones:
                if sesion.fecha_salida and sesion.fecha_entrada:
                    tiempo_invertido_minutos += int((sesion.fecha_salida - sesion.fecha_entrada).total_seconds() / 60)
            
        if curso.duracion_minutos:
            tiempo_progress = int((tiempo_invertido_minutos / curso.duracion_minutos) * 100)
            if tiempo_progress > 100:
                tiempo_progress = 100
    
    puede_editar = False
    if not simular_estudiante:
        puede_editar = request.user.rol == 'admin' or (
            request.user.rol == 'docente' and curso.docente_creador == request.user
        )
    
    from django.utils import timezone
    
    from certificados.models import Certificado
    certificado = Certificado.objects.filter(usuario=request.user, curso=curso).first()

    return render(request, 'cursos/curso_detail.html', {
        'curso': curso,
        'materiales': materiales,
        'clases': clases,
        'tareas': tareas,
        'contenido_con_estado': contenido_con_estado,
        'progreso_general': progreso_general,
        'inscripcion': inscripcion,
        'puede_editar': puede_editar,
        'evaluaciones_aprobadas': evaluaciones_aprobadas,
        'total_evals': total_evals,
        'tiempo_invertido_minutos': tiempo_invertido_minutos,
        'tiempo_progress': tiempo_progress,
        'next_uncompleted': next_uncompleted,
        'simular_estudiante': simular_estudiante,
        'es_colaborador': es_colaborador,
        'certificado': certificado,
        'now': timezone.now()
    })


@login_required
@course_owner_or_admin
def curso_gestion(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    
    # Filtro base
    inscripciones = InscripcionCurso.objects.filter(curso=curso, usuario__rol='colaborador').select_related('usuario')
    
    # Buscador
    from django.db.models import Q
    q = request.GET.get('q', '')
    if q:
        inscripciones = inscripciones.filter(
            Q(usuario__first_name__icontains=q) | 
            Q(usuario__last_name__icontains=q) | 
            Q(usuario__rut__icontains=q) |
            Q(usuario__username__icontains=q)
        )
    
    from certificados.models import Certificado
    from cursos.utils import is_item_completado
    
    completados = []
    pendientes = []
    en_progreso = []
    
    for inscripcion in inscripciones:
        usuario = inscripcion.usuario
        cert = Certificado.objects.filter(usuario=usuario, curso=curso).first()
        
        total_items = curso.clases.count() + curso.evaluaciones.count()
        items_completados = 0
        if total_items > 0:
            for clase in curso.clases.all():
                if is_item_completado(usuario, clase):
                    items_completados += 1
            for eval in curso.evaluaciones.all():
                if is_item_completado(usuario, eval):
                    items_completados += 1
            progreso = int((items_completados / total_items) * 100)
        else:
            progreso = 0
            
        inscripcion.progreso = progreso
        
        if progreso == 100 and inscripcion.estado != 'completado':
            from cursos.utils import check_curso_completed
            check_curso_completed(usuario, curso)
            inscripcion.refresh_from_db()
            cert = Certificado.objects.filter(usuario=usuario, curso=curso).first()
        
        if cert:
            if cert.estado == 'aprobado':
                completados.append(inscripcion)
            else:
                pendientes.append(inscripcion)
        else:
            if inscripcion.estado == 'completado':
                pendientes.append(inscripcion)
            else:
                en_progreso.append(inscripcion)
                
    context = {
        'curso': curso,
        'completados': completados,
        'pendientes': pendientes,
        'en_progreso': en_progreso,
        'q': q,
    }
    return render(request, 'cursos/curso_gestion.html', context)


@login_required
@course_owner_or_admin
def curso_alumno_detail(request, curso_pk, usuario_pk):
    curso = get_object_or_404(Curso, pk=curso_pk)
    
    from usuarios.models import Usuario
    alumno = get_object_or_404(Usuario, pk=usuario_pk)
    
    inscripcion = get_object_or_404(InscripcionCurso, curso=curso, usuario=alumno)
    
    from certificados.models import Certificado
    from cursos.utils import is_item_completado, get_tiempo_invertido_minutos
    
    # Progreso y Tiempo
    total_items = curso.clases.count() + curso.evaluaciones.count()
    items_completados = 0
    if total_items > 0:
        for clase in curso.clases.all():
            if is_item_completado(alumno, clase):
                items_completados += 1
        for eval in curso.evaluaciones.all():
            if is_item_completado(alumno, eval):
                items_completados += 1
        progreso = int((items_completados / total_items) * 100)
    else:
        progreso = 0
        
    tiempo_invertido_minutos = get_tiempo_invertido_minutos(alumno, curso)
    tiempo_invertido = None
    if tiempo_invertido_minutos > 0:
        horas = tiempo_invertido_minutos // 60
        minutos = tiempo_invertido_minutos % 60
        tiempo_invertido = f"{horas}h {minutos}m"
        
    # Evaluaciones
    from evaluaciones.models import IntentoEvaluacion
    evaluaciones = curso.evaluaciones.all()
    eval_datos = []
    for eva in evaluaciones:
        intentos = IntentoEvaluacion.objects.filter(usuario=alumno, evaluacion=eva)
        mejor_intento = intentos.order_by('-puntaje_obtenido').first()
        eval_datos.append({
            'evaluacion': eva,
            'intentos': intentos.count(),
            'mejor_intento': mejor_intento
        })
        
    # Tareas
    from tareas.models import EntregaTarea
    tareas = curso.tareas.all()
    tareas_datos = []
    for tarea in tareas:
        entrega = EntregaTarea.objects.filter(tarea=tarea, estudiante=alumno).first()
        tareas_datos.append({
            'tarea': tarea,
            'entrega': entrega
        })
        
    # Certificado
    certificado = Certificado.objects.filter(usuario=alumno, curso=curso).first()
    
    context = {
        'curso': curso,
        'alumno': alumno,
        'inscripcion': inscripcion,
        'progreso': progreso,
        'tiempo_invertido': tiempo_invertido,
        'eval_datos': eval_datos,
        'tareas_datos': tareas_datos,
        'certificado': certificado,
    }
    return render(request, 'cursos/curso_alumno_detail.html', context)


@login_required
@course_owner_or_admin
def curso_delete(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    
    if request.method == 'POST':
        curso.delete()
        messages.success(request, 'Curso eliminado exitosamente.')
        return redirect('cursos:curso_list')
    
    messages.error(request, 'Método no permitido.')
    return redirect('cursos:curso_detail', pk=pk)


@login_required
@course_owner_or_admin
def material_create(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    
    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.curso = curso
            material.save()
            messages.success(request, f'Material "{material.titulo}" agregado.')
            return redirect('cursos:curso_detail', pk=curso.id)
    else:
        form = MaterialForm(initial={'tipo': 'pdf'})
    
    return render(request, 'cursos/material_form.html', {
        'curso': curso,
        'form': form,
        'accion': 'crear'
    })


@login_required
@docente_or_admin_required
def material_delete(request, pk):
    material = get_object_or_404(Material, pk=pk)
    curso = material.curso
    
    if request.user.rol == 'docente' and curso.docente_creador != request.user:
        return HttpResponseForbidden('No puedes eliminar este material.')
    
    if request.method == 'POST':
        material.delete()
        messages.success(request, 'Material eliminado.')
        return redirect('cursos:curso_detail', pk=curso.id)
    
    messages.error(request, 'Método no permitido.')
    return redirect('cursos:curso_detail', pk=curso.id)


@login_required
@admin_required
def categoria_list(request):
    categorias = Categoria.objects.all()
    return render(request, 'cursos/categoria_list.html', {'categorias': categorias})


@login_required
@admin_required
def categoria_create(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            categoria = form.save()
            messages.success(request, f'Categoría "{categoria.nombre}" creada.')
            return redirect('cursos:categoria_list')
    else:
        form = CategoriaForm(initial={'color': '#6366f1'})
    
    return render(request, 'cursos/categoria_form.html', {'accion': 'crear', 'form': form})


@login_required
@admin_required
def categoria_edit(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            categoria = form.save()
            messages.success(request, f'Categoría "{categoria.nombre}" actualizada.')
            return redirect('cursos:categoria_list')
    else:
        form = CategoriaForm(instance=categoria)
    
    return render(request, 'cursos/categoria_form.html', {
        'accion': 'editar',
        'categoria': categoria,
        'form': form
    })


@login_required
@admin_required
def categoria_delete(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    
    if request.method == 'POST':
        nombre = categoria.nombre
        categoria.delete()
        messages.success(request, f'Categoría "{nombre}" eliminada.')
        return redirect('cursos:categoria_list')
    
    return render(request, 'cursos/categoria_confirm_delete.html', {'categoria': categoria})


# Clase (Lección) Views

@login_required
def clase_list(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    
    session_key = f'modo_estudiante_curso_{curso.id}'
    if 'vista' in request.GET and request.user.rol in ['admin', 'docente']:
        request.session[session_key] = (request.GET.get('vista') == 'estudiante')
        if request.session[session_key]:
            InscripcionCurso.objects.get_or_create(usuario=request.user, curso=curso, defaults={'estado': 'asignado'})
        return redirect('cursos:clase_list', pk=curso.id)
    
    simular_estudiante = request.session.get(session_key, False) and request.user.rol in ['admin', 'docente']
    es_colaborador = request.user.rol == 'colaborador' or simular_estudiante
    
    if curso.estado == 'borrador':
        is_enrolled = InscripcionCurso.objects.filter(usuario=request.user, curso=curso).exists()
        if not is_enrolled:
            if request.user.rol not in ['admin', 'docente']:
                return HttpResponseForbidden('Este curso no está disponible.')
            if request.user.rol == 'docente' and curso.docente_creador != request.user:
                return HttpResponseForbidden('Este curso no está disponible.')
    
    if request.user.rol == 'colaborador':
        if not InscripcionCurso.objects.filter(usuario=request.user, curso=curso).exists():
            return HttpResponseForbidden('Debes estar inscrito en este curso para ver las clases.')
    
    clases = curso.clases.all()
    evaluaciones = curso.evaluaciones.all()
    
    contenido_unificado = list(clases) + list(evaluaciones)
    contenido_unificado.sort(key=lambda x: getattr(x, 'orden', 0))
    
    puede_editar = False
    if not simular_estudiante:
        puede_editar = request.user.rol == 'admin' or (
            request.user.rol == 'docente' and curso.docente_creador == request.user
        )
    
    from cursos.utils import can_access_item
    
    contenido_con_estado = []
    for obj in contenido_unificado:
        completado = False
        bloqueado = False
        is_clase = hasattr(obj, 'contenido')
        
        if es_colaborador:
            if is_clase:
                if not simular_estudiante:
                    completado = ClaseCompletado.objects.filter(usuario=request.user, clase=obj).exists()
            else:
                from evaluaciones.models import IntentoEvaluacion
                if not simular_estudiante:
                    ultimo_intento = IntentoEvaluacion.objects.filter(
                        usuario=request.user, evaluacion=obj
                    ).order_by('-fecha_intento').first()
                    if ultimo_intento and ultimo_intento.aprobado:
                        completado = True
            
            bloqueado = not can_access_item(request.user, curso, obj.orden, simular_estudiante)
                    
        contenido_con_estado.append({
            'item': obj,
            'is_clase': is_clase,
            'completado': completado,
            'bloqueado': bloqueado,
            'orden': obj.orden
        })
    
    return render(request, 'cursos/clase_list.html', {
        'curso': curso,
        'contenido_con_estado': contenido_con_estado,
        'puede_editar': puede_editar,
        'simular_estudiante': simular_estudiante,
        'es_colaborador': es_colaborador
    })


@login_required
@course_owner_or_admin
def clase_create(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    
    if request.method == 'POST':
        form = ClaseForm(request.POST, instance=Clase(curso=curso))
        if form.is_valid():
            try:
                clase = form.save(commit=False)
                clase.curso = curso
                clase.save()
                messages.success(request, f'Clase "{clase.titulo}" creada.')
                return redirect('cursos:clase_list', pk=curso.id)
            except IntegrityError:
                form.add_error('orden', 'Ya existe una clase con ese orden en el curso.')
    else:
        max_orden = curso.clases.aggregate(max_orden=Max('orden'))['max_orden'] or 0
        initial_orden = max_orden + 1
        form = ClaseForm(initial={'orden': initial_orden})
    
    return render(request, 'cursos/clase_form.html', {
        'curso': curso,
        'form': form,
        'accion': 'crear',
        'proximo_orden': curso.clases.count() + 1
    })


@login_required
def clase_detail(request, pk):
    clase = get_object_or_404(Clase, pk=pk)
    curso = clase.curso
    
    if curso.estado == 'borrador':
        is_enrolled = InscripcionCurso.objects.filter(usuario=request.user, curso=curso).exists()
        if not is_enrolled:
            if request.user.rol not in ['admin', 'docente']:
                return HttpResponseForbidden('Este curso no está disponible.')
            if request.user.rol == 'docente' and curso.docente_creador != request.user:
                return HttpResponseForbidden('Este curso no está disponible.')
                
    session_key = f'modo_estudiante_curso_{curso.id}'
    simular_estudiante = request.session.get(session_key, False) and request.user.rol in ['admin', 'docente']
    es_colaborador = request.user.rol == 'colaborador' or simular_estudiante
    
    if es_colaborador:
        inscripcion = InscripcionCurso.objects.filter(usuario=request.user, curso=curso).first()
        if not inscripcion:
            return HttpResponseForbidden('Debes estar inscrito en este curso para ver las clases.')
        elif not simular_estudiante and inscripcion.estado == 'asignado':
            inscripcion.estado = 'en_progreso'
            inscripcion.save()
    
    puede_editar = False
    if not simular_estudiante:
        puede_editar = request.user.rol == 'admin' or (
            request.user.rol == 'docente' and curso.docente_creador == request.user
        )
    
    from cursos.utils import can_access_item, get_adjacent_items
    
    completado = None
    tiene_acceso = True
    
    item_anterior, item_siguiente = get_adjacent_items(curso, clase.orden)
    
    if es_colaborador:
        completado = ClaseCompletado.objects.filter(usuario=request.user, clase=clase).exists()
        
        if not can_access_item(request.user, curso, clase.orden, simular_estudiante):
            tiene_acceso = False
    
    return render(request, 'cursos/clase_detail.html', {
        'clase': clase,
        'curso': curso,
        'completado': completado,
        'tiene_acceso': tiene_acceso,
        'puede_editar': puede_editar,
        'item_anterior': item_anterior,
        'item_siguiente': item_siguiente,
        'es_colaborador': es_colaborador,
        'simular_estudiante': simular_estudiante
    })


@login_required
@docente_or_admin_required
def clase_edit(request, pk):
    clase = get_object_or_404(Clase, pk=pk)
    curso = clase.curso
    
    if request.user.rol == 'docente' and curso.docente_creador != request.user:
        return HttpResponseForbidden('No puedes editar esta clase.')
    
    if request.method == 'POST':
        form = ClaseForm(request.POST, instance=clase)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'Clase "{clase.titulo}" actualizada.')
                return redirect('cursos:clase_detail', pk=clase.id)
            except IntegrityError:
                form.add_error('orden', 'Ya existe una clase con ese orden en el curso.')
    else:
        form = ClaseForm(instance=clase)
    
    return render(request, 'cursos/clase_form.html', {
        'curso': curso,
        'clase': clase,
        'form': form,
        'accion': 'editar'
    })


@login_required
@docente_or_admin_required
def clase_delete(request, pk):
    clase = get_object_or_404(Clase, pk=pk)
    curso = clase.curso
    
    if request.user.rol == 'docente' and curso.docente_creador != request.user:
        return HttpResponseForbidden('No puedes eliminar esta clase.')
    
    if request.method == 'POST':
        titulo = clase.titulo
        clase.delete()
        messages.success(request, f'Clase "{titulo}" eliminada.')
        return redirect('cursos:clase_list', pk=curso.id)
    
    return render(request, 'cursos/clase_confirm_delete.html', {
        'clase': clase,
        'curso': curso
    })

@login_required
def clase_completar(request, pk):
    clase = get_object_or_404(Clase, pk=pk)
    curso = clase.curso
    
    if request.method != 'POST':
        return redirect('cursos:clase_detail', pk=clase.id)
        
    session_key = f'modo_estudiante_curso_{curso.id}'
    simular_estudiante = request.session.get(session_key, False) and request.user.rol in ['admin', 'docente']
    es_colaborador = request.user.rol == 'colaborador' or simular_estudiante
    
    if not es_colaborador:
        messages.error(request, 'Solo los alumnos pueden completar clases.')
        return redirect('cursos:clase_detail', pk=clase.id)
    
    esta_inscrito = InscripcionCurso.objects.filter(
        usuario=request.user, curso=curso
    ).exists()
    if not esta_inscrito:
        messages.error(request, 'Debes estar inscrito en el curso para completar clases.')
        return redirect('cursos:clase_detail', pk=clase.id)
    
    ya_existente = ClaseCompletado.objects.filter(
        usuario=request.user, clase=clase
    ).exists()
    if ya_existente:
        messages.info(request, 'Ya completaste esta clase.')
        return redirect('cursos:clase_detail', pk=clase.id)
    
    from cursos.utils import can_access_item
    
    if not can_access_item(request.user, curso, clase.orden, simular_estudiante):
        messages.error(request, 'Debes completar los módulos anteriores primero.')
        return redirect('cursos:clase_detail', pk=clase.id)
    
    ClaseCompletado.objects.get_or_create(
        usuario=request.user,
        clase=clase
    )
    
    # Verificar completación del curso completo
    from cursos.utils import check_curso_completed
    check_curso_completed(request.user, curso)
    
    messages.success(request, 'Clase marcada como completada.')
    return redirect('cursos:clase_detail', pk=clase.id)

from django.views.decorators.http import require_POST
import json
from django.http import JsonResponse
from django.db import transaction

@login_required
@course_owner_or_admin
@require_POST
def curso_reordenar(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    try:
        data = json.loads(request.body)
        with transaction.atomic():
            for item in data:
                item_id = int(item.get('id'))
                item_tipo = item.get('tipo')
                nuevo_orden = int(item.get('orden'))
                
                if item_tipo == 'clase':
                    obj = get_object_or_404(Clase, pk=item_id, curso=curso)
                elif item_tipo == 'evaluacion':
                    from evaluaciones.models import Evaluacion
                    obj = get_object_or_404(Evaluacion, pk=item_id, curso=curso)
                else:
                    continue
                
                obj.orden = nuevo_orden
                obj.save(update_fields=['orden'])
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
