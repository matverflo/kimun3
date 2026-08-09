from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from .models import Paciente
from django.contrib.auth import get_user_model

Usuario = get_user_model()

@login_required
def dashboard_erp(request):
    pacientes = Paciente.objects.all().order_by('-fecha_ingreso')
    colaboradores = Usuario.objects.filter(rol='colaborador').annotate(
        cursos_realizados=Count('inscripciones', filter=Q(inscripciones__estado='completado')),
        cursos_en_curso=Count('inscripciones', filter=Q(inscripciones__estado='en_progreso')),
        cursos_pendientes=Count('inscripciones', filter=Q(inscripciones__estado='asignado'))
    ).order_by('first_name')
    
    docentes = Usuario.objects.filter(rol__in=['docente', 'admin']).annotate(
        total_cursos=Count('cursos_creados')
    ).order_by('first_name')
    
    context = {
        'pacientes': pacientes,
        'colaboradores': colaboradores,
        'docentes': docentes,
        'total_pacientes': pacientes.count(),
        'total_colaboradores': colaboradores.count(),
        'total_docentes': docentes.count(),
    }
    return render(request, 'pacientes/dashboard.html', context)

@login_required
def expediente_colaborador(request, user_id):
    from django.shortcuts import redirect, get_object_or_404
    from django.utils import timezone
    from datetime import timedelta
    
    if request.user.rol != 'admin':
        return redirect('inicio')
        
    colaborador = get_object_or_404(Usuario, id=user_id, rol='colaborador')
    from django.db.models import Case, When, Value, IntegerField
    inscripciones = colaborador.inscripciones.select_related('curso').annotate(
        orden_estado=Case(
            When(estado='completado', then=Value(1)),
            When(estado='en_progreso', then=Value(2)),
            When(estado='asignado', then=Value(3)),
            default=Value(4),
            output_field=IntegerField(),
        )
    ).order_by('orden_estado', '-fecha_asignacion')
    
    # Obtener límite de pacientes real
    if colaborador.limite_pacientes_personalizado is not None:
        limite_actual = colaborador.limite_pacientes_personalizado
    elif colaborador.cargo:
        limite_actual = colaborador.cargo.limite_pacientes
    else:
        limite_actual = 0
    pacientes_actuales = colaborador.pacientes_asignados.all()
    pacientes_disponibles = Paciente.objects.exclude(colaboradores=colaborador).order_by('nombre_completo')
    
    # Procesamiento para gráfico de horas en los últimos 6 meses
    now = timezone.now()
    six_months_ago = now - timedelta(days=180)
    completed = inscripciones.filter(estado='completado', fecha_termino__gte=six_months_ago)
    
    chart_data = {}
    # Inicializar los últimos 6 meses
    for i in range(5, -1, -1):
        month_date = now - timedelta(days=30*i)
        month_key = month_date.strftime('%Y-%m') # Usar YYYY-MM para ordenamiento correcto
        chart_data[month_key] = 0
        
    for insc in completed:
        if insc.fecha_termino and insc.curso.duracion_horas:
            month_key = insc.fecha_termino.strftime('%Y-%m')
            if month_key in chart_data:
                chart_data[month_key] += insc.curso.duracion_horas
                
    # Métricas de estado de cursos
    cursos_completados = inscripciones.filter(estado='completado').count()
    cursos_en_curso = inscripciones.filter(estado='en_progreso').count()
    cursos_pendientes = inscripciones.filter(estado='asignado').count()
    
    # Horas completadas en los últimos 30 días (Mes) y últimos 7 días (Semana)
    now = timezone.now()
    start_of_month = now - timedelta(days=30)
    start_of_week = now - timedelta(days=7)
    
    # Horas de dedicación (Cursos completados y en progreso asignados recientemente)
    horas_mes = sum(
        insc.curso.duracion_horas for insc in inscripciones.filter(
            estado__in=['completado', 'en_progreso'], 
            fecha_asignacion__gte=start_of_month
        ) if insc.curso.duracion_horas
    )
    
    horas_semana = sum(
        insc.curso.duracion_horas for insc in inscripciones.filter(
            estado__in=['completado', 'en_progreso'], 
            fecha_asignacion__gte=start_of_week
        ) if insc.curso.duracion_horas
    )
    
    # Gráfico por curso de los últimos 30 días y 7 días (Dedicación total)
    last_30_days = now - timedelta(days=30)
    last_7_days = now - timedelta(days=7)
    
    cursos_30 = inscripciones.filter(
        estado__in=['completado', 'en_progreso'],
        fecha_asignacion__gte=last_30_days
    ).order_by('fecha_asignacion')
    
    cursos_7 = inscripciones.filter(
        estado__in=['completado', 'en_progreso'],
        fecha_asignacion__gte=last_7_days
    ).order_by('fecha_asignacion')
    
    chart_labels_30, chart_values_30 = [], []
    chart_labels_7, chart_values_7 = [], []
    
    import textwrap
    
    for insc in cursos_30:
        if insc.curso.duracion_horas:
            # Dividir en líneas si es mayor a 25 caracteres para Chart.js
            titulo_multilinea = textwrap.wrap(insc.curso.titulo, width=25)
            chart_labels_30.append(titulo_multilinea)
            chart_values_30.append(insc.curso.duracion_horas)
            
    for insc in cursos_7:
        if insc.curso.duracion_horas:
            titulo_multilinea = textwrap.wrap(insc.curso.titulo, width=25)
            chart_labels_7.append(titulo_multilinea)
            chart_values_7.append(insc.curso.duracion_horas)
        
    # Cursos disponibles (los que no tiene inscritos)
    from cursos.models import Curso
    cursos_inscritos_ids = inscripciones.values_list('curso_id', flat=True)
    cursos_disponibles = Curso.objects.exclude(id__in=cursos_inscritos_ids).order_by('titulo')

    context = {
        'colaborador': colaborador,
        'inscripciones': inscripciones,
        'limite_actual': limite_actual,
        'pacientes_actuales': pacientes_actuales,
        'cursos_completados': cursos_completados,
        'cursos_en_curso': cursos_en_curso,
        'cursos_pendientes': cursos_pendientes,
        'horas_mes': horas_mes,
        'horas_semana': horas_semana,
        'chart_labels_30': chart_labels_30,
        'chart_values_30': chart_values_30,
        'chart_labels_7': chart_labels_7,
        'chart_values_7': chart_values_7,
        'pacientes_disponibles': pacientes_disponibles,
        'cursos_disponibles': cursos_disponibles,
    }
    return render(request, 'pacientes/expediente_colaborador.html', context)


