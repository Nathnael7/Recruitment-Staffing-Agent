import json
import re
import google.generativeai as genai
from config.settings import GEMINI_MODEL
import logging
import os

# Setup logging
log_dir = ".logs"
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, "agents.log")
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

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

    logging.info("Starting resume matching process")
    job = state.get("job", {})
    model = genai.GenerativeModel(GEMINI_MODEL)
    desc = f"Title: {job.get('title', '')}\nResponsibilities: {job.get('responsibilities', '')}"
    matches = []

    for idx, r in enumerate(state.get("parsed_resumes", [])):
        logging.info(f"Processing resume {idx+1}/{len(state.get('parsed_resumes', []))} (name: {r.get('name', 'N/A')})")
        try:
            # Only process if Gemini says it's a resume
            if not is_resume(r.get('text', ''), model):
                logging.info(f"Skipped non-resume document (name: {r.get('name', 'N/A')})")
                continue

            prompt = f"""You are an AI resume screener with a deterministic policy.

JOB DESCRIPTION
{desc}

RESUME TEXT
{r.get('text', '')}

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
            raw = model.generate_content(prompt).text.strip()
            data = extract_first_json(raw)
            email = extract_email(r.get('text', ''))  # Extract email from resume text

            matches.append({
                "name": r.get("name", ""),
                "score": data.get("score", 0),
                "status": data.get("status", ""),
                "email": email
            })
            logging.info(f"Resume processed (name: {r.get('name', 'N/A')}, score: {data.get('score', 0)}, status: {data.get('status', '')})")
        except Exception as e:
            logging.error(f"Error processing resume (name: {r.get('name', 'N/A')}): {e}", exc_info=True)
            matches.append({
                "name": r.get("name", ""),
                "score": 0,
                "status": f"Error: {type(e).__name__}"
            })
    logging.info("Resume matching process completed")
    return {"matches": matches}