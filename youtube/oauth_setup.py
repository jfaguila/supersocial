#!/usr/bin/env python3
"""
YouTube OAuth2 Setup — Obtiene el refresh_token necesario para la fábrica.

Uso:
    1. Ejecuta: python youtube/oauth_setup.py
    2. Se abrirá tu navegador para autorizar la app
    3. Autoriza con tu cuenta de YouTube
    4. El script imprimirá tu refresh_token
    5. Guárdalo — lo necesitas para configurar el canal en la base de datos

Requisitos:
    pip install google-auth-oauthlib
"""
import json
import os
import sys

# Credenciales del proyecto Google Cloud
DEFAULT_CLIENT_ID = ""
DEFAULT_CLIENT_SECRET = ""

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def get_refresh_token(client_id: str, client_secret: str) -> str:
    """
    Ejecuta el flujo OAuth2 y devuelve el refresh_token.
    Funciona de dos formas:
      - Si tienes navegador: abre automáticamente
      - Si no: te da una URL para copiar/pegar
    """
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("ERROR: Instala google-auth-oauthlib:")
        print("  pip install google-auth-oauthlib")
        sys.exit(1)

    # Construir configuración OAuth2 desde las credenciales
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

    try:
        # Intenta abrir navegador local
        credentials = flow.run_local_server(
            port=8090,
            prompt="consent",
            access_type="offline",
        )
    except Exception:
        # Fallback: flujo manual por consola
        print("\nNo se pudo abrir el navegador. Usa el flujo manual:")
        credentials = flow.run_console(access_type="offline")

    return credentials.refresh_token


def main():
    print("=" * 60)
    print("  YouTube OAuth2 Setup — Obtener refresh_token")
    print("=" * 60)
    print()

    client_id = input(f"Client ID [{DEFAULT_CLIENT_ID[:20]}...]: ").strip()
    if not client_id:
        client_id = DEFAULT_CLIENT_ID

    client_secret = input(f"Client Secret [{DEFAULT_CLIENT_SECRET[:10]}...]: ").strip()
    if not client_secret:
        client_secret = DEFAULT_CLIENT_SECRET

    if not client_id or not client_secret:
        print("ERROR: Necesitas Client ID y Client Secret.")
        print("Consíguelos en: https://console.cloud.google.com → APIs → Credentials")
        sys.exit(1)

    print()
    print("Abriendo navegador para autorización...")
    print("(Si no se abre, copia la URL que aparece abajo)")
    print()

    refresh_token = get_refresh_token(client_id, client_secret)

    if refresh_token:
        print()
        print("=" * 60)
        print("  ✓ REFRESH TOKEN OBTENIDO")
        print("=" * 60)
        print()
        print(f"  {refresh_token}")
        print()
        print("  Guárdalo en un lugar seguro.")
        print("  Lo necesitas para configurar tu canal en la base de datos.")
        print()
        print("  Próximo paso: ejecuta el setup del canal:")
        print("    python youtube/cli.py setup-channel")
        print("=" * 60)
    else:
        print("ERROR: No se pudo obtener el refresh_token.")
        print("Asegúrate de autorizar la app con tu cuenta de YouTube.")


if __name__ == "__main__":
    main()
