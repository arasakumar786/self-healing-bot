import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

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

    try:
        response = client.chat.completions.create(
            model=os.getenv("MODEL", "anthropic/claude-sonnet-4"),
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0,
            max_tokens=500
        )

        raw = response.choices[0].message.content.strip()

        # Remove markdown if model returns it
        raw = raw.replace("```json", "").replace("```", "").strip()

        return json.loads(raw)

    except Exception as e:
        print(f"LLM Error: {e}")

        return {
            "root_cause": "Unable to determine root cause",
            "confidence": "low",
            "risk_level": "needs_review",
            "action_type": "manual",
            "kubectl_command": None,
            "explanation": str(e)
        }