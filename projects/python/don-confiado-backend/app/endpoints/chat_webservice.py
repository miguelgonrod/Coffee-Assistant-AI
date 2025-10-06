from fastapi import APIRouter, HTTPException
from fastapi_utils.cbv import cbv

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

"""Chat endpoints sin utilizar helpers de memoria de LangChain.

Se usa un almacenamiento en memoria simple (dict + listas) por usuario
para construir el contexto de conversación y se generan prompts como cadenas.
"""

from endpoints.dto.message_dto import (ChatRequestDTO)
from supabase import create_client, Client

# --- Configuración de entorno ---
load_dotenv()


# --- Router y clase del servicio de chat ---
chat_webservice_api_router = APIRouter()

# Memoria en proceso por usuario: { user_id: [ {"role": "human"|"ai", "content": str }, ... ] }
_memory_store = {}

# Cliente global de Supabase
_supabase_client = None


def _get_supabase_client():
    """Inicializa y retorna el cliente de Supabase"""
    global _supabase_client
    if _supabase_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if supabase_url and supabase_key:
            _supabase_client = create_client(supabase_url, supabase_key)
    return _supabase_client


def _get_history(user_id: str):
    if user_id not in _memory_store:
        _memory_store[user_id] = []
    return _memory_store[user_id]


def _append_message(user_id: str, role: str, content: str) -> None:
    history = _get_history(user_id)
    history.append({"role": role, "content": content})


def _history_as_text(user_id: str) -> str:
    lines = []
    for msg in _get_history(user_id):
        if msg.get("role") == "human":
            lines.append(f"Usuario: {msg.get('content', '')}")
        elif msg.get("role") == "ai":
            lines.append(f"Asistente: {msg.get('content', '')}")
    return "\n".join(lines)


def _valid_value(value: object) -> bool:
    """Valida que un valor no sea None, vacío o 'null'"""
    if value is None:
        return False
    text = str(value).strip()
    if text == "":
        return False
    if text.lower() == "null":
        return False
    return True


