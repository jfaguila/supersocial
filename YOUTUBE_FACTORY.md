# YouTube Channel Factory — Architecture Document

## 1. System Overview

The YouTube Channel Factory is a modular extension of SuperSocial that enables
automated production and publishing of YouTube videos at scale. It is designed
to produce **30-100 videos/month** across multiple channels, each with its own
persistent AI character, voice, visual identity, and niche.

```
                    +---------------------------+
                    |    YOUTUBE FACTORY         |
                    |    ORCHESTRATOR            |
                    +---------------------------+
                              |
       +----------------------+------------------------+
       |              |              |                  |
  +---------+  +-----------+  +-----------+  +------------------+
  | Channel |  | Character |  |  Script   |  |   SEO Optimizer  |
  | Manager |  |  Manager  |  | Generator |  |                  |
  +---------+  +-----------+  +-----------+  +------------------+
       |              |              |                  |
       |         +---------+   +---------+        +---------+
       |         |  Image  |   |  Voice  |        |Thumbnail|
       |         |  Gen    |   |  Gen    |        |  Gen    |
       |         +---------+   +---------+        +---------+
       |              |              |                  |
       |         +---------+        |                  |
       |         | Img2Vid |        |                  |
       |         +---------+        |                  |
       |              |              |                  |
       |         +---------+--------+------------------+
       |         |   YOUTUBE VIDEO ASSEMBLER            |
       |         |   (FFmpeg 16:9 montage + sync)       |
       |         +--------------------------------------+
       |                        |
       |              +------------------+
       +----------->  | YouTube API      |
                      | Connector        |
                      | (upload + meta)  |
                      +------------------+
```

## 2. Stack Tecnologico

| Component                | Technology                     | Reason                                      |
|--------------------------|--------------------------------|---------------------------------------------|
| Script generation        | OpenAI GPT-4o (existing)       | Best quality for structured narrative        |
| Voice generation         | ElevenLabs (existing)          | Professional voices, per-character voice ID  |
| Image generation         | OpenAI DALL-E 3 / Flux 1.1    | High quality scene images with prompt control|
| Image-to-video           | Runway Gen-3 Alpha Turbo       | Best img2vid quality, 16:9 support           |
| Character consistency    | LoRA prompt anchoring + DALL-E | Persistent visual identity per character     |
| Video assembly           | FFmpeg                         | Proven, fast, zero cost                      |
| Thumbnail generation     | DALL-E 3 + Pillow overlay      | Eye-catching thumbnails with text overlay    |
| YouTube upload           | YouTube Data API v3            | Official API with full metadata control      |
| Orchestration            | Python async (existing)        | Consistent with SuperSocial architecture     |
| Database                 | PostgreSQL (existing)          | Channel, character, video tracking           |
| Task queue               | Redis + APScheduler (existing) | Scheduled batch production                   |

## 3. Production Pipeline (Step by Step)

### Phase 1: Script Generation
```
Input:  channel_config (niche, tone, character) + topic
Output: structured_script {hook, problem, deepening, solution, cta}
```
- LLM generates a 5-scene structured script
- Each scene has: narration text, timing, visual description
- Total target duration: 3-8 minutes (configurable per channel)
- Script is validated for structure and timing

### Phase 2: Voice Generation
```
Input:  structured_script.narration_text + character.voice_id
Output: voiceover.wav (WAV 44.1kHz)
```
- ElevenLabs TTS with character-specific voice
- Duration control via speaking_rate parameter
- Output as WAV for maximum quality in montage

### Phase 3: Scene Image Generation
```
Input:  scene.visual_prompt + character.visual_identity
Output: scene_XX.png (1920x1080 per scene)
```
- DALL-E 3 generates one 1920x1080 image per scene
- Character identity is injected into prompts via LoRA-style descriptors
- Visual consistency maintained through:
  1. Fixed character description block (face, hair, clothing, style)
  2. Fixed art style suffix (cinematic, 4K, specific color palette)
  3. Seed-based generation when API supports it

### Phase 4: Image-to-Video Conversion
```
Input:  scene_XX.png + motion_prompt
Output: scene_XX.mp4 (5-10s per clip, 16:9)
```
- Runway Gen-3 Alpha Turbo in image-to-video mode
- Motion prompt derived from scene context (e.g., "slow zoom in", "camera pan right")
- 16:9 aspect ratio (1344:768 Runway parameter)
- Duration: 5s or 10s per scene based on narration length

