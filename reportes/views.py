# pyright: reportAttributeAccessIssue=false

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q, F, Sum, ExpressionWrapper, fields
from django.utils import timezone
from datetime import timedelta
from cursos.models import Curso, InscripcionCurso
from evaluaciones.models import Evaluacion, IntentoEvaluacion
from certificados.models import Certificado
from usuarios.models import Usuario
from usuarios.decorators import admin_required
from django.http import HttpResponse
import zipfile
import io
from reportes.models import RegistroSesionArt33
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
except ImportError:
    pass

def get_at_risk_students():
    """Returns list of dicts with user and risk reason."""
    from cursos.models import ClaseCompletado

    at_risk = []
    seven_days_ago = timezone.now() - timedelta(days=7)

    enrollments = InscripcionCurso.objects.filter(
        estado__in=['asignado', 'en_progreso']
    ).select_related('usuario', 'curso')

    for enrollment in enrollments:
        risk_reason = None

        if enrollment.fecha_asignacion < seven_days_ago:
            if not hasattr(enrollment, 'completado') or not enrollment.completado:
                has_progress = ClaseCompletado.objects.filter(
                    usuario=enrollment.usuario,
                    clase__curso=enrollment.curso
                ).exists()
                if not has_progress:
                    risk_reason = "Sin actividad en 7+ días"

        if enrollment.fecha_limite:
            days_to_deadline = (enrollment.fecha_limite - timezone.now()).days
            if days_to_deadline <= 7 and days_to_deadline > 0:
                has_passed = IntentoEvaluacion.objects.filter(
                    usuario=enrollment.usuario,
                    evaluacion__curso=enrollment.curso,
                    aprobado=True
                ).exists()
                if not has_passed:
                    risk_reason = f"Deadline en {days_to_deadline} días sin aprobar evaluaciones"

        failed_all = False
        if IntentoEvaluacion.objects.filter(
            usuario=enrollment.usuario,
            evaluacion__curso=enrollment.curso
        ).exists():
            all_attempts = IntentoEvaluacion.objects.filter(
                usuario=enrollment.usuario,
                evaluacion__curso=enrollment.curso
            )
            if all(attempt.aprobado == False for attempt in all_attempts):
                failed_all = True
                risk_reason = "Ha reprobado todas las evaluaciones"

        if risk_reason:
            ultima_actividad = enrollment.fecha_asignacion
            ultimo_progreso = ClaseCompletado.objects.filter(
                usuario=enrollment.usuario,
                clase__curso=enrollment.curso
            ).order_by('-fecha_completado').first()
            
            if ultimo_progreso and ultimo_progreso.fecha_completado > ultima_actividad:
                ultima_actividad = ultimo_progreso.fecha_completado

            at_risk.append({
                'usuario': enrollment.usuario,
                'estado': enrollment.get_estado_display(),
                'ultima_actividad': ultima_actividad.strftime("%d/%m/%Y %H:%M"),
                'riesgo': risk_reason
            })

    return at_risk


