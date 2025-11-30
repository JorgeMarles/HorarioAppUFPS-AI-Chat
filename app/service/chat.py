from app.config import get_settings

import asyncio

import google.genai as genai
from google.genai import types

from .backend_service import backend_service

import os

import httpx

from typing import Generator, Dict, Any, Callable, Coroutine
import inspect

max_iterations = 10  # Prevenir bucles infinitos


def get_prompt():
    # Obtener la ruta del directorio donde está este archivo
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(
        os.path.dirname(current_dir)
    )  # Sube 2 niveles: service -> app -> ai-assistant
    prompt_path = os.path.join(root_dir, "prompt.txt")

    with open(prompt_path, "r", encoding="utf-8") as file:
        return file.read()


def async_to_sync_wrapper(async_func: Callable[..., Coroutine]):
    """
    Convierte una función async en una callable síncrona segura para threads.
    - Usa el event loop actual si existe (AnyIO/uvicorn)
    - Crea y ejecuta un loop nuevo si está en un worker sin loop
    """
    def sync_wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_running_loop()
            return asyncio.run_coroutine_threadsafe(async_func(*args, **kwargs), loop).result()
        except RuntimeError:
            return asyncio.run(async_func(*args, **kwargs))
    return sync_wrapper

def create_backend_tool(async_method: Callable[..., Coroutine], required_keys: Dict[str, type]):
    """
    Wrapper genérico de herramientas del backend:
    - Recibe el contexto por llamada (no se guarda estado)
    - Valida llaves requeridas
    - Filtra solo parámetros aceptados por la firma del método destino
    - Ejecuta la corrutina de forma segura en entorno sync
    """
    sync_method = async_to_sync_wrapper(async_method)
    allowed_params = set(inspect.signature(async_method).parameters.keys())

    def tool(context: Dict[str, Any] = None, **tool_args):
        if context is None:
            raise ValueError("Context requerido")

        # Merge contexto + args del modelo
        merged: Dict[str, Any] = {**context, **tool_args}

        # Validación requerida
        for key, typ in required_keys.items():
            if key not in merged:
                raise ValueError(f"Falta parámetro requerido: {key}")
            if typ and not isinstance(merged[key], typ):
                try:
                    merged[key] = typ(merged[key])
                except Exception:
                    raise ValueError(f"Tipo inválido para {key}, se esperaba {typ.__name__}")

        # Filtrar solo los parámetros que la función acepta
        filtered = {k: v for k, v in merged.items() if k in allowed_params}

        try:
            return sync_method(**filtered)
        except httpx.HTTPStatusError as e:
            return e.response.text

    return tool

pensum_tool = create_backend_tool(backend_service.get_pensum, {"jwt": str})
# ia-afanador: get_schedule no recibe args; solo requiere jwt del contexto
schedule_tool = create_backend_tool(backend_service.get_schedule, {"jwt": str})
# ia-afanador: add_group usa group_code
add_group_tool = create_backend_tool(backend_service.add_group, {"jwt": str, "group_code": str})
# ia-afanador: delete_group usa group_code
delete_group_tool = create_backend_tool(backend_service.delete_group, {"jwt": str, "group_code": str})
# ia-afanador: change_group usa old_group_code y new_group_code
change_group_tool = create_backend_tool(backend_service.change_group, {"jwt": str, "old_group_code": str, "new_group_code": str})

def get_pensum(context: Dict[str, Any], **kwargs):
    return pensum_tool(context, **kwargs)

def get_schedule(context: Dict[str, Any], **kwargs):
    return schedule_tool(context, **kwargs)

def add_group(context: Dict[str, Any], **kwargs):
    return add_group_tool(context, **kwargs)

def delete_group(context: Dict[str, Any], **kwargs):
    return delete_group_tool(context, **kwargs)

def change_group(context: Dict[str, Any], **kwargs):
    return change_group_tool(context, **kwargs)


TOOLS = {
    "get_pensum": {
        "function": get_pensum,
        "tool": {
            "name": "get_pensum",
            "description": "Retrieve the complete curriculum, including all available courses and subjects, along with the user's progress.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    "get_schedule": {
        "function": get_schedule,
        "tool": {
            "name": "get_schedule",
            "description": "Retrieve the user's current draft schedule, including all added subjects and groups.",
            "parameters": {
                "type": "object",
                "properties": {}
            },
        },
    },
    "add_group": {
        "function": add_group,
        "tool": {
            "name": "add_group",
            "description": "Adds a specific subject group to the user's draft schedule. Returns the updated schedule.",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_code": {
                        "type": "string",
                        "description": "The unique code of the group to add (e.g., '1155503-A')."
                    }
                },
                "required": ["group_code"]
            },
        },
    },
    "delete_group": {
        "function": delete_group,
        "tool": {
            "name": "delete_group",
            "description": "Remove a group from the schedule draft. This also removes the associated subject. Returns the updated schedule.",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_code": {
                        "type": "string",
                        "description": "The unique code of the group to delete (e.g., '1155501-A')."
                    }
                },
                "required": ["group_code"]
            },
        },
    },
    "change_group": {
        "function": change_group,
        "tool": {
            "name": "change_group",
            "description": "Change a group in the schedule draft to another group. Returns the updated schedule.",
            "parameters": {
                "type": "object",
                "properties": {
                    "old_group_code": {
                        "type": "string",
                        "description": "The code of the current group to replace (e.g., '1155501-A')."
                    },
                    "new_group_code": {
                        "type": "string",
                        "description": "The code of the new group to assign (e.g., '1155501-B')."
                    }
                },
                "required": ["old_group_code", "new_group_code"]
            },
        },
    },
}


