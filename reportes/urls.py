from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('', views.dashboard_reportes, name='dashboard_reportes'),
    path('progreso/', views.progreso_heatmap, name='progreso_heatmap'),
    path('curso/<int:curso_pk>/', views.reporte_curso, name='reporte_curso'),
    path('ia/', views.dashboard_ia, name='dashboard_ia'),
    path('matriz-senama/', views.descargar_matriz_senama, name='descargar_senama'),
    path('exportar-zip/', views.descargar_zip_certificados, name='exportar_zip'),
    path('exportar-art33/', views.descargar_pdf_art33, name='exportar_art33'),
    path('ia/asignar/', views.asignar_curso_ia, name='asignar_curso_ia'),
    path('api/registrar-tiempo/', views.registrar_tiempo_sesion, name='registrar_tiempo'),
]