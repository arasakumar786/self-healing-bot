import os, json, anthropic
from dotenv import load_dotenv

load_dotenv()
client_ai = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def ask_llm(context, reason):
    prompt = f"""
You are a Kubernetes SRE assistant. A pod failed with reason: {reason}.

Context:
{json.dumps(context, indent=2)}

Respond ONLY with valid JSON in this exact format, no markdown, no preamble:
{{
  "root_cause": "short explanation",
  "confidence": "high|medium|low",
  "risk_level": "safe|needs_review",
  "action_type": "restart|patch_memory|patch_image|rollback|manual",
  "kubectl_command": "the exact kubectl command to fix it, or null",
  "explanation": "why this fix addresses the root cause"
}}
"""
    response = client_ai.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)