# Guía de APIs de Plataformas — SuperSocial

Esta guía explica exactamente qué necesitas configurar para cada plataforma,
dónde conseguirlo, cuánto cuesta, y qué puede hacer George con cada API.

---

## Resumen rápido

| Plataforma | Gratuito | Publicar | Leer tendencias | Dificultad |
|------------|----------|----------|-----------------|------------|
| X (Twitter) | ✅ Básico | ✅ | ✅ | Media |
| TikTok | ✅ | ✅ (solicitar acceso) | ✅ (Research API) | Alta |
| LinkedIn | ✅ | ✅ | ⚠️ Limitado | Media |
| Instagram | ✅ | ✅ | ✅ (hashtags) | Media-Alta |

---

## 1. X (Twitter) API

### Qué necesitas
```
TWITTER_BEARER_TOKEN        ← para leer/buscar tweets
TWITTER_API_KEY             ← para publicar
TWITTER_API_SECRET          ← para publicar
TWITTER_ACCESS_TOKEN        ← para publicar
TWITTER_ACCESS_SECRET       ← para publicar
```

### Cómo obtenerlo

1. Ve a https://developer.twitter.com/en/portal/dashboard
2. Crea una nueva App
3. En la sección **Keys and Tokens**:
   - Copia el **Bearer Token** → `TWITTER_BEARER_TOKEN`
   - Copia **API Key** y **API Key Secret** → `TWITTER_API_KEY` / `TWITTER_API_SECRET`
4. En **Access Token and Secret** (haz clic en "Generate"):
   - Copia ambos → `TWITTER_ACCESS_TOKEN` / `TWITTER_ACCESS_SECRET`

### Nivel de acceso necesario
- **Free tier**: Solo leer. Publicar 1 tweet/día. **No suficiente.**
- **Basic ($100/mes)**: Hasta 100 tweets/mes. **Suficiente para empezar.**
- **Pro ($5,000/mes)**: Sin límites. Para escala.

### ⚠️ Truco importante
Con el **Free tier** puedes probar George. Para producción necesitas **Basic** mínimo.

---

## 2. TikTok API

### Qué necesitas
```
TIKTOK_CLIENT_KEY           ← identificador de tu app
TIKTOK_CLIENT_SECRET        ← secreto de tu app
TIKTOK_ACCESS_TOKEN         ← token de acceso del usuario
```

### Cómo obtenerlo

1. Ve a https://developers.tiktok.com/
2. Crea una app en **TikTok for Developers**
3. Solicita acceso a **dos APIs por separado**:

   **A) Content Posting API** (para publicar videos):
   - En tu app → "Manage products" → Solicitar "Content Posting API"
   - Necesitas cuenta TikTok Business o Creator
   - Aprobación puede tardar 1-2 semanas

   **B) Research API** (para buscar tendencias):
   - Solicitar por separado en https://developers.tiktok.com/products/research-api/
   - Requiere verificación de organización
   - **Alternativa**: Si no tienes acceso, George puede operar sin TikTok Research y solo publicar

4. Para el Access Token:
   - Implementa el flujo OAuth 2.0 de TikTok
   - O usa el **Postman collection** que TikTok provee para obtenerlo manualmente

### ⚠️ Realidad de TikTok
TikTok es la más difícil de las 4. Si no tienes acceso a Research API,
George puede **publicar** en TikTok pero no **analizar tendencias**.
Configura las otras 3 plataformas primero.

---

## 3. LinkedIn API

### Qué necesitas
```
LINKEDIN_CLIENT_ID          ← ID de tu app LinkedIn
LINKEDIN_CLIENT_SECRET      ← secreto de tu app
LINKEDIN_ACCESS_TOKEN       ← token OAuth del usuario
LINKEDIN_PERSON_URN         ← tu identificador LinkedIn (ej: urn:li:person:ABC123)
```

### Cómo obtenerlo

1. Ve a https://www.linkedin.com/developers/apps
2. Crea una nueva app
3. En **Products**, solicita:
   - **"Share on LinkedIn"** — para publicar posts (aprobación automática)
   - **"Sign In with LinkedIn using OpenID Connect"** — para autenticación
4. En **Auth**, copia `Client ID` y `Client Secret`

5. Para el **Access Token** (OAuth 2.0):
   ```
   URL: https://www.linkedin.com/oauth/v2/authorization
   Scopes necesarios: w_member_social, r_basicprofile
   ```
   - Puedes usar https://www.linkedin.com/developers/tools/oauth/token-generator
   - O implementar el flujo OAuth en tu app