class Chat:
    def __init__(self, chat_history):
        settings = get_settings()
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY no configurada")
        model_name = settings.model_name
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.last_response = ""

        gemini_history = []
        for msg in chat_history:
            gemini_history.append(
                types.Content(
                    role=msg["role"], parts=[types.Part.from_text(text=msg["content"])]
                )
            )

        self.chat = self.client.chats.create(
            model=model_name,
            config=types.GenerateContentConfig(
                system_instruction=get_prompt(),
                tools=[
                    types.Tool(
                        function_declarations=[TOOLS[tool]["tool"] for tool in TOOLS]
                    )
                ],
            ),
            history=gemini_history,
        )

    def get_last_response(self) -> str:
        """Obtener la última respuesta"""
        return self.last_response

    def send_message(self, msg: str, context: Dict[str, Any] | None = None):
        response = self.chat.send_message(msg)
        iteration = 0

        while iteration < max_iterations:
            print(f"Iteration {iteration + 1}: {response.candidates}")
            
            # Buscar todas las function calls en todos los parts
            function_calls = []
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_calls.append(part.function_call)

            # Si no hay function calls, terminar el bucle
            if not function_calls:
                break

            # Procesar todos los function calls encontrados
            all_results = []
            
            for function_call in function_calls:
                function_name = function_call.name
                print(f"Function to call: {function_name}")
                
                if function_name in TOOLS:
                    try:
                        fc_args = getattr(function_call, "args", {}) or {}
                        function_result = TOOLS[function_name]["function"](context or {}, **fc_args)
                        
                        all_results.append(
                            types.Part.from_function_response(
                                name=function_name, 
                                response={"content": function_result}
                            )
                        )
                    except Exception as e:
                        print(f"Error en {function_name}: {e}")
                        all_results.append(
                            types.Part.from_function_response(
                                name=function_name, 
                                response={"error": str(e)}
                            )
                        )

            # Enviar todos los resultados de vuelta al modelo para la siguiente iteración
            if all_results:
                response = self.chat.send_message(all_results)
                iteration += 1
            else:
                break

        if iteration >= max_iterations:
            print(f"Warning: Reached max iterations ({max_iterations})")

        self.last_response = response.text if response.text else ""
        return self.last_response

    def send_message_stream(self, msg: str, context: Dict) -> Generator[Dict[str, Any], None, None]:
        """Envía mensaje con streaming de eventos"""
        yield {"type": "message_start", "message": "Enviando mensaje..."}

        response = self.chat.send_message(msg)
        max_iterations = 5  # Prevenir bucles infinitos
        iteration = 0
        total_functions_executed = 0

        while iteration < max_iterations:
            # Buscar todas las function calls en todos los parts
            function_calls = []
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_calls.append(part.function_call)

            # Si no hay function calls, terminar el bucle
            if not function_calls:
                break

            # Procesar todos los function calls encontrados
            all_results = []
            
            for i, function_call in enumerate(function_calls):
                function_name = function_call.name
                total_functions_executed += 1
                
                yield {
                    "type": "function_call",
                    "function_name": function_name,
                    "message": f"Ronda {iteration + 1} - Ejecutando función {i+1}/{len(function_calls)}: {function_name}",
                }

                if function_name in TOOLS:
                    yield {
                        "type": "function_executing",
                        "message": f"Cargando {function_name}...",
                    }

                    try:
                        fc_args = getattr(function_call, "args", {}) or {}
                        print(f"Iteration {iteration + 1}: Executing {function_name}{fc_args}")
                        function_result = TOOLS[function_name]["function"](context, **fc_args)
                        
                        all_results.append(
                            types.Part.from_function_response(
                                name=function_name, 
                                response={"content": function_result}
                            )
                        )

                        yield {
                            "type": "function_completed",
                            "function_name": function_name,
                            "message": f"Función {function_name} completada",
                        }

                    except Exception as e:
                        yield {
                            "type": "error",
                            "message": f"Error en {function_name}: {str(e)}"
                        }
                        all_results.append(
                            types.Part.from_function_response(
                                name=function_name, 
                                response={"error": str(e)}
                            )
                        )

            # Enviar todos los resultados de vuelta al modelo para la siguiente iteración
            if all_results:
                yield {
                    "type": "generating_response",
                    "message": f"Procesando resultados de ronda {iteration + 1}...",
                }

                try:
                    response = self.chat.send_message(all_results)
                    iteration += 1
                except Exception as e:
                    yield {
                        "type": "error",
                        "message": f"Error generando respuesta: {str(e)}"
                    }
                    self.last_response = "Error procesando respuesta"
                    return
            else:
                break

        if iteration >= max_iterations:
            yield {
                "type": "error", 
                "message": f"Alcanzado límite máximo de {max_iterations} rondas de funciones"
            }

        self.last_response = response.text if response.text else ""

        yield {
            "type": "response",
            "content": self.last_response,
            "message": "Respuesta generada",
        }