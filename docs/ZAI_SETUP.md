# Z.AI Setup & Troubleshooting Guide

## Configuration
**File:** `.env`
```properties
ZAI_API_BASE=https://api.z.ai/api/paas/v4/
ZAI_MODEL=glm-4.7-flash
ZAI_API_KEY=d6813aa0...
```

**File:** `config.json`
```json
{
    "model": "glm-4.7-flash",
    ...
}
```

## Troubleshooting

### 1. `404 Not Found`
- **Cause:** Incorrect API URL.
- **Fix:** Ensure `.env` has `ZAI_API_BASE=https://api.z.ai/api/paas/v4/`.

### 2. `Error 1211: Unknown Model`
- **Cause:** Using `glm-4` instead of `glm-4.7-flash`.
- **Fix:** Update `.env` and `config.json` to `glm-4.7-flash`.

### 3. `Error 1113: Insufficient Balance`
- **Cause:** Account out of credits for paid models (`glm-4`, `glm-4.7`).
- **Fix:** Use the free model `glm-4.7-flash`.

### 4. Empty Response / Silence
- **Cause:** Model safety filter or complexity overload.
- **Fix:** `watcher.py` now splits prompts into System/User messages to handle this. If frequent, try reducing `max_tokens` or contexts.

### 5. `ðŸ”´` Garbage Characters
- **Cause:** PowerShell encoding.
- **Fix:** `scripts/start-local.ps1` forces UTF-8 encoding.

## Testing
Run `python scripts/test_zai.py` to verify connection in isolation.
Run `.\scripts\start-local.ps1` to start the watcher.