@login_required
@admin_required
def dashboard_reportes(request):
    tipo = request.GET.get('tipo', 'generales')
    context = {'tipo_seleccionado': tipo}
    
    if tipo == 'generales':
        periodo = request.GET.get('periodo', 'historico')
        hace_30_dias = timezone.now() - timedelta(days=30)
        hace_60_dias = timezone.now() - timedelta(days=60)
        
        # Filtros de fecha según el periodo
        if periodo == 'mensual':
            date_filter = {'date_joined__gte': hace_30_dias}
            inscripcion_filter = {'fecha_asignacion__gte': hace_30_dias}
            certificado_filter = {'fecha_emision__gte': hace_30_dias}
            sesion_filter = {'fecha_entrada__gte': hace_30_dias}
        else:
            date_filter = {}
            inscripcion_filter = {}
            certificado_filter = {}
            sesion_filter = {}

        # 4 Métricas Principales
        total_estudiantes = Usuario.objects.filter(rol='colaborador', **date_filter).count()
        total_cursos = Curso.objects.filter(estado='publicado').count() # Los cursos suelen ser históricos, pero los mantendremos
        total_certificados = Certificado.objects.filter(usuario__rol='colaborador', **certificado_filter).count()
        
        sesiones = RegistroSesionArt33.objects.filter(
            usuario__rol='colaborador',
            fecha_salida__isnull=False,
            fecha_entrada__isnull=False,
            **sesion_filter
        ).annotate(
            duracion=ExpressionWrapper(F('fecha_salida') - F('fecha_entrada'), output_field=fields.DurationField())
        )
        total_duracion = sesiones.aggregate(total=Sum('duracion'))['total']
        
        promedio_minutos = 0
        if total_duracion:
            usuarios_activos = RegistroSesionArt33.objects.filter(
                usuario__rol='colaborador', **sesion_filter
            ).values('usuario').distinct().count()
            if usuarios_activos > 0:
                promedio_minutos = int(total_duracion.total_seconds() / 60 / usuarios_activos)
                
        # Resto de los datos del dashboard (se mantienen históricos para las tablas de abajo)
        cursos_con_mas_inscritos = Curso.objects.annotate(
            num_inscripciones=Count('inscripciones', filter=Q(inscripciones__usuario__rol='colaborador'))
        ).order_by('-num_inscripciones')[:5]
        
        usuarios_por_rol = Usuario.objects.values('rol').annotate(count=Count('id'))
        
        inscripciones_por_estado = InscripcionCurso.objects.filter(usuario__rol='colaborador').values('estado').annotate(count=Count('id'))
        
        evaluaciones_promedio = IntentoEvaluacion.objects.filter(usuario__rol='colaborador').aggregate(promedio=Avg('puntaje_obtenido'))
        
        ultimas_inscripciones = InscripcionCurso.objects.filter(usuario__rol='colaborador').select_related('usuario', 'curso').order_by('-fecha_asignacion')[:10]
        
        context.update({
            'periodo': periodo,
            'total_usuarios': total_estudiantes,
            'total_cursos': total_cursos,
            'total_certificados': total_certificados,
            'promedio_minutos': promedio_minutos,
            
            'cursos_con_mas_inscritos': cursos_con_mas_inscritos,
            'usuarios_por_rol': usuarios_por_rol,
            'inscripciones_por_estado': inscripciones_por_estado,
            'promedio_evaluaciones': evaluaciones_promedio['promedio'] or 0,
            'ultimas_inscripciones': ultimas_inscripciones,
            'estudiantes_en_riesgo': get_at_risk_students(),
        })
        
    elif tipo == 'normativos':
        from usuarios.models import AreaCargo
        context['cargos'] = AreaCargo.objects.all()

    return render(request, 'reportes/dashboard.html', context)


@login_required
@admin_required
def reporte_curso(request, curso_pk):
    curso = get_object_or_404(Curso, pk=curso_pk)
    inscripciones = InscripcionCurso.objects.filter(curso=curso).select_related('usuario')
    
    evaluaciones = curso.evaluaciones.all()
    
    for inscripcion in inscripciones:
        inscripcion.intentos_count = 0
        inscripcion.aprobado = True
        for evaluacion in evaluaciones:
            ultimo = evaluacion.intentos.filter(usuario=inscripcion.usuario).order_by('-fecha_intento').first()
            if ultimo:
                inscripcion.intentos_count += 1
                if not ultimo.aprobado:
                    inscripcion.aprobado = False
    
    context = {
        'curso': curso,
        'inscripciones': inscripciones,
        'evaluaciones': evaluaciones,
    }
    return render(request, 'reportes/reporte_curso.html', context)


