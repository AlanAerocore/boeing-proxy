import os
import re
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

app = FastAPI(title="Boeing Proxy", docs_url=None, redoc_url=None)

# Cookies y token secreto desde variables de entorno
BOEING_COOKIES_STR = os.environ.get("BOEING_COOKIES", "")
SECRET_TOKEN = os.environ.get("SECRET_TOKEN", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "accept-language": "es-ES,es;q=0.9,en;q=0.8",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "Referer": "https://shop.boeing.com/",
}

def parse_cookies(cookie_str: str) -> dict:
    cookies = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies

def extract_specs(html: str) -> dict:
    """Extrae peso y dimensiones del HTML de Boeing."""
    html2 = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html2 = re.sub(r'<style[^>]*>.*?</style>', '', html2, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', html2)
    text = re.sub(r'&[a-z#0-9]+;', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    result = {
        "found": False,
        "part_number": None,
        "description": None,
        "weight_lbs": None,
        "length_in": None,
        "width_in": None,
        "height_in": None,
        "packaged_weight_lbs": None,
        "packaged_length_in": None,
        "packaged_width_in": None,
        "packaged_height_in": None,
        "raw_text": text[:500]
    }

    # Detectar si encontró el part
    if "unable to reach" in text.lower() or "unexpected" in text.lower():
        return result
    if len(text) < 200:
        return result

    result["found"] = True

    # Part number y descripción
    m = re.search(r'([A-Z0-9\-]+)\s+\|\s+([^\|]+)\s+\|', text)
    if m:
        result["part_number"] = m.group(1).strip()
        result["description"] = m.group(2).strip()

    # Weight: "Weight: 1.33 lbs" o "Weight: 1.33 Pounds"
    m = re.search(r'Weight[:\s]+([0-9.]+)\s*(?:lbs?|pounds?)', text, re.IGNORECASE)
    if m:
        result["weight_lbs"] = float(m.group(1))

    # Dimensions: "Dimensions : 4.95 (L) x 3.65 (W) x 3.8 (H) in"
    m = re.search(r'Dimensions?\s*:?\s*([0-9.]+)\s*\(?L\)?\s*[xX×]\s*([0-9.]+)\s*\(?W\)?\s*[xX×]\s*([0-9.]+)\s*\(?H\)?', text, re.IGNORECASE)
    if m:
        result["length_in"] = float(m.group(1))
        result["width_in"] = float(m.group(2))
        result["height_in"] = float(m.group(3))

    # Packaged Weight
    m = re.search(r'Packaged\s+Weight[:\s]+([0-9.]+)\s*(?:lbs?|pounds?)', text, re.IGNORECASE)
    if m:
        result["packaged_weight_lbs"] = float(m.group(1))

    # Packaged Dimensions
    m = re.search(r'Packaged\s+Dimensions?\s*:?\s*([0-9.]+)\s*\(?L\)?\s*[xX×]\s*([0-9.]+)\s*\(?W\)?\s*[xX×]\s*([0-9.]+)\s*\(?H\)?', text, re.IGNORECASE)
    if m:
        result["packaged_length_in"] = float(m.group(1))
        result["packaged_width_in"] = float(m.group(2))
        result["packaged_height_in"] = float(m.group(3))

    return result


@app.get("/boeing")
async def get_boeing_part(
    pn: str = Query(..., description="Part number"),
    token: str = Query(..., description="Secret token")
):
    # Validar token
    if SECRET_TOKEN and token != SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")

    cookies = parse_cookies(BOEING_COOKIES_STR)
    if not cookies:
        raise HTTPException(status_code=500, detail="Boeing cookies not configured")

    # Buscar en Boeing — primero por URL directa de producto via búsqueda
    url = f"https://shop.boeing.com/aviation-supply/searchresults?text={pn}"

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            resp = await client.get(url, headers=HEADERS, cookies=cookies)

        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Boeing returned HTTP {resp.status_code}"
            )

        specs = extract_specs(resp.text)
        specs["source_url"] = url
        specs["http_status"] = resp.status_code
        return JSONResponse(content=specs)

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Boeing request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok", "cookies_configured": bool(BOEING_COOKIES_STR)}
