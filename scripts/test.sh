#!/bin/bash
# Coffee Assistant AI - Script de testing

echo "Coffee Assistant AI - Testing"
echo "================================="

echo "Verificando que los servicios estén corriendo..."

# Test backend
echo "Probando backend..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs || echo "000")

if [ "$response" = "200" ]; then
    echo "✅ Backend OK (puerto 8000)"
else
    echo "❌ Backend no responde (código: $response)"
fi

# Test API chat
echo "Probando API de chat..."
chat_response=$(curl -s -X POST http://localhost:8000/api/chat_v1.0 \
    -H 'Content-Type: application/json' \
    -d '{"message":"test","user_id":"test-user"}' \
    | grep -o '"reply"' || echo "error")

if [ "$chat_response" = '"reply"' ]; then
    echo "✅ API de chat OK"
else
    echo "❌ API de chat falló"
fi

# Test containers
echo "Estado de contenedores:"
docker-compose ps

echo ""
echo "Uso de recursos:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

echo ""
echo "Para ver logs detallados:"
echo "  docker-compose logs -f [servicio]"
