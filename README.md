# SuperSocial — Autonomous Multi-Platform Content Engine

**George** is an autonomous AI agent that runs your entire social media content operation.
One optional weekly prompt. Everything else is automated.

---

## Platforms Supported

| Platform  | Trend Fetch | Publish | Metrics |
|-----------|-------------|---------|---------|
| X (Twitter) | ✅ | ✅ | ✅ |
| TikTok    | ✅ | ✅ | ✅ |
| LinkedIn  | ✅ | ✅ | ✅ |
| Instagram | ✅ | ✅ | ✅ |

---

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Fill in your API keys in .env

# 2. Launch
docker-compose up -d

# 3. (Optional) Provide a weekly strategic prompt
echo "Focus on the anti-9-5 angle this week" > /data/weekly_prompt.txt

# 4. Trigger a cycle manually
docker exec supersocial_george python -m scheduler.weekly_cycle
```

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full technical spec, including:
- System architecture diagram
- Database schema
- George's state machine
- API integration structure
- Deployment instructions
- Security practices
- Phase-based rollout plan

---

## Cycle Overview

**Weekly (Sunday 00:00 UTC)**
1. Pull previous 7-day performance metrics
2. Run feedback loop → update strategy weights
3. Fetch trends from all platforms
4. Analyze: engagement, hooks, emotions, formats
5. Select narrative + emotion + authority per platform
6. Generate content batch via LLM
7. Dedup + validate + format
8. Run video pipeline (script, SRT, HeyGen/Runway JSON)
9. Schedule to optimal time slots
10. Publish (full-auto) or pause for review (semi-auto)

**Daily (06:00 UTC)**
- Publish due scheduled posts
- Pull 24h metrics on yesterday's posts

---

## Configuration

| Key | Description |
|-----|-------------|
| `GEORGE_CYCLE_MODE` | `full` = publish autonomously, `semi` = pause before publish |
| `MAX_POSTS_PER_PLATFORM_PER_DAY` | Default: 3 |
| `CONTENT_NICHES` | Comma-separated: entrepreneurship,financial_freedom,network_marketing,anti_system |

---

## Phase Rollout

| Phase | Mode | Description |
|-------|------|-------------|
| 1 | Semi-autonomous | George generates, human approves before publish |
| 2 | Full automation | George publishes, human receives weekly digest |
| 3 | Self-optimizing | George A/B tests, adapts persona, recalibrates fully |

---

## License

Proprietary — SuperSocial Internal Use Only.
