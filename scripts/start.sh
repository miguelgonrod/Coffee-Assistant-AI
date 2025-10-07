#!/bin/bash
# Coffee Assistant AI - Script de inicio rápido

set -e  # Parar en caso de error

echo "Coffee Assistant AI - Inicio"
echo "================================="

# Verificar que Docker está corriendo
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker no está corriendo"
    echo "Por favor inicia Docker Desktop o el daemon de Docker"
    exit 1
fi

# Verificar que existe .env
if [ ! -f .env ]; then
    echo "⚠️  Archivo .env no encontrado"
    echo "Copiando .env.example como .env..."
    cp .env.example .env
    echo "✅ .env creado. Por favor edítalo con tus credenciales antes de continuar."
    echo "Presiona Enter cuando hayas configurado tus credenciales..."
    read -p ""
fi

# Verificar GOOGLE_API_KEY
source .env
if [ -z "$GOOGLE_API_KEY" ] || [ "$GOOGLE_API_KEY" = "tu_api_key_de_google_aqui" ]; then
    echo "❌ Error: GOOGLE_API_KEY no configurado en .env"
    echo "Por favor edita el archivo .env y configura tu API key de Google"
    exit 1
fi

echo "Iniciando servicios con Docker Compose..."
docker-compose up --build -d

echo ""
echo "✅ Servicios iniciados correctamente!"
echo ""
echo "Backend API: http://localhost:8000"
echo "Documentación: http://localhost:8000/docs"
echo "WhatsApp: Revisa los logs para el QR"
echo ""
echo "Para ver logs:"
echo "  docker-compose logs -f"
echo ""
echo "Para parar:"
echo "  docker-compose down"