@login_required
def descargar_certificado(request, inscripcion_id):
    from django.http import HttpResponse, Http404
    from django.shortcuts import get_object_or_404
    from cursos.models import InscripcionCurso
    import locale
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.units import inch
    
    if request.user.rol != 'admin':
        return redirect('inicio')
        
    inscripcion = get_object_or_404(InscripcionCurso, id=inscripcion_id, estado='completado')
    
    # Intentar poner español para la fecha
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    except:
        pass
        
    response = HttpResponse(content_type='application/pdf')
    filename = f"certificado_{inscripcion.usuario.rut}_{inscripcion.curso.id}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Crear PDF
    p = canvas.Canvas(response, pagesize=landscape(A4))
    width, height = landscape(A4)
    
    # Fondo/Borde
    p.setStrokeColorRGB(0.12, 0.23, 0.37) # --color-primary aprox
    p.setLineWidth(4)
    p.rect(30, 30, width - 60, height - 60)
    
    # Borde interior
    p.setStrokeColorRGB(0.8, 0.8, 0.8)
    p.setLineWidth(1)
    p.rect(36, 36, width - 72, height - 72)
    
    # Logo o Institución
    p.setFont("Helvetica-Bold", 16)
    p.setFillColorRGB(0.5, 0.5, 0.5)
    p.drawCentredString(width/2, height - 80, "RESIDENCIA ELEAM HUALPÉN - PLATAFORMA KIMÜN")
    
    # Título
    p.setFillColorRGB(0.1, 0.1, 0.1)
    p.setFont("Helvetica-Bold", 36)
    p.drawCentredString(width/2, height - 160, "CERTIFICADO DE APROBACIÓN")
    
    # Subtítulo
    p.setFont("Helvetica", 16)
    p.drawCentredString(width/2, height - 210, "Se certifica que:")
    
    # Nombre y RUT
    p.setFont("Helvetica-Bold", 26)
    p.drawCentredString(width/2, height - 250, f"{inscripcion.usuario.get_full_name().upper()}")
    p.setFont("Helvetica", 12)
    p.drawCentredString(width/2, height - 275, f"RUT: {inscripcion.usuario.rut}")
    
    # Curso
    p.setFont("Helvetica", 16)
    p.drawCentredString(width/2, height - 330, "ha completado satisfactoriamente el curso:")
    p.setFont("Helvetica-Bold", 22)
    p.drawCentredString(width/2, height - 370, f"{inscripcion.curso.titulo.upper()}")
    
    # Horas y Nota (simulada)
    p.setFont("Helvetica", 14)
    fecha_term = inscripcion.fecha_termino.strftime('%d de %B, %Y') if inscripcion.fecha_termino else ""
    p.drawCentredString(width/2, height - 420, f"Duración: {inscripcion.curso.duracion_horas} horas académicas | Fecha de término: {fecha_term}")
    p.drawCentredString(width/2, height - 445, "Puntuación obtenida: 100% (Aprobado con Distinción)")
    
    # Firmas
    p.setStrokeColorRGB(0.4, 0.4, 0.4)
    p.setLineWidth(1)
    
    p.line(180, 100, 380, 100)
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(280, 85, "Dirección Académica")
    
    p.line(width - 380, 100, width - 180, 100)
    p.drawCentredString(width - 280, 85, "Dirección General ELEAM")
    
    p.showPage()
    p.save()
    return response


