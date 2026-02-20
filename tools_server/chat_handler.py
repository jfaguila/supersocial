"""
Asistente IA de configuración — lee y escribe el .env conversacionalmente.

El usuario puede decirle las API keys en lenguaje natural y el asistente
las guarda directamente en el fichero .env sin pasos manuales.
"""
import os
import re
from pathlib import Path
from typing import Optional

# ── .env path (inside Docker /app, or local fallback) ──────────────────────
_CANDIDATES = [Path("/app/.env"), Path(".env"), Path(__file__).parent.parent / ".env"]
ENV_FILE = next((p for p in _CANDIDATES if p.exists()), Path("/app/.env"))

# ── API key catalogue ───────────────────────────────────────────────────────
API_KEY_INFO: dict = {
    # LLM
    "OPENAI_API_KEY":         {"desc": "OpenAI — genera todo el contenido con GPT-4o",             "where": "https://platform.openai.com/api-keys",              "required": True,  "group": "LLM"},
    "ANTHROPIC_API_KEY":      {"desc": "Anthropic Claude — backup del LLM si OpenAI falla",         "where": "https://console.anthropic.com/",                    "required": False, "group": "LLM"},
    # Video
    "RUNWAYML_API_KEY":       {"desc": "Runway Gen-3 — genera clips de vídeo con IA",               "where": "https://app.runwayml.com/ → Settings → API Keys",   "required": False, "group": "Video"},
    "ELEVENLABS_API_KEY":     {"desc": "ElevenLabs — voz en off automática para los vídeos",        "where": "https://elevenlabs.io/ → Profile → API Key",        "required": False, "group": "Video"},
    "ELEVENLABS_VOICE_ID":    {"desc": "ID de voz de ElevenLabs (vacío = voz Adam por defecto)",    "where": "https://elevenlabs.io/voice-library",               "required": False, "group": "Video"},
    # Twitter / X
    "TWITTER_BEARER_TOKEN":   {"desc": "Twitter Bearer Token (lectura de tendencias)",              "where": "https://developer.twitter.com/en/portal",           "required": False, "group": "Twitter/X"},
    "TWITTER_API_KEY":        {"desc": "Twitter API Key (Consumer Key)",                            "where": "https://developer.twitter.com/en/portal",           "required": False, "group": "Twitter/X"},
    "TWITTER_API_SECRET":     {"desc": "Twitter API Secret (Consumer Secret)",                     "where": "https://developer.twitter.com/en/portal",           "required": False, "group": "Twitter/X"},
    "TWITTER_ACCESS_TOKEN":   {"desc": "Twitter Access Token",                                     "where": "https://developer.twitter.com/en/portal",           "required": False, "group": "Twitter/X"},
    "TWITTER_ACCESS_SECRET":  {"desc": "Twitter Access Token Secret",                              "where": "https://developer.twitter.com/en/portal",           "required": False, "group": "Twitter/X"},
    # TikTok
    "TIKTOK_CLIENT_KEY":      {"desc": "TikTok Client Key",                                        "where": "https://developers.tiktok.com/",                    "required": False, "group": "TikTok"},
    "TIKTOK_CLIENT_SECRET":   {"desc": "TikTok Client Secret",                                     "where": "https://developers.tiktok.com/",                    "required": False, "group": "TikTok"},
    "TIKTOK_ACCESS_TOKEN":    {"desc": "TikTok Access Token",                                      "where": "https://developers.tiktok.com/",                    "required": False, "group": "TikTok"},
    # LinkedIn
    "LINKEDIN_CLIENT_ID":     {"desc": "LinkedIn App — Client ID",                                 "where": "https://www.linkedin.com/developers/apps",          "required": False, "group": "LinkedIn"},
    "LINKEDIN_CLIENT_SECRET": {"desc": "LinkedIn App — Client Secret",                             "where": "https://www.linkedin.com/developers/apps",          "required": False, "group": "LinkedIn"},
    "LINKEDIN_ACCESS_TOKEN":  {"desc": "LinkedIn OAuth Access Token",                              "where": "https://www.linkedin.com/developers/apps",          "required": False, "group": "LinkedIn"},
    "LINKEDIN_PERSON_URN":    {"desc": "Tu URN de persona LinkedIn (ej: urn:li:person:XXXXX)",      "where": "https://api.linkedin.com/v2/me",                    "required": False, "group": "LinkedIn"},
    # Instagram / Meta
    "INSTAGRAM_ACCESS_TOKEN":           {"desc": "Instagram Graph API — Access Token",              "where": "https://developers.facebook.com/ → Herramientas",   "required": False, "group": "Instagram"},
    "INSTAGRAM_BUSINESS_ACCOUNT_ID":    {"desc": "ID de tu cuenta de negocio de Instagram",        "where": "https://developers.facebook.com/ → Herramientas",   "required": False, "group": "Instagram"},
    "INSTAGRAM_APP_ID":                 {"desc": "Meta App ID",                                     "where": "https://developers.facebook.com/",                  "required": False, "group": "Instagram"},
    "INSTAGRAM_APP_SECRET":             {"desc": "Meta App Secret",                                 "where": "https://developers.facebook.com/",                  "required": False, "group": "Instagram"},
    # Config
    "GEORGE_CYCLE_MODE":      {"desc": "'semi' (tú apruebas cada post) o 'full' (publica solo)",    "where": "no necesita clave, escribe el valor directamente",   "required": False, "group": "Configuración"},
    "CONTENT_NICHES":         {"desc": "Nichos separados por comas (ej: entrepreneurship,ai)",      "where": "no necesita clave, escribe el valor directamente",   "required": False, "group": "Configuración"},
    "CONTENT_LANGUAGES":      {"desc": "'es' para español, 'en' para inglés",                       "where": "no necesita clave, escribe el valor directamente",   "required": False, "group": "Configuración"},
}