@login_required
@admin_required
def reporte_usuario(request, usuario_pk):
    usuario = get_object_or_404(Usuario, pk=usuario_pk)
    inscripciones = InscripcionCurso.objects.filter(usuario=usuario).select_related('curso')
    intentos = IntentoEvaluacion.objects.filter(usuario=usuario).select_related('evaluacion')
    certificados = Certificado.objects.filter(usuario=usuario).select_related('curso')
    
    context = {
        'usuario': usuario,
        'inscripciones': inscripciones,
        'intentos': intentos,
        'certificados': certificados,
    }
    return render(request, 'reportes/reporte_usuario.html', context)


@login_required
@admin_required
def progreso_heatmap(request):
    from cursos.models import Curso, InscripcionCurso, Clase, ClaseCompletado
    from evaluaciones.models import Evaluacion, IntentoEvaluacion
    
    curso_id = request.GET.get('curso')
    cursos = Curso.objects.all()
    
    heatmap_data = []
    
    if curso_id:
        curso = get_object_or_404(Curso, pk=curso_id)
        enrollments = InscripcionCurso.objects.filter(curso=curso).select_related('usuario')
        
        clases = list(curso.clases.all())
        evaluaciones = list(curso.evaluaciones.all())
        
        for enrollment in enrollments:
            student_data = {
                'usuario': enrollment.usuario,
                'estado': enrollment.estado,
                'items': []
            }
            
            for clase in clases:
                completado = ClaseCompletado.objects.filter(
                    usuario=enrollment.usuario,
                    clase=clase
                ).exists()
                student_data['items'].append({
                    'tipo': 'clase',
                    'titulo': clase.titulo,
                    'completado': completado
                })
            
            for evaluacion in evaluaciones:
                ultimo_intento = IntentoEvaluacion.objects.filter(
                    usuario=enrollment.usuario,
                    evaluacion=evaluacion
                ).order_by('-fecha_intento').first()
                
                student_data['items'].append({
                    'tipo': 'evaluacion',
                    'titulo': evaluacion.titulo,
                    'completado': ultimo_intento.aprobado if ultimo_intento else False,
                    'intentos': IntentoEvaluacion.objects.filter(
                        usuario=enrollment.usuario,
                        evaluacion=evaluacion
                    ).count()
                })
            
            heatmap_data.append(student_data)
    
    context = {
        'cursos': cursos,
        'curso_id': int(curso_id) if curso_id else None,
        'heatmap_data': heatmap_data,
    }
    return render(request, 'reportes/progreso_heatmap.html', context)