@login_required
def asignar_paciente(request, user_id):
    from django.contrib import messages
    from django.shortcuts import redirect, get_object_or_404
    
    if request.user.rol != 'admin' or request.method != 'POST':
        return redirect('inicio')
        
    colaborador = get_object_or_404(Usuario, id=user_id, rol='colaborador')
    paciente_id = request.POST.get('paciente_id')
    
    if paciente_id:
        paciente = get_object_or_404(Paciente, id=paciente_id)
        # Asignar paciente (relación M2M)
        paciente.colaboradores.add(colaborador)
        messages.success(request, f'Paciente {paciente.nombre_completo} asignado correctamente a {colaborador.first_name}.')
        
    return redirect('pacientes:expediente_colaborador', user_id=user_id)


@login_required
def desvincular_paciente(request, user_id, paciente_id):
    from django.contrib import messages
    from django.shortcuts import redirect, get_object_or_404
    
    if request.user.rol != 'admin' or request.method != 'POST':
        return redirect('inicio')
        
    colaborador = get_object_or_404(Usuario, id=user_id, rol='colaborador')
    paciente = get_object_or_404(Paciente, id=paciente_id)
    
    paciente.colaboradores.remove(colaborador)
    messages.success(request, f'Paciente {paciente.nombre_completo} ha sido desvinculado.')
    
    return redirect('pacientes:expediente_colaborador', user_id=user_id)


@login_required
def asignar_curso(request, user_id):
    from django.contrib import messages
    from django.shortcuts import redirect, get_object_or_404
    from cursos.models import Curso, InscripcionCurso
    
    if request.user.rol != 'admin' or request.method != 'POST':
        return redirect('inicio')
        
    colaborador = get_object_or_404(Usuario, id=user_id, rol='colaborador')
    curso_id = request.POST.get('curso_id')
    
    if curso_id:
        curso = get_object_or_404(Curso, id=curso_id)
        # Asignar curso
        InscripcionCurso.objects.get_or_create(
            usuario=colaborador,
            curso=curso,
            defaults={'estado': 'asignado'}
        )
        messages.success(request, f'Curso "{curso.titulo}" asignado correctamente a {colaborador.first_name}.')
        
    return redirect('pacientes:expediente_colaborador', user_id=user_id)


# --- VISTAS DEL EXPEDIENTE DEL PACIENTE ---