_SYSTEM_PROMPT = """\
Eres el asistente de configuración de SuperSocial.
Tu misión: ayudar al usuario a configurar las APIs necesarias de forma conversacional.

REGLAS IMPORTANTES:
- Cuando el usuario te dé una API key o valor de configuración, GUÁRDALA INMEDIATAMENTE usando set_env_key. No pidas confirmación.
- Habla siempre en español, de forma amigable y directa.
- Nunca muestres el valor completo de una key en tu respuesta, solo confirma que se guardó.
- Al inicio de cada conversación usa get_env_status() para saber qué falta.

ORDEN DE CONFIGURACIÓN RECOMENDADO:
1. OPENAI_API_KEY — obligatoria, sin ella nada funciona
2. Al menos UNA red social (Twitter, TikTok, LinkedIn o Instagram)
3. Video opcional: Runway + ElevenLabs
4. Ajustes: GEORGE_CYCLE_MODE, CONTENT_NICHES, CONTENT_LANGUAGES

Cuando el usuario termine, dile que ejecute en su terminal:
  docker compose restart tool-server george
para que los cambios tengan efecto.
"""

# ── Tools for Anthropic function calling ────────────────────────────────────
_TOOLS = [
    {
        "name": "get_env_status",
        "description": (
            "Muestra qué claves API están configuradas en el .env y cuáles faltan. "
            "Los valores se muestran enmascarados (****). Úsalo al inicio para saber el estado."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "set_env_key",
        "description": (
            "Guarda o actualiza una variable en el fichero .env. "
            "Llámala SIEMPRE que el usuario proporcione una API key o valor de configuración."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key":   {"type": "string", "description": "Nombre de la variable (ej: OPENAI_API_KEY)"},
                "value": {"type": "string", "description": "Valor a guardar"},
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "get_key_info",
        "description": "Devuelve descripción y URL donde obtener una clave API específica.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Nombre de la variable (ej: TWITTER_API_KEY)"},
            },
            "required": ["key"],
        },
    },
]


# ── Internal helpers ─────────────────────────────────────────────────────────

