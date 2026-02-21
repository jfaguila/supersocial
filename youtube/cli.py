#!/usr/bin/env python3
"""
YouTube Factory CLI — Herramienta de línea de comandos para la fábrica.

Comandos:
    setup-channel   → Configura un nuevo canal de YouTube
    setup-character  → Crea un personaje IA para el canal
    produce          → Produce un vídeo (sin subir a YouTube)
    produce-upload   → Produce y sube a YouTube
    list-channels    → Lista canales configurados
    list-videos      → Lista vídeos producidos
    test-pipeline    → Test rápido del pipeline (solo guion + SEO)

Uso:
    python youtube/cli.py setup-character
    python youtube/cli.py setup-channel
    python youtube/cli.py produce --topic "How AI replaces jobs" --channel-id <id>
    python youtube/cli.py test-pipeline --topic "Test topic"
"""
import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime

# Asegurar que el directorio raíz está en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def cmd_setup_character(args):
    """Crea un personaje IA interactivamente."""
    print("\n" + "=" * 60)
    print("  Crear Personaje IA para YouTube")
    print("=" * 60)

    name = input("\nNombre del personaje: ").strip() or "George"
    physical = input(
        "Descripción física (ej: '30-year-old male, short dark hair, stubble'): "
    ).strip() or "30-year-old male, short dark hair, light stubble, sharp jawline, warm brown eyes"
    clothing = input(
        "Ropa (ej: 'dark fitted t-shirt, silver watch'): "
    ).strip() or "dark fitted t-shirt, minimalist silver watch"
    art_style = input(
        "Estilo artístico [photorealistic, cinematic lighting, 4K]: "
    ).strip() or "photorealistic, cinematic lighting, shallow depth of field, 4K"
    color_palette = input(
        "Paleta de colores [deep blues, warm oranges, dark backgrounds]: "
    ).strip() or "deep blues, warm oranges, dark backgrounds"
    environment = input(
        "Entorno por defecto [modern minimalist office]: "
    ).strip() or "modern minimalist office, large window with city view"
    voice_id = input(
        "ElevenLabs Voice ID (dejar vacío para 'Adam'): "
    ).strip() or "pNInz6obpgDQGcFmaJgB"

    character_id = str(uuid.uuid4())
    character_data = {
        "id": character_id,
        "name": name,
        "physical_description": physical,
        "clothing_description": clothing,
        "art_style": art_style,
        "color_palette": color_palette,
        "default_environment": environment,
        "negative_prompt": "cartoon, anime, deformed, blurry, low quality, multiple people, text, watermark",
        "elevenlabs_voice_id": voice_id,
        "voice_stability": 0.5,
        "voice_similarity_boost": 0.75,
        "voice_style": 0.4,
        "voice_speaking_rate": 1.0,
    }

    # Guardar como JSON para referencia
    output_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"character_{name.lower()}.json")
    with open(output_path, "w") as f:
        json.dump(character_data, f, indent=2)

    print(f"\n✓ Personaje '{name}' creado")
    print(f"  ID: {character_id}")
    print(f"  Archivo: {output_path}")
    print(f"\n  Cuando la DB esté activa, inserta con:")
    print(f"    python youtube/cli.py db-insert-character {output_path}")
    return character_data


def cmd_setup_channel(args):
    """Configura un canal de YouTube interactivamente."""
    print("\n" + "=" * 60)
    print("  Configurar Canal de YouTube")
    print("=" * 60)

    name = input("\nNombre del canal: ").strip() or "AI Business Hub"
    youtube_channel_id = input("YouTube Channel ID (de la URL): ").strip()
    niche = input("Nicho (ej: artificial_intelligence, entrepreneurship): ").strip() or "artificial_intelligence"
    language = input("Idioma [en]: ").strip() or "en"
    tone = input("Tono [professional, authoritative]: ").strip() or "professional, authoritative"
    duration = input("Duración objetivo en minutos [5]: ").strip()
    target_duration = int(duration) if duration else 5
    videos_per_week = input("Vídeos por semana [3]: ").strip()
    vpw = int(videos_per_week) if videos_per_week else 3

    print("\n--- Credenciales Google OAuth2 ---")
    client_id = input("Client ID: ").strip()
    client_secret = input("Client Secret: ").strip()
    refresh_token = input("Refresh Token: ").strip()

    character_id = input("\nCharacter ID (del paso anterior): ").strip()

    channel_id = str(uuid.uuid4())
    channel_data = {
        "id": channel_id,
        "name": name,
        "youtube_channel_id": youtube_channel_id,
        "niche": niche,
        "language": language,
        "tone": tone,
        "target_duration_minutes": target_duration,
        "videos_per_week": vpw,
        "google_client_id": client_id,
        "google_client_secret": client_secret,
        "google_refresh_token": refresh_token,
        "publish_schedule_cron": "0 14 * * 1,3,5",
        "privacy_status": "unlisted",
        "default_category_id": "28",
        "made_for_kids": False,
        "character_id": character_id,
    }

    output_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"channel_{name.lower().replace(' ', '_')}.json")
    with open(output_path, "w") as f:
        json.dump(channel_data, f, indent=2)

    print(f"\n✓ Canal '{name}' configurado")
    print(f"  ID: {channel_id}")
    print(f"  Archivo: {output_path}")
    return channel_data


