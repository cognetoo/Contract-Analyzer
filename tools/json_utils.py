import json, re
from typing import Any

def safe_json_load(raw: str) -> Any:
    if raw is None:
        raise ValueError("Empty response")

    raw = raw.strip()

    # remove code fences
    raw = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()

    # try direct parse first
    try:
        return json.loads(raw)
    except:
        pass

    # extract first JSON object or array from the text
    m = re.search(r"(\{[\s\S]*\}|[\s\S]*)", raw)
    if not m:
        raise ValueError("No JSON found in response")

    return json.loads(m.group(1))