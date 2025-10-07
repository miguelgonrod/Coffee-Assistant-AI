#!/bin/bash
# Coffee Assistant AI - Script de desarrollo

set -e

echo "Coffee Assistant AI - Modo Desarrollo"
echo "=========================================="

# Función para cleanup al salir
cleanup() {
    echo ""
    echo "🛑 Deteniendo servicios..."
    docker-compose down
    echo "✅ Servicios detenidos"
}

# Configurar trap para cleanup
trap cleanup EXIT INT TERM

# Verificar .env
if [ ! -f .env ]; then
    echo "⚠️  Creando .env desde .env.example..."
    cp .env.example .env
fi

echo "Iniciando en modo desarrollo..."
echo "   - Hot reload habilitado"
echo "   - Logs en tiempo real"
echo ""

# Iniciar servicios y mostrar logs
docker-compose up --build
