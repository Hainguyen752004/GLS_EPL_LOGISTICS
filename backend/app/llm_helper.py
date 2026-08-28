import json
import urllib.request
import urllib.error
from config import GEMINI_API_KEY

def call_gemini_llm(prompt: str, system_instruction: str = "") -> str:
    """
    Gọi API Google Gemini (Bản gemini-2.0-flash / gemini-2.5-flash) bằng GEMINI_API_KEY_GT
    """
    if not GEMINI_API_KEY:
        print("[Gemini LLM Error]: Missing GEMINI_API_KEY_GT")
        return ""

    # Thử danh sách các model Gemini theo thứ tự ưu tiên
    model_candidates = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro"
    ]

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1024
        }
    }
    
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    for model in model_candidates:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                candidates = res_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        reply = parts[0].get("text", "").strip()
                        if reply:
                            print(f"[Gemini LLM Success]: Model {model} response generated successfully!")
                            return reply
        except urllib.error.HTTPError as http_err:
            print(f"[Gemini Model {model} HTTP Error]: {http_err.code} - {http_err.reason}")
        except Exception as e:
            print(f"[Gemini Model {model} Error]: {e}")

    return ""