@cbv(chat_webservice_api_router)
class ChatWebService:
    # --- v1.0: Chat con memoria en sesión ---
    @chat_webservice_api_router.post("/api/chat_v1.0")
    async def chat_with_memory(self, request: ChatRequestDTO):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            api_key = input("Por favor, ingrese su API KEY de Google (GOOGLE_API_KEY): ")
            os.environ["GOOGLE_API_KEY"] = api_key

        # Modelo y prompt del sistema
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

        system_prompt = """ROLE:
            Coffetto, un asistente de inteligencia artificial especializado en café que actúa como
            tu compañero cafetero personal. Es un experto apasionado que te ayuda a descubrir,
            registrar y preparar el café perfecto para tu gusto.

            TASK:
            Mantener una conversación amigable con el usuario sobre café, siempre iniciando con un
            saludo personalizado y preguntando su nombre. Después del saludo inicial, presentarse
            brevemente como Coffetto en 1–2 frases, explicando que soy tu asistente para todo lo
            relacionado con café. Luego, responder de manera clara y concisa cualquier pregunta
            usando solo la información provista en el contexto.

            CONTEXT:
            Coffetto está diseñado para amantes del café que desean explorar, organizar y perfeccionar
            su experiencia cafetera. Mi misión es ayudarte a descubrir nuevos sabores, registrar tus
            cafés favoritos y aprender las mejores técnicas de preparación.

            Capacidades principales:
            1. Registro de cafés favoritos:
            - Guardar información detallada de cada café: nombre, variedad, proceso, tueste, perfil de sabor
            - Registrar dónde comprar cada café para futuras referencias
            - Organizar tu colección personal de cafés preferidos

            2. Recomendaciones personalizadas:
            - Sugerir cafés basados en tus gustos y preferencias
            - Encontrar cafés similares a los que ya te gustan
            - Descubrir nuevos sabores que podrían interesarte

            3. Métodos de preparación:
            - Registrar técnicas de preparación con ratios específicos
            - Guardar instrucciones detalladas para cada método
            - Calcular proporciones exactas según la cantidad de café deseada

            4. Recomendaciones de preparación:
            - Sugerir el mejor método para cada tipo de café
            - Ajustar recetas según tus preferencias
            - Optimizar la extracción para resaltar los sabores del café

            Usuarios objetivo:
            - Amantes del café que quieren organizar su experiencia cafetera
            - Personas que buscan descubrir nuevos cafés y métodos de preparación
            - Baristas caseros que desean perfeccionar sus técnicas

            Propuesta de valor:
            - Personaliza tu experiencia cafetera según tus gustos únicos
            - Organiza y recuerda toda la información importante sobre tus cafés
            - Te guía para preparar el café perfecto en casa
            - Te ayuda a explorar el mundo del café de manera ordenada

            Estilo de comunicación:
            - Apasionado, cercano y conocedor del café
            - Sin tecnicismos innecesarios, pero con precisión cafetera
            - Siempre entusiasta y dispuesto a compartir conocimiento sobre café

            CONSTRAINTS:
            - Nunca inventar datos sobre cafés específicos o lugares de compra
            - No inventar capacidades o información que no esté en este contexto
            - Mantener siempre un tono apasionado pero confiable sobre el café
            - Hablar en primera persona como "Coffetto"

            OUTPUT_POLICY:
            - Responde en 2–4 frases como máximo
            - Siempre comienza saludando y pidiendo el nombre del usuario
            - Después del saludo, preséntate brevemente como tu asistente de café (1–2 frases)
            - Luego responde a la pregunta del usuario con la información disponible
            - Si no sabes algo, dilo claramente en lugar de inventar

            INSTRUCCIONES ADICIONALES:
            - Siempre empieza con un saludo y la pregunta por el nombre del usuario
            - Mantén todas las respuestas cortas, claras y enfocadas en café
            - Sé entusiasta y conocedor en cada respuesta sobre café
            - NO uses formato Markdown (**, *, _, etc.) ya que no funciona en WhatsApp
            - Usa texto plano sin formato especial
            """

        # Construcción de historial y prompt como texto
        history_text = _history_as_text(request.user_id)
        user_input = request.message
        _append_message(request.user_id, "human", user_input)

        prompt_text = (
            f"{system_prompt}\n\n"
            f"Historial:\n{history_text}\n\n"
            f"Usuario: {user_input}\n"
            f"Asistente:"
        )

        # Respuesta final directa del modelo
        result = llm.invoke(prompt_text)
        reply = getattr(result, "content", str(result))
        _append_message(request.user_id, "ai", reply)

        return {
            "reply": reply,
        }

    # --- v1.1: Clasificación de intención + extracción y registro de distribuidor ---
    @chat_webservice_api_router.post("/api/chat_v1.1")
    async def chat_with_structure_output(self, request: ChatRequestDTO):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            api_key = input("Por favor, ingrese su API KEY de Google (GOOGLE_API_KEY): ")
            os.environ["GOOGLE_API_KEY"] = api_key

        # Modelo base
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

        # Registrar el mensaje actual en memoria y construir historial
        user_input = request.message
        _append_message(request.user_id, "human", user_input)
        history_text = _history_as_text(request.user_id)

        # Esquema de intención + clasificador estructurado
        intention_schema = {
            "title": "UserIntention",
            "description": (
                "Clasifica la intención del mensaje del usuario relacionado con café. "
                "Devuelve solo una de las etiquetas permitidas."
            ),
            "type": "object",
            "properties": {
                "userintention": {
                    "type": "string",
                    "enum": ["Register_coffee", "Register_brewing_method", "Recommend_coffee", "Recommend_brewing", "Show_my_coffees", "Show_my_brewing_methods", "Other"],
                    "description": (
                        "'Register_coffee': cuando el usuario quiere registrar/guardar información de un café que le gusta. "
                        "'Register_brewing_method': cuando el usuario quiere registrar/guardar un método de preparación de café. "
                        "'Recommend_coffee': cuando el usuario pide recomendaciones de café basadas en sus gustos. "
                        "'Recommend_brewing': cuando el usuario pide recomendaciones de método de preparación para un café específico. "
                        "'Show_my_coffees': cuando el usuario pregunta por sus cafés favoritos, registrados o guardados. "
                        "'Show_my_brewing_methods': cuando el usuario pregunta por sus métodos de preparación registrados o guardados. "
                        "'Other': conversación casual u otro propósito relacionado con café."
                    ),
                }
            },
            "required": ["userintention"],
            "additionalProperties": False,
        }

        model_with_structure = llm.with_structured_output(intention_schema)

        # Clasificación de intención (prompt plano)
        classify_text = (
            "Eres un clasificador especializado en café. Lee la conversación y clasifica la intención "
            "estrictamente en una de las etiquetas: 'Register_coffee', 'Register_brewing_method', 'Recommend_coffee', 'Recommend_brewing', 'Show_my_coffees', 'Show_my_brewing_methods' u 'Other'. "
            "Usa 'Register_coffee' cuando el usuario quiere guardar/registrar información de un café. "
            "Usa 'Register_brewing_method' cuando quiere guardar un método de preparación. "
            "Usa 'Recommend_coffee' cuando pide recomendaciones de café. "
            "Usa 'Recommend_brewing' cuando pide recomendaciones de preparación. "
            "Usa 'Show_my_coffees' cuando pregunta por sus cafés favoritos, registrados, guardados o cuáles tiene. "
            "Usa 'Show_my_brewing_methods' cuando pregunta por sus métodos de preparación registrados o cuáles tiene. "
            "En otro caso usa 'Other'.\n\n"
            f"Historial:\n{history_text}\n\n"
            f"Último mensaje del usuario: {user_input}"
        )

        result = model_with_structure.invoke(classify_text)
        print(result)
        user_intention = result[0]["args"].get("userintention")

        if user_intention == "Other":
            # Rama 'Other': respuesta general con memoria y conocimiento de café
            system_prompt = """ROLE:
                Coffetto, un asistente de inteligencia artificial especializado en café que actúa como
                tu compañero cafetero personal. Es un experto apasionado que te ayuda a descubrir,
                registrar y preparar el café perfecto para tu gusto.

                TASK:
                Mantener una conversación amigable con el usuario sobre café. Si es la primera interacción,
                saluda y pregunta el nombre del usuario, luego preséntate brevemente como Coffetto.
                Para conversaciones posteriores, responde preguntas sobre café de manera educativa y
                entusiasta, compartiendo conocimiento sobre el mundo del café.

                CONOCIMIENTO DE CAFÉ:
                - Origen: El café proviene de la planta Coffea, principalmente Coffea arabica y Coffea robusta
                - Historia: Originario de Etiopía, se expandió por el mundo árabe y llegó a Europa en el siglo XVII
                - Variedades: Bourbon, Typica, Geisha, Caturra, Catuai, SL28, entre muchas otras
                - Procesos: Lavado (elimina mucílago), Natural (secado con fruta), Honey (secado con mucílago)
                - Tuestado: Claro (ácido, floral), Medio (equilibrado), Oscuro (amargo, ahumado)
                - Métodos de preparación: Espresso, V60, Chemex, French Press, AeroPress, Cold Brew
                - Ratios comunes: 1:15 a 1:17 (café:agua) para métodos de filtrado
                - Molienda: Gruesa para French Press, media para V60, fina para espresso
                - Extracción: Balance entre dulzor, acidez y amargor
                - Temperatura: 90-96°C para la mayoría de métodos
                - Defectos: Sobre-extracción (amargo), Sub-extracción (ácido/salado)

                CAPACIDADES PRINCIPALES:
                1. Registro de cafés favoritos con información detallada
                2. Recomendaciones personalizadas de café
                3. Registro de métodos de preparación con ratios específicos
                4. Recomendaciones de preparación para cada café
                5. Respuestas educativas sobre café, variedades, procesos y técnicas
                6. Consejos para mejorar la preparación en casa

                ESTILO DE COMUNICACIÓN:
                - Apasionado, cercano y conocedor del café
                - Educativo pero accesible, sin tecnicismos excesivos
                - Siempre entusiasta y dispuesto a compartir conocimiento
                - Respuestas claras y prácticas

                CONSTRAINTS:
                - Nunca inventar datos sobre cafés específicos o lugares de compra
                - Basar las respuestas en conocimiento general bien establecido sobre café
                - Mantener siempre un tono apasionado pero confiable sobre el café
                - Hablar en primera persona como "Coffetto"

                OUTPUT_POLICY:
                - Para saludos iniciales: saluda, pregunta el nombre y preséntate brevemente
                - Para preguntas sobre café: responde de manera educativa en 3-5 frases
                - Mantén las respuestas informativas pero concisas
                - Si no sabes algo específico, dilo claramente y sugiere lo que sí puedes ayudar

                INSTRUCCIONES ADICIONALES:
                - Solo saluda y pide el nombre si es la primera interacción del usuario
                - Para conversaciones existentes, enfócate en responder la pregunta sobre café
                - Sé educativo y comparte conocimiento útil sobre café
                - NO uses formato Markdown (**, *, _, etc.) ya que no funciona en WhatsApp
                - Usa texto plano sin formato especial
            """

            # Usar memoria propia y construir prompt plano
            history_text = _history_as_text(request.user_id)
            user_input = request.message

            prompt_text = (
                f"{system_prompt}\n\n"
                f"Historial:\n{history_text}\n\n"
                f"Usuario: {user_input}\n"
                f"Asistente:"
            )

            ai_result = llm.invoke(prompt_text)
            reply = getattr(ai_result, "content", str(ai_result))
            _append_message(request.user_id, "ai", reply)
            print(ai_result)
            return {
                "userintention": "Other",
                "reply": reply,
            }
        elif user_intention == "Register_coffee":
            # Rama 'Register_coffee': validar completitud y luego extraer datos del café

            # 1) Verificación de completitud para registro de café
            completeness_schema = {
                "title": "CoffeeCompleteness",
                "type": "object",
                "properties": {
                    "is_complete": {"type": "boolean"},
                    "missing_fields": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "nombre_cafe",
                                "variedad",
                                "proceso",
                                "tueste",
                                "perfil_sabor",
                                "donde_comprar"
                            ]
                        }
                    }
                },
                "required": ["is_complete", "missing_fields"],
                "additionalProperties": False,
            }

            completeness_model = llm.with_structured_output(completeness_schema)
            completeness_text = (
                "Evalúa si el mensaje contiene la información completa para registrar un café. "
                "Requisitos mínimos: nombre_cafe. Campos opcionales: variedad, proceso, tueste, perfil_sabor, donde_comprar. "
                "Devuelve is_complete=true solo si al menos el nombre del café está presente en el mensaje. "
                "Si falta el nombre o si el usuario quiere agregar más información, lista los campos faltantes en missing_fields.") + f"\n\nMensaje del usuario: {request.message}"

            completeness = completeness_model.invoke(completeness_text)
            print(completeness)
            is_complete = bool(completeness[0]["args"].get("is_complete", False))
            missing_fields = completeness[0]["args"].get("missing_fields", []) or []

            if not is_complete:
                # Solicitud de datos faltantes para el café
                history_text = _history_as_text(request.user_id)
                user_input = request.message

                request_missing_text = (
                    "ROLE: Coffetto, asistente cafetero entusiasta y amigable.\n"
                    "Pide al usuario, de manera amigable, los datos faltantes del café: "
                    f"{', '.join(missing_fields)}. Explica que estos datos te ayudarán a recordar y recomendar mejor el café. "
                    "NO uses formato Markdown (**, *, etc.) - usa solo texto plano.\n\n"
                    f"Historial:\n{history_text}\n\n"
                    f"Usuario: {user_input}\n"
                    f"Asistente:"
                )

                reply_obj = llm.invoke(request_missing_text)
                reply_text = getattr(reply_obj, "content", str(reply_obj))
                _append_message(request.user_id, "ai", reply_text)

                return {
                    "userintention": "Register_coffee",
                    "status": "need_more_data",
                    "missing_fields": missing_fields,
                    "reply": reply_text,
                }

            # 2) Extracción de datos del café (solo cuando está completo)
            extraction_schema = {
                "title": "CoffeeData",
                "description": (
                    "Extrae únicamente los campos del café que el usuario proporciona. No inventes valores."
                ),
                "type": "object",
                "properties": {
                    "nombre_cafe": {
                        "type": "string",
                        "description": "Nombre del café"
                    },
                    "variedad": {"type": "string", "description": "Variedad del café (ej: Geisha, Bourbon, Typica)"},
                    "proceso": {"type": "string", "description": "Proceso de beneficiado (ej: Lavado, Natural, Honey)"},
                    "tueste": {"type": "string", "description": "Nivel de tueste (ej: Claro, Medio, Oscuro)"},
                    "perfil_sabor": {"type": "string", "description": "Descripción del perfil de sabor y notas"},
                    "donde_comprar": {"type": "string", "description": "Lugar donde se puede comprar este café"}
                },
                "additionalProperties": False,
            }

            extractor = llm.with_structured_output(extraction_schema)
            extract_text = (
                "Extrae los campos del café desde el mensaje del usuario. No inventes datos. "
                "Si un campo no está presente, omítelo (no devuelvas null).\n\n"
                f"Mensaje del usuario: {request.message}"
            )
            extracted_payload = extractor.invoke(extract_text)
            print(extracted_payload)
            extracted = extracted_payload[0]["args"] if isinstance(extracted_payload, list) else extracted_payload

            # Validación credenciales Supabase
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            if not supabase_url or not supabase_key:
                # Respuesta breve informando falta de credenciales
                user_input = request.message

                creds_text = (
                    "ROLE: Coffetto, asistente cafetero.\n"
                    "Informa brevemente que faltan las credenciales de Supabase (SUPABASE_URL / "
                    "SUPABASE_SERVICE_ROLE_KEY) y que deben configurarse antes de continuar guardando cafés. "
                    "NO uses formato Markdown - usa solo texto plano.\n\n"
                    f"Usuario: {user_input}\n"
                    f"Asistente:"
                )
                reply_obj = llm.invoke(creds_text)
                reply_text = getattr(reply_obj, "content", str(reply_obj))
                _append_message(request.user_id, "ai", reply_text)
                return {
                    "userintention": "Register_coffee",
                    "status": "error",
                    "error": "Missing Supabase credentials",
                    "reply": reply_text,
                    "extracted": extracted,
                }

            # Inicialización cliente Supabase
            supabase_client = _get_supabase_client()

            record = {k: v for k, v in extracted.items() if _valid_value(v)}
            record["user_id"] = request.user_id  # Asociar café con el usuario

            try:
                # Inserción en Supabase y confirmación
                response = supabase_client.table("cafes").insert(record).execute()
                data = getattr(response, "data", None)

                user_input = request.message

                confirm_text = (
                    "ROLE: Coffetto, asistente cafetero entusiasta.\n"
                    "Confirma brevemente que el café ha sido registrado exitosamente en tu colección. "
                    "NO uses formato Markdown - usa solo texto plano.\n\n"
                    f"Usuario: {user_input}\n"
                    f"Asistente:"
                )
                reply_obj = llm.invoke(confirm_text)
                reply_text = getattr(reply_obj, "content", str(reply_obj))
                _append_message(request.user_id, "ai", reply_text)

                return {
                    "userintention": "Register_coffee",
                    "status": "created",
                    "data": data,
                    "reply": reply_text,
                }
            except Exception as e:
                # Manejo de error al registrar café
                user_input = request.message

                error_text = (
                    "ROLE: Coffetto, asistente cafetero empático.\n"
                    "Informa que ocurrió un error al registrar el café y que intente de nuevo, "
                    "sin detalles técnicos. NO uses formato Markdown - usa solo texto plano.\n\n"
                    f"Usuario: {user_input}\n"
                    f"Asistente:"
                )
                reply_obj = llm.invoke(error_text)
                reply_text = getattr(reply_obj, "content", str(reply_obj))
                _append_message(request.user_id, "ai", reply_text)
                return {
                    "userintention": "Register_coffee",
                    "status": "error",
                    "error": str(e),
                    "reply": reply_text,
                    "extracted": extracted,
                }

        elif user_intention == "Register_brewing_method":
            # Lógica para registrar métodos de preparación
            completeness_schema = {
                "title": "BrewingMethodCompleteness",
                "type": "object",
                "properties": {
                    "is_complete": {"type": "boolean"},
                    "missing_fields": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["nombre_metodo", "ratio", "instrucciones"]
                        }
                    }
                },
                "required": ["is_complete", "missing_fields"],
                "additionalProperties": False,
            }

            completeness_model = llm.with_structured_output(completeness_schema)
            completeness_text = (
                "Evalúa si el mensaje contiene información completa para registrar un método de preparación de café. "
                "Requisitos mínimos: nombre_metodo. Campos opcionales: ratio, instrucciones. "
                "Devuelve is_complete=true solo si al menos el nombre del método está presente."
            ) + f"\n\nMensaje del usuario: {request.message}"

            completeness = completeness_model.invoke(completeness_text)
            is_complete = bool(completeness[0]["args"].get("is_complete", False))
            missing_fields = completeness[0]["args"].get("missing_fields", []) or []

            if not is_complete:
                history_text = _history_as_text(request.user_id)
                user_input = request.message

                request_missing_text = (
                    "ROLE: Coffetto, asistente cafetero entusiasta.\n"
                    "Pide al usuario los datos faltantes del método de preparación: "
                    f"{', '.join(missing_fields)}. Explica que esto te ayudará a recordar cómo preparar el café. "
                    "NO uses formato Markdown - usa solo texto plano.\n\n"
                    f"Historial:\n{history_text}\n\n"
                    f"Usuario: {user_input}\n"
                    f"Asistente:"
                )

                reply_obj = llm.invoke(request_missing_text)
                reply_text = getattr(reply_obj, "content", str(reply_obj))
                _append_message(request.user_id, "ai", reply_text)

                return {
                    "userintention": "Register_brewing_method",
                    "status": "need_more_data",
                    "missing_fields": missing_fields,
                    "reply": reply_text,
                }

            # Extracción de datos del método de preparación
            extraction_schema = {
                "title": "BrewingMethodData",
                "description": "Extrae los campos del método de preparación. No inventes valores.",
                "type": "object",
                "properties": {
                    "nombre_metodo": {"type": "string", "description": "Nombre del método de preparación"},
                    "ratio": {"type": "string", "description": "Proporción café:agua (ej: 1:15, 1:16)"},
                    "instrucciones": {"type": "string", "description": "Instrucciones paso a paso del método"}
                },
                "additionalProperties": False,
            }

            extractor = llm.with_structured_output(extraction_schema)
            extract_text = (
                "Extrae los campos del método de preparación desde el mensaje del usuario. No inventes datos.\n\n"
                f"Mensaje del usuario: {request.message}"
            )
            extracted_payload = extractor.invoke(extract_text)
            extracted = extracted_payload[0]["args"] if isinstance(extracted_payload, list) else extracted_payload

            # Validación credenciales Supabase
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            if not supabase_url or not supabase_key:
                user_input = request.message
                creds_text = (
                    "ROLE: Coffetto, asistente cafetero.\n"
                    "Informa que faltan las credenciales de Supabase para guardar métodos. "
                    "NO uses formato Markdown - usa solo texto plano.\n\n"
                    f"Usuario: {user_input}\n"
                    f"Asistente:"
                )
                reply_obj = llm.invoke(creds_text)
                reply_text = getattr(reply_obj, "content", str(reply_obj))
                _append_message(request.user_id, "ai", reply_text)
                return {
                    "userintention": "Register_brewing_method",
                    "status": "error",
                    "error": "Missing Supabase credentials",
                    "reply": reply_text,
                }

            # Inicialización cliente Supabase
            supabase_client = _get_supabase_client()

            record = {k: v for k, v in extracted.items() if _valid_value(v)}
            record["user_id"] = request.user_id

            try:
                response = supabase_client.table("metodos_preparacion").insert(record).execute()
                data = getattr(response, "data", None)

                user_input = request.message
                confirm_text = (
                    "ROLE: Coffetto, asistente cafetero entusiasta.\n"
                    "Confirma que el método de preparación ha sido registrado exitosamente. "
                    "NO uses formato Markdown - usa solo texto plano.\n\n"
                    f"Usuario: {user_input}\n"
                    f"Asistente:"
                )
                reply_obj = llm.invoke(confirm_text)
                reply_text = getattr(reply_obj, "content", str(reply_obj))
                _append_message(request.user_id, "ai", reply_text)

                return {
                    "userintention": "Register_brewing_method",
                    "status": "created",
                    "data": data,
                    "reply": reply_text,
                }
            except Exception as e:
                user_input = request.message
                error_text = (
                    "ROLE: Coffetto, asistente cafetero empático.\n"
                    "Informa que ocurrió un error al registrar el método de preparación. "
                    "NO uses formato Markdown - usa solo texto plano.\n\n"
                    f"Usuario: {user_input}\n"
                    f"Asistente:"
                )
                reply_obj = llm.invoke(error_text)
                reply_text = getattr(reply_obj, "content", str(reply_obj))
                _append_message(request.user_id, "ai", reply_text)
                return {
                    "userintention": "Register_brewing_method",
                    "status": "error",
                    "error": str(e),
                    "reply": reply_text,
                }

        elif user_intention == "Recommend_coffee":
            # Lógica para recomendar cafés basada en gustos
            history_text = _history_as_text(request.user_id)
            user_input = request.message

            # Buscar cafés en la base de datos del usuario
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            
            if supabase_url and supabase_key:
                try:
                    supabase_client = _get_supabase_client()
                    
                    # Obtener cafés del usuario
                    cafes_response = supabase_client.table("cafes").select("*").eq("user_id", request.user_id).execute()
                    cafes_data = getattr(cafes_response, "data", [])
                    
                    cafes_context = ""
                    if cafes_data:
                        cafes_context = "Cafés registrados:\n"
                        for cafe in cafes_data:
                            cafes_context += f"- {cafe.get('nombre_cafe', 'Sin nombre')}: {cafe.get('perfil_sabor', 'Sin descripción')}\n"
                    else:
                        cafes_context = "No hay cafés registrados aún."
                        
                except Exception as e:
                    cafes_context = "Error al acceder a la base de datos de cafés."
            else:
                cafes_context = "Base de datos no configurada."

            recommend_text = (
                f"ROLE: Coffetto, asistente cafetero experto en recomendaciones.\n"
                f"Basándote en los gustos del usuario y los cafés registrados, recomienda cafés similares "
                f"o nuevas opciones que podrían gustar. NO uses formato Markdown - usa solo texto plano.\n\n"
                f"{cafes_context}\n\n"
                f"Historial:\n{history_text}\n\n"
                f"Usuario: {user_input}\n"
                f"Asistente:"
            )

            reply_obj = llm.invoke(recommend_text)
            reply_text = getattr(reply_obj, "content", str(reply_obj))
            _append_message(request.user_id, "ai", reply_text)

            return {
                "userintention": "Recommend_coffee",
                "reply": reply_text,
            }

        elif user_intention == "Recommend_brewing":
            # Lógica para recomendar métodos de preparación
            history_text = _history_as_text(request.user_id)
            user_input = request.message

            # Buscar métodos registrados
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            
            if supabase_url and supabase_key:
                try:
                    supabase_client = _get_supabase_client()
                    
                    # Obtener métodos del usuario
                    metodos_response = supabase_client.table("metodos_preparacion").select("*").eq("user_id", request.user_id).execute()
                    metodos_data = getattr(metodos_response, "data", [])
                    
                    metodos_context = ""
                    if metodos_data:
                        metodos_context = "Métodos de preparación registrados:\n"
                        for metodo in metodos_data:
                            metodos_context += f"- {metodo.get('nombre_metodo', 'Sin nombre')}: {metodo.get('ratio', 'Sin ratio')}\n"
                    else:
                        metodos_context = "No hay métodos de preparación registrados aún."
                        
                except Exception as e:
                    metodos_context = "Error al acceder a la base de datos de métodos."
            else:
                metodos_context = "Base de datos no configurada."

            recommend_text = (
                f"ROLE: Coffetto, asistente cafetero experto en preparación.\n"
                f"Recomienda métodos de preparación adecuados para el café mencionado o ayuda a calcular "
                f"las proporciones basándote en los métodos registrados. NO uses formato Markdown - usa solo texto plano.\n\n"
                f"{metodos_context}\n\n"
                f"Historial:\n{history_text}\n\n"
                f"Usuario: {user_input}\n"
                f"Asistente:"
            )

            reply_obj = llm.invoke(recommend_text)
            reply_text = getattr(reply_obj, "content", str(reply_obj))
            _append_message(request.user_id, "ai", reply_text)

            return {
                "userintention": "Recommend_brewing",
                "reply": reply_text,
            }

        elif user_intention == "Show_my_coffees":
            # Mostrar cafés registrados del usuario
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            
            if not supabase_url or not supabase_key:
                user_input = request.message
                creds_text = (
                    "ROLE: Coffetto, asistente cafetero.\n"
                    "Informa que faltan las credenciales de Supabase para consultar los cafés. "
                    "NO uses formato Markdown - usa solo texto plano.\n\n"
                    f"Usuario: {user_input}\n"
                    f"Asistente:"
                )
                reply_obj = llm.invoke(creds_text)
                reply_text = getattr(reply_obj, "content", str(reply_obj))
                _append_message(request.user_id, "ai", reply_text)
                return {
                    "userintention": "Show_my_coffees",
                    "status": "error",
                    "error": "Missing Supabase credentials",
                    "reply": reply_text,
                }

            try:
                supabase_client = _get_supabase_client()
                cafes_response = supabase_client.table("cafes").select("*").eq("user_id", request.user_id).execute()
                cafes_data = getattr(cafes_response, "data", [])
                
                user_input = request.message
                
                if cafes_data:
                    # Formatear lista de cafés
                    cafes_list = ""
                    for i, cafe in enumerate(cafes_data, 1):
                        cafes_list += f"{i}. {cafe.get('nombre_cafe', 'Sin nombre')}"
                        if cafe.get('variedad'):
                            cafes_list += f" - {cafe.get('variedad')}"
                        if cafe.get('perfil_sabor'):
                            cafes_list += f" ({cafe.get('perfil_sabor')})"
                        if cafe.get('donde_comprar'):
                            cafes_list += f" - Disponible en: {cafe.get('donde_comprar')}"
                        cafes_list += "\n"
                    
                    show_text = (
                        f"ROLE: Coffetto, asistente cafetero entusiasta.\n"
                        f"Muestra al usuario sus cafés registrados de manera organizada y amigable. "
                        f"NO uses formato Markdown - usa solo texto plano.\n\n"
                        f"Cafés registrados:\n{cafes_list}\n"
                        f"Usuario: {user_input}\n"
                        f"Asistente:"
                    )
                else:
                    show_text = (
                        f"ROLE: Coffetto, asistente cafetero empático.\n"
                        f"Informa que aún no hay cafés registrados y anima al usuario a registrar su primer café. "
                        f"NO uses formato Markdown - usa solo texto plano.\n\n"
                        f"Usuario: {user_input}\n"
                        f"Asistente:"
                    )
                
                reply_obj = llm.invoke(show_text)
                reply_text = getattr(reply_obj, "content", str(reply_obj))
                _append_message(request.user_id, "ai", reply_text)
                
                return {
                    "userintention": "Show_my_coffees",
                    "status": "success",
                    "data": cafes_data,
                    "reply": reply_text,
                }
                
            except Exception as e:
                user_input = request.message
                error_text = (
                    "ROLE: Coffetto, asistente cafetero empático.\n"
                    "Informa que ocurrió un error al consultar los cafés registrados. "
                    "NO uses formato Markdown - usa solo texto plano.\n\n"
                    f"Usuario: {user_input}\n"
                    f"Asistente:"
                )
                reply_obj = llm.invoke(error_text)
                reply_text = getattr(reply_obj, "content", str(reply_obj))
                _append_message(request.user_id, "ai", reply_text)
                return {
                    "userintention": "Show_my_coffees",
                    "status": "error",
                    "error": str(e),
                    "reply": reply_text,
                }

        elif user_intention == "Show_my_brewing_methods":
            # Mostrar métodos de preparación registrados del usuario
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            
            if not supabase_url or not supabase_key:
                user_input = request.message
                creds_text = (
                    "ROLE: Coffetto, asistente cafetero.\n"
                    "Informa que faltan las credenciales de Supabase para consultar los métodos. "
                    "NO uses formato Markdown - usa solo texto plano.\n\n"
                    f"Usuario: {user_input}\n"
                    f"Asistente:"
                )
                reply_obj = llm.invoke(creds_text)
                reply_text = getattr(reply_obj, "content", str(reply_obj))
                _append_message(request.user_id, "ai", reply_text)
                return {
                    "userintention": "Show_my_brewing_methods",
                    "status": "error", 
                    "error": "Missing Supabase credentials",
                    "reply": reply_text,
                }

            try:
                supabase_client = _get_supabase_client()
                metodos_response = supabase_client.table("metodos_preparacion").select("*").eq("user_id", request.user_id).execute()
                metodos_data = getattr(metodos_response, "data", [])
                
                user_input = request.message
                
                if metodos_data:
                    # Formatear lista de métodos
                    metodos_list = ""
                    for i, metodo in enumerate(metodos_data, 1):
                        metodos_list += f"{i}. {metodo.get('nombre_metodo', 'Sin nombre')}"
                        if metodo.get('ratio'):
                            metodos_list += f" - Ratio: {metodo.get('ratio')}"
                        if metodo.get('instrucciones'):
                            # Limitar instrucciones para no saturar
                            instrucciones = metodo.get('instrucciones')[:100]
                            if len(metodo.get('instrucciones', '')) > 100:
                                instrucciones += "..."
                            metodos_list += f" - {instrucciones}"
                        metodos_list += "\n"
                    
                    show_text = (
                        f"ROLE: Coffetto, asistente cafetero entusiasta.\n"
                        f"Muestra al usuario sus métodos de preparación registrados de manera organizada. "
                        f"NO uses formato Markdown - usa solo texto plano.\n\n"
                        f"Métodos registrados:\n{metodos_list}\n"
                        f"Usuario: {user_input}\n"
                        f"Asistente:"
                    )
                else:
                    show_text = (
                        f"ROLE: Coffetto, asistente cafetero empático.\n"
                        f"Informa que aún no hay métodos de preparación registrados y anima al usuario a registrar su primer método. "
                        f"NO uses formato Markdown - usa solo texto plano.\n\n"
                        f"Usuario: {user_input}\n"
                        f"Asistente:"
                    )
                
                reply_obj = llm.invoke(show_text)
                reply_text = getattr(reply_obj, "content", str(reply_obj))
                _append_message(request.user_id, "ai", reply_text)
                
                return {
                    "userintention": "Show_my_brewing_methods", 
                    "status": "success",
                    "data": metodos_data,
                    "reply": reply_text,
                }
                
            except Exception as e:
                user_input = request.message
                error_text = (
                    "ROLE: Coffetto, asistente cafetero empático.\n"
                    "Informa que ocurrió un error al consultar los métodos registrados. "
                    "NO uses formato Markdown - usa solo texto plano.\n\n"
                    f"Usuario: {user_input}\n"
                    f"Asistente:"
                )
                reply_obj = llm.invoke(error_text)
                reply_text = getattr(reply_obj, "content", str(reply_obj))
                _append_message(request.user_id, "ai", reply_text)
                return {
                    "userintention": "Show_my_brewing_methods",
                    "status": "error", 
                    "error": str(e),
                    "reply": reply_text,
                }
