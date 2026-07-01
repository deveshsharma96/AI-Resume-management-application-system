from groq import Groq
import os
import json
import pdfplumber
import re

from datetime import datetime

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
 
def extract_text(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    return text
 
 
def parse_resume_ai(file_path):
    try:
        text = extract_text(file_path)
 
        prompt = f"""
        Extract structured resume data in STRICT JSON format.
 
        Return ONLY valid JSON. No explanation.
 
        Required format:
               
        {{
            "name": "",
            "email": "",
            "phone": "",
            "skills": [{{"skill_name": "", "skill_experience": ""}}],
            "education": [{{"degree_name": "", "start_year": "", "end_year": ""}}],
            "work_history": [{{"organization": "", "org_start_year": "", "org_end_year": "", "designations":[{{"designation": "", "start_year": "", "end_year": "", "responsibilities": ""}}]}}],
            "certifications": [{{"certificate": "", "completion_year": ""}}],
            "parse_confidence": 80
        }}
 
        Resume Text:
        {text[:12000]}
        """
 
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0   # 🔥 important for consistent JSON
        )
 
        raw_output = response.choices[0].message.content.strip()
 
        parsed = safe_json_parse(raw_output)
       
        # 🔥 REMOVE unsupported fields
        UNSUPPORTED_KEYS = [
            "preferred_locations",
            "offer_status",
            "offers"
        ]
 
        for key in UNSUPPORTED_KEYS:
            parsed.pop(key, None)
 
        if not isinstance(parsed, dict):
            return {"error": "Invalid JSON from AI"}
 
        # ✅ HARD SAFETY (prevents frontend break)
        parsed.setdefault("skills", [])
        parsed.setdefault("education", [])
        parsed.setdefault("work_history", [])
        parsed.setdefault("certifications", [])
       
        # ✅ Fix skills structure
        if not isinstance(parsed.get("skills"), list):
            parsed["skills"] = []
 
        clean_skills = []
        for sk in parsed["skills"]:
            if isinstance(sk, dict):
                clean_skills.append({
                    "skill_name": sk.get("skill_name"),
                    "skill_experience": sk.get("skill_experience")
                })
        parsed["skills"] = clean_skills

       
        parsed["total_experience"] = calculate_total_experience(parsed.get("work_history", []))


        return parsed
 
    except Exception as e:
        return {"error": str(e)}
 
 
def safe_json_parse(text):
   
 
    try:
        return json.loads(text)
    except:
        try:
            match = re.search(r"\{.*\}", text, re.S)
            if match:
                return json.loads(match.group(0))
        except:
            pass
 

    return {}
 
 
 
def calculate_total_experience(work_history):
    total_months = 0
 
    for job in work_history:
        try:
            start_year = int(job.get("org_start_year") or 0)
            end_year = job.get("org_end_year")
 
            if not start_year:
                continue
 
            # If currently working
            if not end_year or str(end_year).lower() in ["present", "current"]:
                end_year = datetime.now().year
            else:
                end_year = int(end_year)
 
            months = (end_year - start_year) * 12
            total_months += max(months, 0)
 
        except:
            continue
 
    years = total_months // 12
    months = total_months % 12
 
    return f"{years} years {months} months"

    

