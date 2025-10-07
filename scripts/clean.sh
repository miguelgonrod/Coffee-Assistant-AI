#!/bin/bash
# Coffee Assistant AI - Script de limpieza

echo "Coffee Assistant AI - Limpieza"
echo "=================================="

echo "Deteniendo servicios..."
docker-compose down

echo "Eliminando contenedores..."
docker-compose rm -f

echo "Eliminando imágenes..."
docker rmi coffee-assistant-ai_coffetto-backend coffee-assistant-ai_coffetto-whatsapp 2>/dev/null || true

echo "Eliminando volúmenes huérfanos..."
docker volume prune -f

echo "Eliminando redes huérfanas..."
docker network prune -f

echo "Limpiando archivos de autenticación de WhatsApp..."
rm -rf projects/typescript/don-confiado-whatsapp-qr/auth_info_baileys

echo ""
echo "Limpieza completada"
echo ""
echo "Para reiniciar limpio:"
echo "  ./scripts/start.sh"
