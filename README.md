# Coffee Assistant AI

Plataforma open-source para asistente de café inteligente con WhatsApp. Sistema completo que incluye:

- **Backend Python**: FastAPI con IA para respuestas sobre café
- **WhatsApp Bot**: Integración completa con QR y manejo de mensajes
- **Docker**: Despliegue containerizado listo para producción

## Inicio Rápido con Docker (Recomendado)

```bash
# 1. Clona el repositorio
git clone https://github.com/miguelgonrod/Coffee-Assistant-AI.git
cd Coffee-Assistant-AI

# 2. Configura variables de entorno
cp .env.example .env
# Edita .env con tus credenciales

# 3. Ejecuta con Docker Compose
docker-compose up --build
```

**¡Listo!** El sistema estará corriendo en:
- Backend: http://localhost:8000
- WhatsApp QR: Se mostrará en los logs del contenedor

## Requisitos

### Para Docker (Recomendado)
- Docker 20.10+
- Docker Compose 2.0+

### Para desarrollo local
- Python 3.11+
- Node.js 20+
- Cuenta Google Generative AI (Gemini): `GOOGLE_API_KEY`
- (Opcional) Supabase: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`

## Estructura principal

- `projects/python/don-confiado-backend/app/`: backend FastAPI
- `projects/typescript/don-confiado-whatsapp-qr/`: servicio de WhatsApp QR

## Configuración con Docker

### Variables de Entorno
Configura el archivo `.env` basándote en `.env.example`:

```bash
# Google Generative AI (Obligatorio)
GOOGLE_API_KEY=tu_api_key_de_google_aqui

# Supabase (Opcional)
SUPABASE_URL=tu_url_de_supabase_aqui
SUPABASE_SERVICE_ROLE_KEY=tu_service_role_key_aqui

# Backend URL (para WhatsApp)
BACKEND_URL=http://coffetto-backend:8000
```

### Comandos Docker

```bash
# Construir e iniciar servicios
docker-compose up --build

# Solo iniciar (sin rebuild)
docker-compose up

# Ejecutar en background
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar servicios
docker-compose down
```

## Desarrollo Local (Alternativo)

### Backend Python (FastAPI)

```bash
cd projects/python/don-confiado-backend/app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python tribu-main.py
```

### WhatsApp TypeScript

```bash
cd projects/typescript/don-confiado-whatsapp-qr
npm install
npx tsx src/index.ts
```

## API Endpoints

**Documentación Interactiva:** http://localhost:8000/docs

### Chat Básico
```bash
curl -X POST http://localhost:8000/api/chat_v1.0 \
  -H 'Content-Type: application/json' \
  -d '{"message":"¿Cuál es el mejor método para hacer café?","user_id":"usuario-demo"}'
```

### Chat Avanzado (con Supabase)
```bash
curl -X POST http://localhost:8000/api/chat_v1.1 \
  -H 'Content-Type: application/json' \
  -d '{"message":"Quiero registrar un proveedor NIT 900123456, ACME Café","user_id":"usuario-demo"}'
```

## WhatsApp Integration

1. Una vez iniciados los contenedores, verás un QR en los logs
2. Escanea el QR con WhatsApp Web
3. ¡Empieza a chatear con el asistente de café!

**Comandos disponibles por WhatsApp:**
- Pregunta sobre métodos de preparación
- Consulta sobre tipos de café
- Solicita recetas específicas

## Desarrollo y Personalización

### Estructura del Proyecto
```
Coffee-Assistant-AI/
├── docker-compose.yml          # Orquestación de servicios
├── .env.example               # Variables de entorno template
│
├── projects/python/don-confiado-backend/
│   ├── Dockerfile            # Container del backend
│   └── app/
│       ├── tribu-main.py     # Punto de entrada
│       ├── endpoints/        # API endpoints
│       ├── business/         # Lógica de negocio
│       └── ai/               # Agentes de IA
│
└── projects/typescript/don-confiado-whatsapp-qr/
    ├── Dockerfile            # Container WhatsApp
    └── src/
        ├── index.ts          # Punto de entrada
        └── whatsapp_handler.ts # Manejo de WhatsApp
```

### Hot Reload en Desarrollo
Los volúmenes están configurados para desarrollo:
- Backend: cambios en `/app` se reflejan automáticamente
- WhatsApp: cambios en `/src` requieren reinicio del contenedor

## Solución de Problemas

### Errores Comunes
| Error | Solución |
|-------|----------|
| `GOOGLE_API_KEY` faltante | Configura la clave en `.env` |
| Puerto 8000 ocupado | `docker-compose down` y reinicia |
| QR no aparece | Revisa logs: `docker-compose logs coffetto-whatsapp` |
| Error Supabase | Verifica `SUPABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY` |

### Logs y Debugging
```bash
# Ver logs de todos los servicios
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f coffetto-backend
docker-compose logs -f coffetto-whatsapp

# Entrar a un contenedor para debug
docker exec -it coffetto_backend_service bash
```

## Scripts de Utilidad

El proyecto incluye varios scripts para facilitar el desarrollo y operación:

```bash
# Inicio rápido - verifica configuración e inicia servicios
./scripts/start.sh

# Desarrollo - inicia con logs en vivo y hot reload
./scripts/dev.sh

# Testing - verifica que todos los servicios funcionen
./scripts/test.sh

# Limpieza completa - elimina contenedores, imágenes y datos
./scripts/clean.sh
```

### Descripción de Scripts

| Script | Función | Uso |
|--------|---------|-----|
| `start.sh` | Inicio en producción/demo | Verifica .env, inicia servicios en background |
| `dev.sh` | Desarrollo con logs | Hot reload activado, logs en tiempo real |
| `test.sh` | Verificación de servicios | Prueba endpoints, estado de contenedores |
| `clean.sh` | Limpieza completa | Elimina todo para empezar limpio |

**Nota:** Todos los scripts requieren permisos de ejecución. Se configuran automáticamente al clonar.

## Base de Datos (Opcional - Supabase)

Si quieres usar las funcionalidades avanzadas con Supabase, crea estas tablas en tu base de datos:

### Tabla de Cafés y Métodos
```sql
-- Tabla para almacenar cafés
CREATE TABLE public.cafes (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT,
    nombre_cafe TEXT,
    variedad TEXT,
    proceso TEXT,
    tueste TEXT,
    perfil_sabor TEXT,
    donde_comprar TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabla para almacenar preparaciones de cafés
CREATE TABLE public.metodos_preparacion (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT,
    nombre_metodo TEXT,
    ratio TEXT,
    instrucciones TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);


```

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia BSD 3-Clause - ver el archivo [LICENSE](LICENSE) para detalles.

## 🆘 Soporte

- 📧 **Issues**: [GitHub Issues](https://github.com/miguelgonrod/Coffee-Assistant-AI/issues)
- 💬 **Discusiones**: [GitHub Discussions](https://github.com/miguelgonrod/Coffee-Assistant-AI/discussions)
- 📖 **Wiki**: [Documentación extendida](https://github.com/miguelgonrod/Coffee-Assistant-AI/wiki)

---

**¿Te gusta el proyecto? ⭐ Dale una estrella en GitHub!**