6. Para tu **Person URN**:
   ```bash
   curl -H "Authorization: Bearer TU_ACCESS_TOKEN" \
        https://api.linkedin.com/v2/userinfo
   # El campo "sub" es tu Person URN
   ```

### ⚠️ Token expira cada 60 días
LinkedIn access tokens duran **60 días**. Necesitarás renovarlos o implementar
refresh automático. George te avisará cuando el token esté próximo a expirar.

---

## 4. Instagram Graph API

### Qué necesitas
```
INSTAGRAM_ACCESS_TOKEN             ← token de acceso
INSTAGRAM_BUSINESS_ACCOUNT_ID     ← ID de tu cuenta Business/Creator
INSTAGRAM_APP_ID                   ← ID de tu app Facebook
INSTAGRAM_APP_SECRET               ← secreto de tu app Facebook
```

### Requisito previo importante
**Necesitas una cuenta Instagram Business o Creator** conectada a una
página de Facebook. Las cuentas personales NO tienen acceso a la API.

### Cómo obtenerlo

1. Ve a https://developers.facebook.com/ y crea una App (tipo "Business")

2. Añade el producto **"Instagram Graph API"** a tu app

3. En **Graph API Explorer** (https://developers.facebook.com/tools/explorer/):
   - Selecciona tu app
   - Solicita estos permisos: `instagram_basic`, `instagram_content_publish`,
     `instagram_manage_insights`, `pages_read_engagement`
   - Genera el token

4. Para obtener tu **Business Account ID**:
   ```bash
   curl "https://graph.facebook.com/v19.0/me/accounts?access_token=TU_TOKEN"
   # Copia el page_id de tu página Facebook

   curl "https://graph.facebook.com/v19.0/TU_PAGE_ID?fields=instagram_business_account&access_token=TU_TOKEN"
   # El campo instagram_business_account.id es tu INSTAGRAM_BUSINESS_ACCOUNT_ID
   ```

5. Convierte a **Long-Lived Token** (dura 60 días, renovable):
   ```bash
   curl "https://graph.facebook.com/v19.0/oauth/access_token
     ?grant_type=fb_exchange_token
     &client_id=TU_APP_ID
     &client_secret=TU_APP_SECRET
     &fb_exchange_token=TU_SHORT_TOKEN"
   ```

### ⚠️ Límites de publicación
Instagram Graph API tiene estos límites:
- Máximo **50 posts/día** por cuenta
- Máximo **25 stories/día**
- Videos: deben estar en URL pública accesible

---

## 5. OpenAI (para generación de contenido)

### Qué necesitas
```
OPENAI_API_KEY    ← sk-...
OPENAI_MODEL      ← gpt-4o (recomendado) o gpt-4o-mini (más barato)
```

### Cómo obtenerlo
1. https://platform.openai.com/api-keys
2. Crea una API key
3. **Carga créditos** — George genera ~50-100 posts/semana

### Coste estimado
| Ciclo | Posts generados | Coste estimado |
|-------|----------------|----------------|
| Semanal (4 plataformas) | ~80 posts | $0.50 - $2.00 |
| Mensual | ~320 posts | $2.00 - $8.00 |

Con `gpt-4o-mini` el coste baja a $0.20-$0.50/semana.

---

## Verificar tu configuración

Después de configurar el `.env`, ejecuta:

```bash
# Con Docker:
curl http://localhost:8000/george/api-health

# Sin Docker:
python -c "from tools_server.api_checker import ApiChecker; import asyncio; print(ApiChecker().check_all())"
```

Obtendrás algo como:
```json
{
  "overall_ready": true,
  "platforms": [
    {
      "platform": "twitter",
      "configured": true,
      "can_read": true,
      "can_publish": true,
      "missing_keys": []
    },
    {
      "platform": "tiktok",
      "configured": false,
      "missing_keys": ["TIKTOK_CLIENT_KEY", "TIKTOK_ACCESS_TOKEN"],
      "notes": "Requiere solicitar acceso a TikTok Research API"
    }
  ],
  "warnings": ["⚠️ TIKTOK: faltan credenciales"]
}
```

---

## Orden recomendado de configuración

```
1. OpenAI         ← imprescindible, 5 minutos
2. Twitter/X      ← más fácil, 10 minutos
3. Instagram      ← requiere cuenta Business, 20 minutos
4. LinkedIn       ← acceso automático, 15 minutos
5. TikTok         ← más complejo, puede tardar semanas (solicitarlo ya)
```

George funciona con **cualquier combinación** de plataformas.
No necesitas las 4 configuradas para arrancar.