@login_required
@admin_required
def dashboard_ia(request):
    tipo = request.GET.get('tipo')
    
    context = {'tipo_seleccionado': tipo}
    
    if not tipo:
        from pacientes.models import ReporteAsignacionIA
        from .models import ReporteUpskilling, ReporteNuevosCursos
        context['historial_asignacion'] = ReporteAsignacionIA.objects.select_related('paciente').all()[:50]
        context['historial_upskilling'] = ReporteUpskilling.objects.all()[:50]
        context['historial_nuevos_cursos'] = ReporteNuevosCursos.objects.all()[:50]
    
    if tipo in ['upskilling', 'nuevos_cursos']:
        from .services import obtener_analisis_institucional
        from .models import ReporteUpskilling, ReporteNuevosCursos
        
        regenerar = request.GET.get('regenerar') == 'true'
        reporte_id = request.GET.get('reporte_id')
        reporte = None
        
        if reporte_id:
            if tipo == 'upskilling':
                reporte = ReporteUpskilling.objects.filter(id=reporte_id).first()
            else:
                reporte = ReporteNuevosCursos.objects.filter(id=reporte_id).first()
        else:
            # Si no hay ID, el usuario hizo clic en "Ejecutar Análisis", forzamos a crear uno nuevo
            reporte = None
            
        if reporte and not regenerar:
            resultado_ia = reporte.datos_json
            fecha_generacion = reporte.fecha_generacion
        else:
            resultado_ia = obtener_analisis_institucional(tipo)
            if not resultado_ia.get('error'):
                if tipo == 'upskilling':
                    reporte = ReporteUpskilling.objects.create(datos_json=resultado_ia)
                else:
                    reporte = ReporteNuevosCursos.objects.create(datos_json=resultado_ia)
                
                from django.http import HttpResponseRedirect
                return HttpResponseRedirect(f"?tipo={tipo}&reporte_id={reporte.id}")
            else:
                fecha_generacion = None
        
        context['fecha_generacion'] = fecha_generacion
        if tipo == 'upskilling' and not resultado_ia.get('error'):
            from django.db.models import Count, Q, Exists, OuterRef
            from usuarios.models import Usuario
            from cursos.models import InscripcionCurso
            
            upskilling_list = resultado_ia.get('upskilling', [])
            filtered_upskilling = []
            needs_save = False
            
            for item in upskilling_list:
                try:
                    c_id = int(item.get('curso_id', 0))
                    
                    if 'sugeridos_ids' not in item:
                        colabs = Usuario.objects.filter(rol='colaborador').exclude(
                            inscripciones__curso_id=c_id
                        )
                        patologias = item.get('patologias_objetivo', [])
                        if patologias and isinstance(patologias, list):
                            q_pats = Q()
                            for p in patologias:
                                q_pats |= Q(pacientes_asignados__patologias__icontains=p.strip())
                            colabs = colabs.filter(q_pats).distinct()
                        else:
                            # Fallback si no hay patologías, filtramos por rol por defecto
                            roles = item.get('roles_ideales', [])
                            if roles and isinstance(roles, list):
                                q_roles = Q()
                                for r in roles:
                                    q_roles |= Q(cargo__nombre__icontains=r.split('/')[0].strip())
                                colabs = colabs.filter(q_roles)
                            
                        sugeridos = list(colabs.annotate(
                            cursos_pendientes=Count('inscripciones', filter=Q(inscripciones__estado__in=['asignado', 'en_progreso']))
                        ).order_by('cursos_pendientes')[:3].values_list('id', flat=True))
                        
                        item['sugeridos_ids'] = sugeridos
                        needs_save = True

                except (ValueError, TypeError):
                    pass
            
            # Guardamos el JSON limpio en la base de datos ANTES de inyectarle QuerySets
            if needs_save and reporte:
                reporte.datos_json = resultado_ia
                reporte.save()
                
            # Ahora inyectamos los QuerySets para que el template los pueda renderizar
            for item in upskilling_list:
                try:
                    c_id = int(item.get('curso_id', 0))
                    if item.get('sugeridos_ids'):
                        colabs_finales = Usuario.objects.filter(id__in=item['sugeridos_ids']).annotate(
                            cursos_pendientes=Count('inscripciones', filter=Q(inscripciones__estado__in=['asignado', 'en_progreso'])),
                            ya_inscrito=Exists(InscripcionCurso.objects.filter(usuario=OuterRef('pk'), curso_id=c_id))
                        )
                        item['colaboradores_sugeridos'] = colabs_finales
                        filtered_upskilling.append(item)
                except (ValueError, TypeError):
                    pass
            
            resultado_ia['upskilling'] = filtered_upskilling
            
        context['resultado_ia'] = resultado_ia
    elif tipo == 'pacientes':
        from pacientes.models import Paciente
        context['pacientes'] = Paciente.objects.all()
        
    return render(request, 'reportes/dashboard_ia.html', context)


