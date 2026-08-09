import os
import json
from openai import OpenAI
from django.conf import settings
from .models import Paciente
from usuarios.models import Usuario

def obtener_sugerencia_asignacion(paciente_id):
    """
    Se conecta a la API de OpenAI (o compatible con Qwen) para analizar los
    datos del paciente y recomendar cuidadores.
    """
    paciente = Paciente.objects.get(id=paciente_id)
    
    # Obtener colaboradores disponibles (no asignados actualmente al paciente)
    colaboradores_actuales = paciente.colaboradores.all()
    colaboradores_disponibles = Usuario.objects.filter(rol='colaborador').exclude(id__in=colaboradores_actuales.values_list('id', flat=True))
    
    # Preparar el contexto para la IA
    datos_paciente = f"""
    Paciente: {paciente.nombre_completo}
    Edad: {paciente.edad}
    Nivel de Dependencia: {paciente.get_nivel_dependencia_display()}
    Patologías: {paciente.patologias}
    Requerimientos Especiales: {paciente.requerimientos_especiales}
    """
    
    candidatos_lista = []
    for c in colaboradores_disponibles:
        cargo_nombre = c.cargo.nombre if c.cargo else "Cuidador General"
        especialidades = c.especialidades_externas or "Ninguna registrada"
        
        # Obtener cursos completados si existen
        cursos_completados = []
        if hasattr(c, 'inscripciones'):
            from cursos.models import InscripcionCurso
            inscripciones = c.inscripciones.filter(estado='completado')
            cursos_completados = [i.curso.titulo for i in inscripciones]
            
        cursos_str = ", ".join(cursos_completados) if cursos_completados else "Sin cursos internos completados"
        
        candidatos_lista.append(
            f"- ID: {c.id} | Nombre: {c.get_full_name()} | Cargo: {cargo_nombre} | Especialidades: {especialidades} | Cursos Completados: {cursos_str}"
        )
        
    datos_candidatos = "\n".join(candidatos_lista)
    
    if not candidatos_lista:
        return {"error": "No hay cuidadores disponibles para analizar."}

    # Inicializar cliente
    api_key = os.getenv('OPENAI_API_KEY')
    model_name = os.getenv('MODEL_API', 'gpt-3.5-turbo')
    
    if not api_key:
        return {"error": "No se ha configurado la API KEY en el archivo .env"}
        
    # Lógica de URL base para Qwen (DashScope) u otros
    client_kwargs = {'api_key': api_key}
    if 'qwen' in model_name.lower():
        # Usamos el endpoint Internacional porque las cuentas de Latam/Europa lo requieren
        client_kwargs['base_url'] = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        
    client = OpenAI(**client_kwargs)
    
    system_prompt = """
    Eres un Coordinador Clínico Jefe (IA Médica) de una residencia de pacientes gerontológicos y dependientes.
    Tu tarea es analizar el perfil de un paciente y sugerir a los cuidadores MÁS ADECUADOS de la lista disponible.
    
    INSTRUCCIONES CLAVES:
    1. Redacta un 'resumen_caso' clínico y profesional detallando los riesgos y necesidades del paciente.
    2. Identifica 4 a 6 'habilidades_sugeridas' clave (ej. Atención centrada en la persona, Prevención de caídas).
    3. Identifica 2 a 3 'certificaciones_requeridas' ideales para este caso.
    4. Evalúa a cada candidato disponible, dale un 'match_rate' (0 al 100).
    5. Para cada candidato recomendado, en 'certificaciones_cumplidas', enumera qué cursos o especialidades *reales* de los que tiene registrados le sirven para este caso.
    6. Su justificación debe ser analítica y profesional.
    
    Devuelve EXACTAMENTE un objeto JSON válido con este esquema, sin texto extra, sin formato markdown ```json :
    {
      "resumen_caso": "Caso de un adulto mayor con...",
      "habilidades_sugeridas": ["Habilidad 1", "Habilidad 2"],
      "certificaciones_requeridas": ["Certificación 1", "Certificación 2"],
      "recomendaciones": [
        {
          "id_colaborador": 12,
          "nombre": "Juan Perez",
          "cargo": "TENS",
          "match_rate": 85,
          "certificaciones_cumplidas": ["Curso de Demencia", "IAAS"],
          "justificacion": "Excelente compatibilidad. Posee el curso aprobado de..."
        }
      ]
    }
    """
    
    user_prompt = f"Datos del Paciente:\n{datos_paciente}\n\nCandidatos Disponibles:\n{datos_candidatos}"
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        
        content = response.choices[0].message.content.strip()
        # Clean potential markdown
        if content.startswith('```json'):
            content = content.replace('```json', '', 1)
        if content.endswith('```'):
            content = content[:-3]
            
        data = json.loads(content)
        return data
        
    except Exception as e:
        return {"error": f"Error de conexión con la IA: {str(e)}"}