def cmd_test_pipeline(args):
    """Test rápido: genera guion + SEO sin imágenes ni vídeo."""
    topic = args.topic or "How AI is changing the way we work in 2025"
    niche = args.niche or "artificial_intelligence"

    print(f"\n{'=' * 60}")
    print(f"  Test Pipeline — Solo guion + SEO")
    print(f"  Tema: {topic}")
    print(f"{'=' * 60}\n")

    async def run():
        os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
        os.environ.setdefault("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))

        if not os.environ.get("OPENAI_API_KEY"):
            print("ERROR: Necesitas OPENAI_API_KEY en variables de entorno")
            return

        from content.llm_client import LLMClient
        from youtube.script_generator import YouTubeScriptGenerator
        from youtube.seo_optimizer import SEOOptimizer

        llm = LLMClient()
        script_gen = YouTubeScriptGenerator(llm)
        seo_gen = SEOOptimizer(llm)

        # Generar guion
        print("→ Generando guion...")
        script = await script_gen.generate(
            topic=topic,
            niche=niche,
            target_duration_minutes=5,
            language=args.language or "en",
        )

        print(f"\n{'─' * 40}")
        print(f"  GUION: {script.title_suggestion}")
        print(f"  Palabras: {script.word_count} | Duración: {script.total_duration_seconds:.0f}s")
        print(f"{'─' * 40}")
        for scene in script.scenes:
            print(f"\n  [{scene.scene_type.upper()}] ({scene.duration_seconds:.0f}s)")
            print(f"  Narración: {scene.narration[:150]}...")
            print(f"  Visual: {scene.visual_description[:100]}...")

        # Generar SEO
        print(f"\n→ Generando SEO...")
        seo = await seo_gen.optimize(
            topic=topic,
            script_summary=script.full_narration,
            niche=niche,
            language=args.language or "en",
        )

        print(f"\n{'─' * 40}")
        print(f"  TÍTULO: {seo.title}")
        print(f"  HASHTAGS: {' '.join(seo.hashtags)}")
        print(f"  TAGS: {', '.join(seo.tags[:10])}...")
        print(f"  CATEGORÍA: {seo.category_id}")
        print(f"{'─' * 40}")
        print(f"\n  DESCRIPCIÓN:")
        print(f"  {seo.description[:500]}...")

        # Guardar resultado
        output_dir = os.path.join(os.path.dirname(__file__), "data", "test_outputs")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"test_{int(datetime.now().timestamp())}.json")
        with open(output_path, "w") as f:
            json.dump({
                "script": script.to_dict(),
                "seo": {
                    "title": seo.title,
                    "description": seo.description,
                    "tags": seo.tags,
                    "hashtags": seo.hashtags,
                    "category_id": seo.category_id,
                },
            }, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Test completo. Resultado guardado en: {output_path}")

    asyncio.run(run())


def cmd_produce(args):
    """Produce un vídeo completo (sin subir a YouTube)."""
    topic = args.topic
    if not topic:
        print("ERROR: --topic es obligatorio")
        return

    channel_file = args.channel_config
    character_file = args.character_config

    if not channel_file or not character_file:
        print("ERROR: Necesitas --channel-config y --character-config")
        print("  Crea los archivos con: python youtube/cli.py setup-character / setup-channel")
        return

    print(f"\n{'=' * 60}")
    print(f"  Producción de Vídeo")
    print(f"  Tema: {topic}")
    print(f"  Upload: {'SÍ' if args.upload else 'NO (dry run)'}")
    print(f"{'=' * 60}\n")

    async def run():
        os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")

        with open(channel_file) as f:
            channel_data = json.load(f)
        with open(character_file) as f:
            character_data = json.load(f)

        from youtube.channel_manager import ChannelConfig
        from youtube.character_manager import CharacterManager, CharacterIdentity
        from youtube.factory_pipeline import FactoryPipeline

        # Construir ChannelConfig desde JSON
        channel_config = ChannelConfig(
            channel_id=channel_data["id"],
            name=channel_data["name"],
            niche=channel_data["niche"],
            language=channel_data["language"],
            tone=channel_data["tone"],
            target_duration_minutes=channel_data["target_duration_minutes"],
            videos_per_week=channel_data["videos_per_week"],
            publish_schedule_cron=channel_data.get("publish_schedule_cron", "0 14 * * 1,3,5"),
            default_category_id=channel_data.get("default_category_id", "28"),
            made_for_kids=channel_data.get("made_for_kids", False),
            privacy_status=channel_data.get("privacy_status", "unlisted"),
            google_client_id=channel_data.get("google_client_id", ""),
            google_client_secret=channel_data.get("google_client_secret", ""),
            google_refresh_token=channel_data.get("google_refresh_token", ""),
            character_id=channel_data.get("character_id", ""),
        )

        # Construir CharacterIdentity desde JSON
        identity = CharacterIdentity(
            character_id=character_data["id"],
            name=character_data["name"],
            physical=character_data["physical_description"],
            clothing=character_data["clothing_description"],
            art_style=character_data["art_style"],
            color_palette=character_data["color_palette"],
            environment=character_data["default_environment"],
            negative_prompt=character_data["negative_prompt"],
            voice_id=character_data["elevenlabs_voice_id"],
            voice_stability=character_data.get("voice_stability", 0.5),
            voice_similarity_boost=character_data.get("voice_similarity_boost", 0.75),
            voice_style=character_data.get("voice_style", 0.4),
            voice_speaking_rate=character_data.get("voice_speaking_rate", 1.0),
        )

        output_dir = args.output_dir or os.path.join(
            os.path.dirname(__file__), "data", "productions"
        )

        pipeline = FactoryPipeline()
        result = await pipeline.produce(
            topic=topic,
            channel_config=channel_config,
            character_identity=identity,
            output_dir=output_dir,
            upload=args.upload,
        )

        if result.success:
            print(f"\n{'=' * 60}")
            print(f"  ✓ VÍDEO PRODUCIDO")
            print(f"{'=' * 60}")
            print(f"  Título: {result.title}")
            print(f"  Duración: {result.duration_seconds:.0f}s")
            print(f"  Escenas: {result.scenes_count}")
            print(f"  Vídeo: {result.video_file_path}")
            print(f"  Thumbnail: {result.thumbnail_file_path}")
            print(f"  Pipeline: {result.pipeline_duration_seconds:.0f}s")
            if result.youtube_url:
                print(f"  YouTube: {result.youtube_url}")
            print(f"{'=' * 60}")
        else:
            print(f"\n✗ Error: {result.error}")

    asyncio.run(run())


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Factory CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")

    # setup-character
    subparsers.add_parser("setup-character", help="Crear un personaje IA")

    # setup-channel
    subparsers.add_parser("setup-channel", help="Configurar un canal de YouTube")

    # test-pipeline
    test_parser = subparsers.add_parser("test-pipeline", help="Test rápido (guion + SEO)")
    test_parser.add_argument("--topic", type=str, help="Tema del vídeo")
    test_parser.add_argument("--niche", type=str, default="artificial_intelligence")
    test_parser.add_argument("--language", type=str, default="en")

    # produce
    produce_parser = subparsers.add_parser("produce", help="Producir un vídeo")
    produce_parser.add_argument("--topic", type=str, required=True, help="Tema del vídeo")
    produce_parser.add_argument("--channel-config", type=str, help="Ruta al JSON del canal")
    produce_parser.add_argument("--character-config", type=str, help="Ruta al JSON del personaje")
    produce_parser.add_argument("--output-dir", type=str, help="Directorio de salida")
    produce_parser.add_argument("--upload", action="store_true", help="Subir a YouTube")

    args = parser.parse_args()

    if args.command == "setup-character":
        cmd_setup_character(args)
    elif args.command == "setup-channel":
        cmd_setup_channel(args)
    elif args.command == "test-pipeline":
        cmd_test_pipeline(args)
    elif args.command == "produce":
        cmd_produce(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