@login_required
def expediente_paciente(request, paciente_id):
    from .models import Paciente, HitoClinico, RecetaMedica, RegistroRutinaDiaria
    from usuarios.models import Usuario
    from django.shortcuts import get_object_or_404
    from django.utils import timezone
    import datetime
    
    paciente = get_object_or_404(Paciente, id=paciente_id)
    hitos_clinicos = paciente.hitos_clinicos.all()
    colaboradores_actuales = paciente.colaboradores.all()
    colaboradores_disponibles = Usuario.objects.filter(rol='colaborador').exclude(id__in=colaboradores_actuales.values_list('id', flat=True)).order_by('first_name')
    
    # Lógica de Rutinas de Hoy
    hoy = timezone.now().date()
    registros_hoy = RegistroRutinaDiaria.objects.filter(receta__paciente=paciente, fecha_completada__date=hoy)
    recetas_completadas_ids = registros_hoy.values_list('receta_id', flat=True)
    
    rutinas_pendientes = paciente.recetas.filter(activa=True).exclude(id__in=recetas_completadas_ids)
    rutinas_completadas = registros_hoy
    
    context = {
        'paciente': paciente,
        'hitos_clinicos': hitos_clinicos,
        'colaboradores_actuales': colaboradores_actuales,
        'colaboradores_disponibles': colaboradores_disponibles,
        'rutinas_pendientes': rutinas_pendientes,
        'rutinas_completadas': rutinas_completadas,
    }
    return render(request, 'pacientes/expediente_paciente.html', context)


@login_required
def agregar_hito_clinico(request, paciente_id):
    from .models import Paciente, HitoClinico
    from django.contrib import messages
    from django.shortcuts import redirect, get_object_or_404
    
    if request.user.rol != 'admin' or request.method != 'POST':
        return redirect('inicio')
        
    paciente = get_object_or_404(Paciente, id=paciente_id)
    descripcion = request.POST.get('descripcion')
    importancia = request.POST.get('importancia', 'baja')
    
    if descripcion:
        HitoClinico.objects.create(
            paciente=paciente,
            responsable=request.user,
            descripcion=descripcion,
            importancia=importancia
        )
        messages.success(request, 'Hito clínico agregado correctamente al registro del paciente.')
        
    return redirect('pacientes:expediente_paciente', paciente_id=paciente_id)


@login_required
def asignar_colaborador_a_paciente(request, paciente_id):
    from .models import Paciente
    from usuarios.models import Usuario
    from django.contrib import messages
    from django.shortcuts import redirect, get_object_or_404
    
    if request.user.rol != 'admin' or request.method != 'POST':
        return redirect('inicio')
        
    paciente = get_object_or_404(Paciente, id=paciente_id)
    user_id = request.POST.get('user_id')
    
    if user_id:
        colaborador = get_object_or_404(Usuario, id=user_id)
        paciente.colaboradores.add(colaborador)
        messages.success(request, f'{colaborador.get_full_name()} ha sido asignado a los cuidados del paciente.')
        
    return redirect('pacientes:expediente_paciente', paciente_id=paciente_id)


@login_required
def desvincular_colaborador_de_paciente(request, paciente_id, user_id):
    from .models import Paciente
    from usuarios.models import Usuario
    from django.contrib import messages
    from django.shortcuts import redirect, get_object_or_404
    
    if request.user.rol != 'admin' or request.method != 'POST':
        return redirect('inicio')
        
    paciente = get_object_or_404(Paciente, id=paciente_id)
    colaborador = get_object_or_404(Usuario, id=user_id)
    
    paciente.colaboradores.remove(colaborador)
    messages.success(request, f'{colaborador.get_full_name()} ha sido desvinculado de los cuidados de este paciente.')
    
    return redirect('pacientes:expediente_paciente', paciente_id=paciente_id)


@login_required
def crear_receta_diaria(request, paciente_id):
    from .models import Paciente, RecetaMedica
    from usuarios.models import Usuario
    from django.contrib import messages
    from django.shortcuts import redirect, get_object_or_404
    
    paciente = get_object_or_404(Paciente, id=paciente_id)
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        detalles = request.POST.get('detalles', '')
        user_id = request.POST.get('colaborador_id')
        
        colaborador = None
        if user_id:
            colaborador = get_object_or_404(Usuario, id=user_id)
            
        if titulo:
            RecetaMedica.objects.create(
                paciente=paciente,
                colaborador_encargado=colaborador,
                titulo=titulo,
                detalles=detalles
            )
            messages.success(request, 'Receta / Tarea añadida exitosamente al plan diario.')
            
    return redirect('pacientes:expediente_paciente', paciente_id=paciente_id)


