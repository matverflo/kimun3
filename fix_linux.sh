#!/bin/bash
# Script para solucionar el Error 403 en entornos Linux (Local o Servidor)

echo "========================================"
echo "   Solucionador de Error 403 (Linux)    "
echo "========================================"

# 1. Arreglar permisos de archivos (Caso Nginx/Apache)
echo "[1/2] Ajustando permisos de la carpeta y base de datos..."
# Asegurarse de que el usuario actual y el servidor web puedan leer/escribir
chmod -R 775 .
# Dar permisos específicos a la base de datos si existe
if [ -f "db.sqlite3" ]; then
    chmod 664 db.sqlite3
    echo "Permisos de db.sqlite3 actualizados."
fi

# 2. Configurar automáticamente CSRF y ALLOWED_HOSTS en el .env
echo "[2/2] Configurando Accesos de Red (CSRF y ALLOWED_HOSTS)..."

# Obtener la IP local de la máquina Linux
IP_LOCAL=$(hostname -I | awk '{print $1}')

if [ -z "$IP_LOCAL" ]; then
    echo "No se pudo detectar la IP local automáticamente."
else
    echo "IP Local detectada: $IP_LOCAL"
    
    if [ ! -f ".env" ]; then
        echo "No se encontró un archivo .env, copiando desde .env.example..."
        cp .env.example .env
    fi

    # Revisar si la IP ya está en el .env
    if grep -q "$IP_LOCAL" .env; then
        echo "La IP $IP_LOCAL ya está configurada en el .env."
    else
        echo "Agregando $IP_LOCAL a ALLOWED_HOSTS y CSRF_TRUSTED_ORIGINS en .env..."
        
        # Añadir al final del archivo si no existen, o usar sed para modificarlas.
        # Una forma segura de inyectarlas para pruebas en Linux:
        echo "" >> .env
        echo "# Autoconfigurado por fix_linux.sh" >> .env
        echo "ALLOWED_HOSTS=127.0.0.1,localhost,$IP_LOCAL,*" >> .env
        echo "CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000,http://$IP_LOCAL:8000,http://$IP_LOCAL" >> .env
        
        echo "¡Configuración de red actualizada exitosamente!"
    fi
fi

echo "========================================"
echo "Proceso terminado. Por favor reinicia tu servidor de Django (Gunicorn/runserver)."
echo "Si usas runserver, recuerda correrlo así: python manage.py runserver 0.0.0.0:8000"
echo "========================================"