### Phase 5: Video Assembly
```
Input:  scene clips + voiceover.wav + subtitles.srt
Output: final_video.mp4 (1920x1080, H.264, optimized for YouTube)
```
- FFmpeg concatenates clips in scene order
- Voice-over mixed as primary audio track
- Subtitles burned into video (YouTube-optimized font size 28)
- Cross-dissolve transitions between scenes (0.5s)
- Export: H.264, CRF 20, AAC 192kbps, -movflags +faststart
- Total duration matches voice-over

### Phase 6: Thumbnail Generation
```
Input:  video_title + character.visual_identity + niche_context
Output: thumbnail.jpg (1280x720, JPEG, <2MB)
```
- DALL-E 3 generates base image
- Pillow overlays: bold title text, channel branding
- High contrast, large faces, 3 words maximum

### Phase 7: SEO & Metadata
```
Input:  script + niche + channel_config
Output: {title, description, tags, hashtags, category}
```
- LLM generates SEO-optimized title (max 70 chars)
- Description: 5000 chars with timestamps, links, keywords
- Tags: 15-30 relevant tags
- Category mapping to YouTube category IDs
- AI content disclosure flag

### Phase 8: YouTube Upload
```
Input:  final_video.mp4 + thumbnail.jpg + metadata
Output: youtube_video_id
```
- YouTube Data API v3 resumable upload
- Set: title, description, tags, category, thumbnail
- Privacy: unlisted initially, then public on schedule
- Made for Kids: false (configurable)
- AI disclosure: self_declared_made_with_ai = true

## 4. Character Consistency System

### Problem
AI image generators produce different faces/people each time.
YouTube channels need a recognizable, consistent character.

### Solution: Prompt Anchoring + Visual Identity Blocks

Each character has a `visual_identity` block stored in DB:
```json
{
  "character_id": "george_ai",
  "name": "George",
  "physical": "30-year-old male, short dark hair, light stubble, sharp jawline, warm brown eyes",
  "clothing": "dark fitted t-shirt, minimalist silver watch",
  "style": "photorealistic, cinematic lighting, shallow depth of field, 4K",
  "color_palette": "deep blues, warm oranges, dark backgrounds",
  "environment": "modern minimalist office, large window with city view",
  "negative_prompt": "cartoon, anime, deformed, blurry, low quality, multiple people"
}
```

This block is prepended to EVERY image generation prompt:
```
"Portrait of [physical], wearing [clothing], in [environment], [style]. Scene: [scene_description]"
```

### Consistency guarantees
1. **Same prompt structure** every time (deterministic template)
2. **Negative prompt** blocks unwanted variations
3. **Style suffix** locks the visual aesthetic
4. **Periodic audit**: every 10 videos, George compares thumbnails for drift

### Future enhancement (Phase 2)
- Train a custom LoRA on the best-generated images
- Use ComfyUI + SDXL locally for pixel-perfect consistency
- Cost: $0 after initial GPU setup (~$50/month for cloud GPU)

## 5. Multi-Channel Architecture

```
youtube_channels
├── Channel: "AI Business Hub"
│   ├── Character: George (male, tech)
│   ├── Niche: artificial_intelligence
│   ├── Voice: ElevenLabs "Adam"
│   ├── Schedule: MWF 14:00 UTC
│   └── Target: 12 videos/month
│
├── Channel: "Freedom Finance"
│   ├── Character: Sofia (female, finance)
│   ├── Niche: financial_freedom
│   ├── Voice: ElevenLabs "Rachel"
│   ├── Schedule: TTh 16:00 UTC
│   └── Target: 8 videos/month
│
└── Channel: "Rebel Entrepreneur"
    ├── Character: Marcus (male, motivational)
    ├── Niche: anti_system, entrepreneurship
    ├── Voice: ElevenLabs "Antoni"
    ├── Schedule: Daily 10:00 UTC
    └── Target: 30 videos/month
```

Each channel operates independently with its own:
- YouTube API credentials (separate Google Cloud project)
- Character identity (visual + voice)
- Content niche and tone
- Publishing schedule
- Performance metrics

## 6. Cost Estimation (Monthly, 50 videos)