@login_required
@admin_required
def descargar_matriz_senama(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="matriz_cumplimiento_senama.pdf"'

    doc = SimpleDocTemplate(response, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle(name='TitleStyle', parent=styles['Heading1'], alignment=1, fontSize=16, spaceAfter=10)
    elements.append(Paragraph("Matriz de cumplimiento SENAMA", title_style))

    # Table 1: Users
    data = [['RUT', 'Nombre', 'Cargo', 'Residencia', 'Atención directa', 'Horas exigidas', 'Horas ejecutadas', 'Cumple']]
    
    brechas = []
    usuarios = Usuario.objects.filter(rol='colaborador').prefetch_related('inscripciones__curso', 'pacientes_asignados', 'cargo')
    
    total_cumplen = 0
    total_usuarios = 0

    for user in usuarios:
        total_usuarios += 1
        cargo = user.cargo.nombre if user.cargo else "Sin cargo"
        atencion_directa = 'Sí' if user.pacientes_asignados.exists() else 'No'
        
        # Horas exigidas = suma de las horas de todos los cursos asignados al usuario
        horas_exigidas = sum(insc.curso.duracion_horas for insc in user.inscripciones.all())
        # Horas ejecutadas = suma de las horas de los cursos completados
        horas_ejecutadas = sum(insc.curso.duracion_horas for insc in user.inscripciones.filter(estado='completado'))
        
        cumple = 'Sí' if (horas_ejecutadas >= horas_exigidas and horas_exigidas > 0) or horas_exigidas == 0 else 'No'
        
        if cumple == 'Sí':
            total_cumplen += 1
        elif horas_exigidas > 0:
            faltan = horas_exigidas - horas_ejecutadas
            brechas.append([
                'Alta', 'Horas de capacitación', user.get_full_name() or user.username,
                f"{user.get_full_name()} acumula {horas_ejecutadas} de {horas_exigidas} horas exigidas en el período.",
                f"Asignar tiempo para completar las {faltan} horas pendientes."
            ])

        data.append([
            user.rut,
            user.get_full_name() or user.username,
            cargo,
            'ELEAM Kimün',
            atencion_directa,
            str(horas_exigidas),
            str(horas_ejecutadas),
            cumple
        ])

    # Subtitle with global compliance
    admin_name = request.user.get_full_name() or request.user.username
    cumplimiento_pct = round((total_cumplen / total_usuarios * 100) if total_usuarios > 0 else 100)
    subtitle_text = f"Alcance: ELEAM Kimün | Período: Histórico al {timezone.now().strftime('%d/%m/%Y')} | Cumplimiento: {cumplimiento_pct}%<br/>Generado el {timezone.now().strftime('%d/%m/%Y %H:%M')} por {admin_name}."
    elements.append(Paragraph(subtitle_text, styles['Normal']))
    elements.append(Spacer(1, 20))

    # Style Table 1
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3F51B5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 30))

    # Table 2: Brechas
    if brechas:
        elements.append(Paragraph(f"Brechas detectadas ({len(brechas)})", styles['Heading2']))
        elements.append(Spacer(1, 10))
        brechas_data = [['Severidad', 'Categoría', 'Entidad', 'Descripción', 'Recomendación']] + brechas
        t2 = Table(brechas_data, repeatRows=1, colWidths=[60, 120, 100, 200, 200])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#B71C1C')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#FFCC80')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(t2)

    doc.build(elements)
    return response