def _read_env() -> dict[str, str]:
    """Lee el .env y devuelve un dict {KEY: value}."""
    env: dict[str, str] = {}
    if not ENV_FILE.exists():
        return env
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _write_env_key(key: str, value: str) -> None:
    """Escribe o actualiza una clave en el .env, preservando el resto del fichero."""
    content = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""

    # Quote values with spaces, hashes or quotes
    if any(c in value for c in (" ", "#", '"', "'")):
        value_str = f'"{value}"'
    else:
        value_str = value

    new_line = f"{key}={value_str}"
    pattern = re.compile(rf"^{re.escape(key)}\s*=.*$", re.MULTILINE)

    if pattern.search(content):
        content = pattern.sub(new_line, content)
    else:
        if content and not content.endswith("\n"):
            content += "\n"
        content += new_line + "\n"

    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    ENV_FILE.write_text(content, encoding="utf-8")


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "••••"
    return value[:4] + "••••" + value[-4:]


def _handle_tool(name: str, inp: dict) -> str:
    if name == "get_env_status":
        env = _read_env()
        lines: list[str] = []
        groups: dict[str, list[str]] = {}
        for key, info in API_KEY_INFO.items():
            g = info["group"]
            groups.setdefault(g, [])
            val = env.get(key, "")
            status = f"✓ {_mask(val)}" if val else "✗ no configurada"
            req = " *" if info["required"] else ""
            groups[g].append(f"  {key}{req}: {status}")
        for g, items in groups.items():
            lines.append(f"[{g}]")
            lines.extend(items)
        return "\n".join(lines)

    if name == "set_env_key":
        key = inp.get("key", "").upper().strip()
        value = inp.get("value", "").strip()
        if not key or not value:
            return "Error: clave o valor vacío."
        _write_env_key(key, value)
        return f"✓ {key} guardada correctamente en .env."

    if name == "get_key_info":
        key = inp.get("key", "").upper().strip()
        info = API_KEY_INFO.get(key)
        if not info:
            return f"No tengo información específica sobre {key}."
        return (
            f"{key}\n"
            f"Descripción: {info['desc']}\n"
            f"Dónde obtenerla: {info['where']}\n"
            f"Obligatoria: {'Sí' if info['required'] else 'No'}"
        )

    return "Herramienta desconocida."


# ── Main chat function ───────────────────────────────────────────────────────

def chat_with_assistant(messages: list[dict], api_key: str) -> str:
    """
    Procesa la conversación con el asistente de configuración.

    Args:
        messages: lista de {role: 'user'|'assistant', content: str}
        api_key:  clave Anthropic a usar (puede venir del .env o del cliente)

    Returns:
        Texto de respuesta del asistente.
    """
    import anthropic  # lazy import — the key might not be set at module load

    client = anthropic.Anthropic(api_key=api_key)

    # Convert plain text messages to Anthropic format (content can be list or str)
    def _to_anthropic(msgs: list[dict]) -> list[dict]:
        result = []
        for m in msgs:
            content = m["content"]
            # Already in Anthropic format (list of blocks)
            if isinstance(content, list):
                result.append({"role": m["role"], "content": content})
            else:
                result.append({"role": m["role"], "content": str(content)})
        return result

    anthropic_msgs = _to_anthropic(messages)

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        tools=_TOOLS,
        messages=anthropic_msgs,
    )

    # Agentic loop: handle tool calls
    while response.stop_reason == "tool_use":
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result_text = _handle_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })

        anthropic_msgs = anthropic_msgs + [
            {"role": "assistant", "content": response.content},
            {"role": "user",      "content": tool_results},
        ]

        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            tools=_TOOLS,
            messages=anthropic_msgs,
        )

    text_parts = [b.text for b in response.content if hasattr(b, "text") and b.text]
    return "\n".join(text_parts)


def resolve_api_key(provided: Optional[str] = None) -> Optional[str]:
    """Resuelve qué clave Anthropic usar: la del cliente, o la del entorno."""
    if provided and provided.strip():
        return provided.strip()
    env = _read_env()
    from_env = env.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
    return from_env if from_env else None