| Service             | Unit Cost              | 50 Videos        | Monthly Total |
|---------------------|------------------------|------------------|---------------|
| OpenAI GPT-4o       | ~$0.03/1K tokens       | ~200K tokens     | **$6**        |
| ElevenLabs          | Starter plan           | 30K chars/mo     | **$5**        |
| DALL-E 3            | $0.04/image (1024x1792)| 250 images + 50 thumbs | **$12** |
| Runway Gen-3 Turbo  | $0.05/second           | 250 clips x 7s avg | **$88**     |
| YouTube API         | Free (quota based)     | 50 uploads       | **$0**        |
| PostgreSQL + Redis  | Docker (self-hosted)   | —                | **$0**        |
| VPS (4 vCPU, 8GB)   | Hetzner/OVH            | —                | **$15**       |
| **TOTAL**           |                        |                  | **~$126/mo**  |

### Cost per video: ~$2.52

### Low-Cost Alternative (30 videos/month)

| Replacement                          | Savings      |
|--------------------------------------|-------------|
| Flux 1.1 Pro (Replicate) vs DALL-E 3 | -$4/mo      |
| Kling 1.6 vs Runway Gen-3            | -$40/mo     |
| ElevenLabs free tier (10K chars)      | -$5/mo      |
| GPT-4o-mini vs GPT-4o                | -$4/mo      |
| **Low-cost total**                    | **~$73/mo** |

## 7. Real Bottlenecks

### 1. Character Consistency (CRITICAL)
- Current AI image models cannot guarantee identical faces
- Mitigation: strict prompt anchoring + visual identity blocks
- Long-term: custom LoRA training on generated character images

### 2. Runway Generation Time
- Each clip takes 30-120 seconds to generate
- 5 scenes x 50 videos = 250 clips = 2-8 hours of API wait time
- Mitigation: parallel generation (3 concurrent), batch scheduling overnight

### 3. YouTube API Quotas
- Default quota: 10,000 units/day
- Video upload: 1,600 units each
- Maximum: ~6 uploads per day per project
- Mitigation: multiple Google Cloud projects, upload scheduling

### 4. ElevenLabs Character Limits
- Starter plan: 30,000 chars/month
- Average 5-min script: ~750 words = ~4,000 chars
- Maximum: ~7 videos/month on Starter
- Mitigation: Scale plan ($22/mo) for 100K chars (~25 videos)

### 5. Content Quality at Scale
- LLM-generated scripts can become repetitive
- Mitigation: topic database, deduplication, trend injection, variety scoring

## 8. Technical Level Required

| Skill                        | Level      | Why                                        |
|------------------------------|------------|--------------------------------------------|
| Python (async)               | Advanced   | Core orchestration language                |
| Docker                       | Intermediate | Deployment and service management        |
| PostgreSQL                   | Intermediate | Data persistence and queries             |
| FFmpeg                       | Intermediate | Video assembly and encoding              |
| REST APIs                    | Intermediate | YouTube, ElevenLabs, OpenAI, Runway      |
| YouTube Data API v3          | Intermediate | OAuth2 + resumable uploads               |
| Prompt Engineering           | Advanced   | Character consistency + script quality    |
| Google Cloud Console         | Basic      | API credentials and quota management      |

## 9. Strategic Recommendation

### Phase 1: MVP (Weeks 1-2)
- Single channel, single character
- 2 videos/week to validate pipeline
- Manual topic selection, automated everything else
- Validate character consistency manually

### Phase 2: Scale (Weeks 3-6)
- Enable auto-topic selection via trend analysis
- Add 2nd channel with different niche
- Increase to 3 videos/week per channel
- Implement performance feedback loop

### Phase 3: Full Automation (Weeks 7-12)
- 3+ channels running autonomously
- Topic selection driven by trend + performance data
- A/B testing thumbnails
- Auto-schedule based on audience analytics
- Target: 30-50 videos/month total

### Key Success Metric
- **Cost per 1,000 views** — if < $0.50, the system is profitable with ads alone
- **Watch time** > 40% average = algorithm boost
- **Subscriber growth rate** > 5%/week = channel viability confirmed

### Revenue Model
At 50 videos/month generating 500K total views:
- YouTube AdSense: $500-1,500/month (CPM $1-3)
- Affiliate links in descriptions: $200-800/month
- Digital product funnels: $500-2,000/month
- **Projected revenue: $1,200-4,300/month**
- **Cost: ~$126/month**
- **ROI: 850-3,300%**