@login_required
def completar_rutina(request, paciente_id, receta_id):
    from .models import Paciente, RecetaMedica, RegistroRutinaDiaria
    from django.contrib import messages
    from django.shortcuts import redirect, get_object_or_404
    from django.utils import timezone
    
    receta = get_object_or_404(RecetaMedica, id=receta_id, paciente_id=paciente_id)
    
    # Prevenir doble completado en el mismo dia
    hoy = timezone.now().date()
    if not RegistroRutinaDiaria.objects.filter(receta=receta, fecha_completada__date=hoy).exists():
        RegistroRutinaDiaria.objects.create(
            receta=receta,
            completada_por=request.user
        )
        messages.success(request, 'Tarea marcada como completada para el día de hoy.')
        
    return redirect('pacientes:expediente_paciente', paciente_id=paciente_id)


@login_required
def descargar_historial_rutinas(request, paciente_id):
    from django.http import HttpResponse
    from django.shortcuts import get_object_or_404
    from .models import Paciente, RegistroRutinaDiaria
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    import io

    paciente = get_object_or_404(Paciente, id=paciente_id)
    registros = RegistroRutinaDiaria.objects.filter(receta__paciente=paciente).order_by('-fecha_completada')

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Estilos Básicos
    p.setFont("Helvetica-Bold", 16)
    p.drawString(1 * inch, 10 * inch, f"Historial de Tareas y Cuidados")
    
    p.setFont("Helvetica", 11)
    p.drawString(1 * inch, 9.7 * inch, f"Paciente: {paciente.nombre_completo}")
    p.drawString(1 * inch, 9.5 * inch, f"RUT: {paciente.rut}")
    
    y = 9 * inch
    p.setFont("Helvetica-Bold", 10)
    p.drawString(1 * inch, y, "Fecha / Hora")
    p.drawString(2.5 * inch, y, "Tarea / Receta")
    p.drawString(5.5 * inch, y, "Completado Por")
    
    p.setStrokeColor(colors.gray)
    p.line(1*inch, y-5, 7.5*inch, y-5)
    
    y -= 0.3 * inch
    p.setFont("Helvetica", 9)
    
    for reg in registros:
        fecha_str = reg.fecha_completada.strftime("%d/%m/%Y %H:%M")
        tarea_str = reg.receta.titulo
        encargado_str = reg.completada_por.get_full_name() if reg.completada_por else "Desconocido"
        
        p.drawString(1 * inch, y, fecha_str)
        p.drawString(2.5 * inch, y, tarea_str[:40]) # Truncar si es muy largo
        p.drawString(5.5 * inch, y, encargado_str)
        
        y -= 0.2 * inch
        if y < 1 * inch:
            p.showPage()
            y = 10 * inch
            p.setFont("Helvetica", 9)

    p.showPage()
    p.save()

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="historial_rutinas_{paciente.rut}.pdf"'
    return response


@login_required
def sugerencia_ia(request, paciente_id):
    from django.shortcuts import render, get_object_or_404
    from .models import Paciente
    from .services import obtener_sugerencia_asignacion
    
    paciente = get_object_or_404(Paciente, id=paciente_id)
    
    # Si la petición es un POST, el usuario quiere asignar al colaborador
    if request.method == 'POST':
        from usuarios.models import Usuario
        from django.contrib import messages
        from django.shortcuts import redirect
        
        colab_id = request.POST.get('colaborador_id')
        if colab_id:
            colaborador = get_object_or_404(Usuario, id=colab_id)
            if colaborador not in paciente.colaboradores.all():
                paciente.colaboradores.add(colaborador)
                messages.success(request, f'¡{colaborador.get_full_name()} asignado exitosamente al paciente vía IA!')
        return redirect('pacientes:expediente_paciente', paciente_id=paciente_id)
    
    # Es un GET, llamamos a la IA
    resultado_ia = obtener_sugerencia_asignacion(paciente_id)
    
    context = {
        'paciente': paciente,
        'resultado_ia': resultado_ia
    }
    return render(request, 'pacientes/sugerencia_ia.html', context)

