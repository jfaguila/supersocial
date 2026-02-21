#!/usr/bin/env python3
"""
YouTube OAuth2 Setup — Obtiene el refresh_token necesario para la fábrica.

NO abre ningún navegador. Flujo 100% manual:
    1. Ejecuta: python youtube/oauth_setup.py
    2. Copia la URL que aparece
    3. Pégala en TU navegador (el que tú elijas)
    4. Autoriza con tu cuenta de YouTube
    5. Google te redirige a localhost con un código en la URL
    6. Copia ese código y pégalo aquí
    7. El script imprime tu refresh_token

Requisitos:
    pip install httpx   (ya instalado en el proyecto)
"""
import sys
import urllib.parse

import httpx

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"  # Flujo manual sin servidor local


def get_refresh_token(client_id: str, client_secret: str) -> str | None:
    """
    Flujo OAuth2 manual — sin abrir navegador.
    Genera URL, el usuario autoriza, pega el código, y obtenemos el refresh_token.
    """
    # Paso 1: Construir la URL de autorización
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{AUTH_URI}?{urllib.parse.urlencode(params)}"

    print()
    print("─" * 60)
    print("  PASO 1: Copia esta URL y ábrela en tu navegador")
    print("─" * 60)
    print()
    print(f"  {auth_url}")
    print()
    print("─" * 60)
    print("  PASO 2: Autoriza con tu cuenta de YouTube")
    print("  PASO 3: Google te mostrará un código de autorización")
    print("  PASO 4: Copia ese código y pégalo aquí abajo")
    print("─" * 60)
    print()

    auth_code = input("  Código de autorización: ").strip()
    if not auth_code:
        print("ERROR: No se proporcionó código.")
        return None

    # Paso 2: Intercambiar código por tokens
    print()
    print("  Intercambiando código por tokens...")

    resp = httpx.post(
        TOKEN_URI,
        data={
            "code": auth_code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=30.0,
    )

    if resp.status_code != 200:
        print(f"ERROR: Google respondió {resp.status_code}")
        print(f"  {resp.text}")
        return None

    data = resp.json()
    refresh_token = data.get("refresh_token")
    access_token = data.get("access_token")

    if not refresh_token:
        print("ERROR: No se recibió refresh_token.")
        print("  Asegúrate de que seleccionaste 'consent' y la app tiene acceso offline.")
        print(f"  Respuesta: {data}")
        return None

    # Paso 3: Verificar que funciona haciendo una llamada de prueba
    print("  Verificando acceso a YouTube...")
    verify_resp = httpx.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "snippet", "mine": "true"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15.0,
    )

    if verify_resp.status_code == 200:
        channels = verify_resp.json().get("items", [])
        if channels:
            ch_name = channels[0]["snippet"]["title"]
            ch_id = channels[0]["id"]
            print(f"  Canal detectado: {ch_name} (ID: {ch_id})")
        else:
            print("  Acceso OK pero no se encontraron canales asociados.")
    else:
        print(f"  Verificación falló ({verify_resp.status_code}) — pero el token puede funcionar igualmente.")

    return refresh_token


def main():
    print("=" * 60)
    print("  YouTube OAuth2 Setup — Obtener refresh_token")
    print("  (No abre ningún navegador)")
    print("=" * 60)
    print()
    print("  Necesitas Client ID y Client Secret de tu proyecto")
    print("  en Google Cloud Console.")
    print()

    client_id = input("  Client ID: ").strip()
    client_secret = input("  Client Secret: ").strip()

    if not client_id or not client_secret:
        print("ERROR: Necesitas ambos valores.")
        print("Consíguelos en: https://console.cloud.google.com → APIs → Credentials")
        sys.exit(1)

    refresh_token = get_refresh_token(client_id, client_secret)

    if refresh_token:
        print()
        print("=" * 60)
        print("  REFRESH TOKEN OBTENIDO")
        print("=" * 60)
        print()
        print(f"  {refresh_token}")
        print()
        print("  Guárdalo en un lugar seguro.")
        print()
        print("  Próximo paso:")
        print("    python youtube/cli.py setup-channel")
        print("=" * 60)
    else:
        print()
        print("ERROR: No se pudo obtener el refresh_token.")


if __name__ == "__main__":
    main()
