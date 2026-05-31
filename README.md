# Boeing Proxy

Microservicio para consultar specs de partes en shop.boeing.com.

## Endpoint

GET /boeing?pn={PART_NUMBER}&token={SECRET_TOKEN}

Respuesta JSON:
{
  "found": true,
  "part_number": "AA48110-2",
  "description": "OIL FILTER",
  "weight_lbs": 1.33,
  "length_in": 4.95,
  "width_in": 3.65,
  "height_in": 3.8,
  "packaged_weight_lbs": 1.46,
  "packaged_length_in": 5.65,
  "packaged_width_in": 4.0,
  "packaged_height_in": 4.05
}

## Variables de entorno (configurar en Render dashboard)

- BOEING_COOKIES: string de cookies copiado de tu browser en shop.boeing.com
- SECRET_TOKEN: token secreto para proteger el endpoint (ej: una cadena aleatoria)

## Deploy en Render

1. Subir este repo a GitHub (repo privado)
2. Conectar en render.com → New Web Service
3. Configurar BOEING_COOKIES y SECRET_TOKEN en Environment
4. Deploy
