from django.urls import path
from . import views

app_name = 'pacientes'

urlpatterns = [
    path('', views.dashboard_erp, name='dashboard_erp'),
    path('residente/crear/', views.crear_paciente, name='crear_paciente'),
    path('residente/<int:paciente_id>/desactivar/', views.desactivar_paciente, name='desactivar_paciente'),
    path('expediente/colaborador/<int:user_id>/', views.expediente_colaborador, name='expediente_colaborador'),
    path('expediente/docente/<int:user_id>/', views.expediente_docente, name='expediente_docente'),
    path('certificado/<int:inscripcion_id>/', views.descargar_certificado, name='descargar_certificado'),
    path('expediente/colaborador/<int:user_id>/asignar-residente/', views.asignar_paciente, name='asignar_paciente'),
    path('expediente/colaborador/<int:user_id>/desvincular-residente/<int:paciente_id>/', views.desvincular_paciente, name='desvincular_paciente'),
    path('expediente/colaborador/<int:user_id>/asignar-curso/', views.asignar_curso, name='asignar_curso'),
    
    # Rutas del Expediente de Residente
    path('expediente/residente/<int:paciente_id>/', views.expediente_paciente, name='expediente_paciente'),
    path('expediente/residente/<int:paciente_id>/agregar-hito/', views.agregar_hito_clinico, name='agregar_hito_clinico'),
    path('expediente/residente/<int:paciente_id>/asignar-personal/', views.asignar_colaborador_a_paciente, name='asignar_colaborador_a_paciente'),
    path('expediente/residente/<int:paciente_id>/desvincular/<int:user_id>/', views.desvincular_colaborador_de_paciente, name='desvincular_colaborador_de_paciente'),
    
    # Rutinas Médicas
    path('expediente/residente/<int:paciente_id>/crear-rutina/', views.crear_receta_diaria, name='crear_receta_diaria'),
    path('expediente/residente/<int:paciente_id>/completar-rutina/<int:receta_id>/', views.completar_rutina, name='completar_rutina'),
    path('expediente/residente/<int:paciente_id>/historial-rutinas/', views.descargar_historial_rutinas, name='descargar_historial_rutinas'),
    
    # Asignación IA
    path('expediente/residente/<int:paciente_id>/sugerencia-ia/', views.sugerencia_ia, name='sugerencia_ia'),
    path('expediente/residente/<int:paciente_id>/sugerencia-ia/eliminar/<int:reporte_id>/', views.eliminar_reporte_ia, name='eliminar_reporte_ia'),
]
