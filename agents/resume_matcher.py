import json
import re
import google.generativeai as genai
from config.settings import GEMINI_MODEL

import json
import re
import google.generativeai as genai
from config.settings import GEMINI_MODEL

def match_resumes(state):
    def extract_email(text):
        # Simple regex for email extraction
        match = re.search(r'[\w\.-]+@[\w\.-]+', text)
        return match.group(0) if match else ""

    def extract_first_json(text):
        cleaned = re.sub(r"^```(?:json)?\s*|```$", "", text.strip(), flags=re.MULTILINE).strip()
        match = re.search(r"\{.*?\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError("No JSON object found in response")

    def is_resume(text, model):
        prompt = (
            "You are an AI assistant. Determine if the following text is a resume/CV. "
            "Reply only with 'YES' or 'NO'.\n\n"
            f"TEXT:\n{text}\n"
        )
        response = model.generate_content(prompt).text.strip().upper()
        return response.startswith("YES")

    job = state["job"]
    model = genai.GenerativeModel(GEMINI_MODEL)
    desc = f"Title: {job['title']}\nResponsibilities: {job['responsibilities']}"
    matches = []

    for r in state["parsed_resumes"]:
        # Only process if Gemini says it's a resume
        if not is_resume(r['text'], model):
            continue

        prompt = f"""You are an AI resume screener with a deterministic policy.

JOB DESCRIPTION
{desc}

RESUME TEXT
{r['text']}

SCORING GUIDELINES (0–100):
- +20 title keywords
- +30 matched responsibilities
- +20 matching skills/tools
- +10 culture-fit language
- −10 vague or unrelated
- −10 missing essentials

EVALUATION RULES
1. Strict and fair.
2. Deterministic.
3. Return only JSON: {{ "score": <int>, "status": <str> }}

Status rules:
- Shortlisted if score ≥ 70
- Review Manually if 50–69
- Not Suitable if < 50
"""
        try:
            raw = model.generate_content(prompt).text.strip()
            data = extract_first_json(raw)
            email = extract_email(r['text'])  # Extract email from resume text

            matches.append({"name": r["name"], "score": data["score"], "status": data["status"], "email": email})
        except Exception as e:
            matches.append({"name": r["name"], "score": 0, "status": f"Error: {e}"})
    return {"matches": matches}