@login_required
@admin_required
def descargar_pdf_art33(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    cargo_id = request.GET.get('cargo')

    from cursos.models import Curso
    nombres_cursos = Curso.objects.values_list('titulo', flat=True)

    queryset = RegistroSesionArt33.objects.select_related('usuario', 'usuario__cargo').filter(modulo_visitado__in=nombres_cursos)
    
    if fecha_inicio:
        queryset = queryset.filter(fecha_entrada__gte=fecha_inicio)
    if fecha_fin:
        queryset = queryset.filter(fecha_entrada__lte=fecha_fin + " 23:59:59")
    if cargo_id:
        queryset = queryset.filter(usuario__cargo_id=cargo_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="registro_asistencia_digital_Art33.pdf"'

    doc = SimpleDocTemplate(response, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(name='TitleStyle', parent=styles['Heading1'], alignment=1, fontSize=16, spaceAfter=10)
    elements.append(Paragraph("Registro de Asistencia Digital (Art. 33)", title_style))

    admin_name = request.user.get_full_name() or request.user.username
    subtitle_text = f"Generado el {timezone.now().strftime('%d/%m/%Y %H:%M')} por {admin_name}"
    elements.append(Paragraph(subtitle_text, styles['Normal']))
    elements.append(Spacer(1, 20))

    data = [['FECHA', 'RUT', 'COLABORADOR', 'CARGO', 'MÓDULO', 'ENTRADA', 'SALIDA', 'MINUTOS', 'DIRECCIÓN IP']]
    
    for registro in queryset:
        if registro.fecha_salida:
            minutos = int((registro.fecha_salida - registro.fecha_entrada).total_seconds() / 60)
            salida_str = registro.fecha_salida.strftime('%H:%M:%S')
        else:
            minutos = 0
            salida_str = 'En curso'

        cargo_nombre = registro.usuario.cargo.nombre if registro.usuario.cargo else 'Sin Cargo'
        
        data.append([
            registro.fecha_entrada.strftime('%d/%m/%Y'),
            registro.usuario.rut,
            registro.usuario.get_full_name() or registro.usuario.username,
            cargo_nombre,
            registro.modulo_visitado,
            registro.fecha_entrada.strftime('%H:%M:%S'),
            salida_str,
            f"{minutos} min",
            registro.direccion_ip or 'N/A'
        ])

    t = Table(data, repeatRows=1)
    
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1C314A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]
    
    for i in range(1, len(data)):
        bg_color = colors.whitesmoke if i % 2 != 0 else colors.white
        style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg_color))
        
    t.setStyle(TableStyle(style_cmds))
    elements.append(t)

    doc.build(elements)
    return response


