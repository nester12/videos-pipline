import json
import re
import time
import requests

APPROVED_FREE_MODELS = {
    'gemini-3.6-flash',
    'gemini-3.1-flash-lite',
    'gemini-2.5-flash',
    'gemini-2.5-flash-lite',
}


def extract_json_text(data: dict) -> dict:
    parts = (((data.get('candidates') or [{}])[0].get('content') or {}).get('parts') or [])
    text = ''.join(str(p.get('text') or '') for p in parts).strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.I)
    text = re.sub(r'\s*```$', '', text)
    return json.loads(text)


class GeminiClient:
    def __init__(self, api_key: str, model: str = 'gemini-2.5-flash'):
        if model not in APPROVED_FREE_MODELS:
            raise RuntimeError(f'Model {model} is not approved for zero-cost mode')
        self.api_key = api_key
        self.model = model

    def generate_json(self, prompt: str, *, use_google_search: bool = False, timeout: int = 60) -> dict:
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent'
        payload = {
            'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
            'generationConfig': {
                'responseMimeType': 'application/json',
                'temperature': 0.7,
                'maxOutputTokens': 2200,
            },
        }
        if use_google_search:
            payload['tools'] = [{'google_search': {}}]
        last = None
        for attempt in range(3):
            try:
                r = requests.post(url, params={'key': self.api_key}, json=payload, timeout=timeout)
                if r.status_code == 200:
                    return extract_json_text(r.json())
                last = RuntimeError(f'Gemini HTTP {r.status_code}: {r.text[:300]}')
                if r.status_code not in {429, 500, 502, 503, 504}:
                    break
            except requests.RequestException as exc:
                last = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
        raise RuntimeError(f'Gemini free-tier request failed; no paid fallback will be used: {last}')
