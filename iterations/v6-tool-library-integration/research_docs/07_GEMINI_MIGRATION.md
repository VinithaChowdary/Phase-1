# G. GEMINI 3 PRO PREVIEW MIGRATION (TECHNICAL)

## 1. Dependency Updates
*   Add `google-genai` to `requirements.txt`.
*   Add `google-auth` for Service Account handling.

## 2. Authentication
*   Use `GOOGLE_APPLICATION_CREDENTIALS` environment variable pointing to the JSON key file.
*   Initialize client:
    ```python
    from google import genai
    import os
    
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY")) # Or vertexai
    # For Vertex AI / Service Account:
    # import vertexai
    # vertexai.init(project=..., location=...)
    ```
    *Note: The official `google-genai` SDK simplifies this.*

## 3. Code Replacement Strategy

### Old (OpenAI/DeepSeek)
```python
from openai import AsyncOpenAI
client = AsyncOpenAI(base_url="...", api_key="...")
response = await client.chat.completions.create(
    model="deepseek-chat",
    messages=[...]
)
```

### New (Gemini 3 Pro)
```python
from pydantic_ai.models.gemini import GeminiModel
# Or using the raw SDK if needed, but PydanticAI is preferred for this agent
model = GeminiModel('gemini-exp-1206', api_key=...)
```

If raw access is needed:
```python
from google.genai import types
response = await client.models.generate_content(
    model='gemini-exp-1206',
    contents=[...],
    config=types.GenerateContentConfig(temperature=0)
)
```

## 4. Token Usage Tracking
Gemini API returns usage metadata in the response object.
```python
usage = response.usage_metadata
print(f"Prompt: {usage.prompt_token_count}, Candidates: {usage.candidates_token_count}")
```
This must be mapped to the standard logging format.

## 5. Rate Limiting
Gemini 3 Pro Preview has quotas.
*   Implement `tenacity` retry decorator with exponential backoff.
*   Handle `429 Resource Exhausted`.