@login_required
@admin_required
def descargar_zip_certificados(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    cargo_id = request.GET.get('cargo')

    queryset = InscripcionCurso.objects.select_related('usuario', 'usuario__cargo', 'curso').filter(estado__in=['completado', 'en_progreso'])

    if fecha_inicio:
        queryset = queryset.filter(fecha_asignacion__gte=fecha_inicio)
    if fecha_fin:
        queryset = queryset.filter(fecha_asignacion__lte=fecha_fin + " 23:59:59")
    if cargo_id:
        queryset = queryset.filter(usuario__cargo_id=cargo_id)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for insc in queryset:
            rut_folder = f"rut_{insc.usuario.rut.replace('.', '_').replace('-', '_')}"
            
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []
            title = "Certificado de Aprobación" if insc.estado == 'completado' else "Constancia de Alumno Regular"
            elements.append(Paragraph(title, styles['Heading1']))
            elements.append(Spacer(1, 20))
            elements.append(Paragraph(f"El usuario {insc.usuario.get_full_name()} ({insc.usuario.rut})", styles['Normal']))
            verb = "ha completado satisfactoriamente" if insc.estado == 'completado' else "se encuentra cursando actualmente"
            elements.append(Paragraph(f"{verb} el curso {insc.curso.titulo}.", styles['Normal']))
            
            doc.build(elements)
            
            pdf_content = pdf_buffer.getvalue()
            pdf_buffer.close()

            base_folder = "certificados_cursos" if insc.estado == 'completado' else "certificado_alumno_regular"
            file_name = f"certificado_{insc.curso.titulo[:10].replace(' ', '_').upper()}.pdf"
            
            zip_file.writestr(f"{base_folder}/{rut_folder}/{file_name}", pdf_content)

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="documentos_capacitacion.zip"'
    return response


import json
from django.http import JsonResponse

@login_required
def registrar_tiempo_sesion(request):
    if request.method == 'POST' and request.user.rol == 'colaborador':
        try:
            data = json.loads(request.body)
            curso_id = data.get('curso_id')
            if not curso_id:
                return JsonResponse({'status': 'error', 'msg': 'no curso_id'})
                
            from cursos.models import Curso
            curso = Curso.objects.get(id=curso_id)
            
            from datetime import timedelta
            now = timezone.now()
            
            # Buscamos la última sesión que haya tenido
            sesion = RegistroSesionArt33.objects.filter(
                usuario=request.user,
                modulo_visitado=curso.titulo,
            ).order_by('-fecha_salida').first()
            
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
                
            # Si existe una sesión y su último latido de salida fue hace MENOS de 15 minutos, la continuamos.
            # Si pasaron más de 15 minutos de inactividad, se considera una sesión totalmente nueva.
            if sesion and sesion.fecha_salida and (now - sesion.fecha_salida) <= timedelta(minutes=15):
                sesion.fecha_salida = now
                sesion.direccion_ip = ip
                sesion.save()
            else:
                RegistroSesionArt33.objects.create(
                    usuario=request.user,
                    modulo_visitado=curso.titulo,
                    fecha_entrada=now,
                    fecha_salida=now,
                    direccion_ip=ip
                )
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': str(e)})
    return JsonResponse({'status': 'invalid'})

@login_required
@admin_required
def descargar_pdf_art33(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    cargo_id = request.GET.get('cargo')

    from cursos.models import Curso
    nombres_cursos = Curso.objects.values_list('titulo', flat=True)

    queryset = RegistroSesionArt33.objects.select_related('usuario', 'usuario__cargo').filter(modulo_visitado__in=nombres_cursos)
    
    if fecha_inicio:
        queryset = queryset.filter(fecha_entrada__gte=fecha_inicio)
    if fecha_fin:
        queryset = queryset.filter(fecha_entrada__lte=fecha_fin + " 23:59:59")
    if cargo_id:
        queryset = queryset.filter(usuario__cargo_id=cargo_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="registro_asistencia_digital_Art33.pdf"'

    doc = SimpleDocTemplate(response, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(name='TitleStyle', parent=styles['Heading1'], alignment=1, fontSize=16, spaceAfter=10)
    elements.append(Paragraph("Registro de Asistencia Digital (Art. 33)", title_style))

    admin_name = request.user.get_full_name() or request.user.username
    subtitle_text = f"Generado el {timezone.now().strftime('%d/%m/%Y %H:%M')} por {admin_name}"
    elements.append(Paragraph(subtitle_text, styles['Normal']))
    elements.append(Spacer(1, 20))

    data = [['FECHA', 'RUT', 'COLABORADOR', 'CARGO', 'MÓDULO', 'ENTRADA', 'SALIDA', 'MINUTOS', 'DIRECCIÓN IP']]
    
    for registro in queryset:
        if registro.fecha_salida:
            minutos = int((registro.fecha_salida - registro.fecha_entrada).total_seconds() / 60)
            salida_str = registro.fecha_salida.strftime('%H:%M:%S')
        else:
            minutos = 0
            salida_str = 'En curso'

        cargo_nombre = registro.usuario.cargo.nombre if registro.usuario.cargo else 'Sin Cargo'
        
        data.append([
            registro.fecha_entrada.strftime('%d/%m/%Y'),
            registro.usuario.rut,
            registro.usuario.get_full_name() or registro.usuario.username,
            cargo_nombre,
            registro.modulo_visitado,
            registro.fecha_entrada.strftime('%H:%M:%S'),
            salida_str,
            f"{minutos} min",
            registro.direccion_ip or 'N/A'
        ])

    t = Table(data, repeatRows=1)
    
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1C314A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]
    
    for i in range(1, len(data)):
        bg_color = colors.whitesmoke if i % 2 != 0 else colors.white
        style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg_color))
        
    t.setStyle(TableStyle(style_cmds))
    elements.append(t)

    doc.build(elements)
    return response


@login_required
@admin_required
def descargar_zip_certificados(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    cargo_id = request.GET.get('cargo')

    queryset = InscripcionCurso.objects.select_related('usuario', 'usuario__cargo', 'curso').filter(estado__in=['completado', 'en_progreso'])

    if fecha_inicio:
        queryset = queryset.filter(fecha_asignacion__gte=fecha_inicio)
    if fecha_fin:
        queryset = queryset.filter(fecha_asignacion__lte=fecha_fin + " 23:59:59")
    if cargo_id:
        queryset = queryset.filter(usuario__cargo_id=cargo_id)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for insc in queryset:
            rut_folder = f"rut_{insc.usuario.rut.replace('.', '_').replace('-', '_')}"
            
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []
            title = "Certificado de Aprobación" if insc.estado == 'completado' else "Constancia de Alumno Regular"
            elements.append(Paragraph(title, styles['Heading1']))
            elements.append(Spacer(1, 20))
            elements.append(Paragraph(f"El usuario {insc.usuario.get_full_name()} ({insc.usuario.rut})", styles['Normal']))
            verb = "ha completado satisfactoriamente" if insc.estado == 'completado' else "se encuentra cursando actualmente"
            elements.append(Paragraph(f"{verb} el curso {insc.curso.titulo}.", styles['Normal']))
            
            doc.build(elements)
            
            pdf_content = pdf_buffer.getvalue()
            pdf_buffer.close()

            base_folder = "certificados_cursos" if insc.estado == 'completado' else "certificado_alumno_regular"
            file_name = f"certificado_{insc.curso.titulo[:10].replace(' ', '_').upper()}.pdf"
            
            zip_file.writestr(f"{base_folder}/{rut_folder}/{file_name}", pdf_content)

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="documentos_capacitacion.zip"'
    return response


import json
from django.http import JsonResponse

@login_required
def registrar_tiempo_sesion(request):
    if request.method == 'POST' and request.user.rol == 'colaborador':
        try:
            data = json.loads(request.body)
            curso_id = data.get('curso_id')
            if not curso_id:
                return JsonResponse({'status': 'error', 'msg': 'no curso_id'})
                
            from cursos.models import Curso
            curso = Curso.objects.get(id=curso_id)
            
            from datetime import timedelta
            now = timezone.now()
            
            # Buscamos la última sesión que haya tenido
            sesion = RegistroSesionArt33.objects.filter(
                usuario=request.user,
                modulo_visitado=curso.titulo,
            ).order_by('-fecha_salida').first()
            
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
                
            # Si existe una sesión y su último latido de salida fue hace MENOS de 15 minutos, la continuamos.
            # Si pasaron más de 15 minutos de inactividad, se considera una sesión totalmente nueva.
            if sesion and sesion.fecha_salida and (now - sesion.fecha_salida) <= timedelta(minutes=15):
                sesion.fecha_salida = now
                sesion.direccion_ip = ip
                sesion.save()
            else:
                RegistroSesionArt33.objects.create(
                    usuario=request.user,
                    modulo_visitado=curso.titulo,
                    fecha_entrada=now,
                    fecha_salida=now,
                    direccion_ip=ip
                )
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': str(e)})
    return JsonResponse({'status': 'invalid'})

@login_required
@admin_required
def asignar_curso_ia(request):
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    from cursos.models import Curso, InscripcionCurso
    from usuarios.models import Usuario

    if request.method == 'POST':
        curso_id = request.POST.get('curso_id')
        colaborador_id = request.POST.get('colaborador_id')
        
        if curso_id and colaborador_id:
            curso = get_object_or_404(Curso, id=curso_id)
            usuario = get_object_or_404(Usuario, id=colaborador_id)
            
            insc, created = InscripcionCurso.objects.get_or_create(
                curso=curso, 
                usuario=usuario, 
                defaults={'estado': 'asignado'}
            )
            
            msg = f'¡{usuario.get_full_name()} ha sido inscrito exitosamente en "{curso.titulo}"!' if created else f'{usuario.get_full_name()} ya estaba inscrito en este curso.'
            return JsonResponse({'status': 'success', 'message': msg})
                
    return JsonResponse({'status': 'error', 'message': 'Datos inválidos'})
