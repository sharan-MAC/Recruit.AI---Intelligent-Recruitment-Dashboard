import os
import json
try:
    import google.generativeai as genai
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("Google Generative AI package not found.")

from dotenv import load_dotenv

load_dotenv()

model = None
if AI_AVAILABLE:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-3-flash-preview')

async def extract_candidate_data(resume_text: str):
    if not model:
        return None
    prompt = f"""
    Extract structured data from this resume. Return ONLY JSON.
    Format:
    {{
      "name": "string",
      "email": "string",
      "phone": "string",
      "technical_skills": [{{ "name": "string", "proficiency": "string" }}],
      "soft_skills": [{{ "name": "string", "proficiency": "string" }}],
      "education": "string",
      "experience_years": float,
      "previous_companies": ["string"],
      "certifications": ["string"],
      "projects": ["string"]
    }}
    Resume: {resume_text}
    """
    try:
        response = await model.generate_content_async(prompt)
        if not response or not response.text:
            return None
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
        return json.loads(text)
    except Exception as e:
        print(f"AI Extraction Error: {e}")
        return None

async def rank_candidate_for_job(candidate_data: dict, job_description: str):
    if not model:
        return {"score": 0, "analysis": "AI service unavailable"}
    prompt = f"""
    Rank this candidate for the job. Return ONLY JSON.
    Format: {{ "score": number (0-100), "analysis": "string" }}
    Candidate: {json.dumps(candidate_data)}
    Job: {job_description}
    """
    try:
        response = await model.generate_content_async(prompt)
        if not response or not response.text:
            return {"score": 0, "analysis": "AI failed to generate a response"}
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
        return json.loads(text)
    except Exception as e:
        print(f"AI Ranking Error: {e}")
        return {"score": 0, "analysis": "Error during ranking"}

async def get_embedding(text: str):
    """Generates an embedding for the given text using Gemini."""
    if not AI_AVAILABLE:
        return None
    try:
        # Using the embedding model
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document",
            title="Resume Content"
        )
        return result['embedding']
    except Exception as e:
        print(f"AI Embedding Error: {e}")
        return None
