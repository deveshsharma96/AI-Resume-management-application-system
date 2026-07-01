# resume_parser.py
"""
import re
from typing import Dict, Any, Optional
import pdfplumber



SECTION_HEADERS = {

    # ---------- PROFILE / SUMMARY ----------
    "summary": [
        "summary",
        "profile",
        "professional summary",
        "about",
        "career summary",
        "overview"
    ],

    # ---------- EXPERIENCE ----------
    "experience": [
        "experience",
        "experiences",
        "work experience",
        "professional experience",
        "employment history",
        "career history",
        "industry experience"
    ],

    # ---------- EDUCATION ----------
    "education": [
        "education",
        "academic background",
        "academics",
        "degrees",
        "qualifications",
        "educational qualifications"
    ],

    # ---------- SKILLS ----------
    "skills": [
        "skills",
        "technical skills",
        "skillset",
        "skill set",
        "core skills",
        "key skills",
        "technical expertise",
        "technical competencies",
        "technologies",
        "tech stack",
        "tools",
        "tools & technologies",
        "programming skills"
    ],

    # ---------- CERTIFICATIONS ----------
    "certifications": [
        "certification",
        "certifications",
        "certificate",
        "certificates",
        "licenses",
        "training",
        "courses",
        "professional certifications"
    ],

    # ---------- EXTRACURRICULAR ----------
    "extracurricular": [
        "extracurricular",
        "activities",
        "extra curricular activities",
        "co-curricular activities",
        "achievements",
        "accomplishments"
    ],

    # ---------- INTERESTS ----------
    "interests": [
        "interests",
        "hobbies",
        "personal interests"
    ]
}


# Flattened list for boundary detection
ALL_SECTION_TITLES = sorted(
    {h for group in SECTION_HEADERS.values() for h in group},
    key=len,
    reverse=True
)


# ===============================
# TEXT EXTRACTION
# ===============================
def extract_text(file_path: str) -> str:
    text = ""

    try:
        with pdfplumber.open(file_path) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception:
        pass

    if len(text.strip()) < 300:
        try:
            from tika import parser
            parsed = parser.from_file(file_path)
            text = parsed.get("content") or ""
        except Exception:
            pass

    return text.strip()


# ===============================
# SECTION EXTRACTION (FIXED)
# ===============================
def extract_section(text: str, headers: list) -> str:
    lines = [l.strip() for l in text.splitlines()]
    start = None
    end = None

    headers_lower = [h.lower() for h in headers]

    # -------- Find section start --------
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(line_lower.startswith(h) for h in headers_lower):
            start = i + 1
            break

    if start is None:
        return ""

    # -------- Find section end --------
    for j in range(start, len(lines)):
        line_lower = lines[j].lower()
        if any(line_lower.startswith(h) for h in ALL_SECTION_TITLES):
            end = j
            break

    section_lines = lines[start:end] if end else lines[start:]
    return "\n".join(section_lines).strip()

# ===============================
# BASIC HELPERS
# ===============================
def _first_non_empty_line(text: str) -> Optional[str]:
    for line in text.splitlines():
        s = line.strip()
        if s:
            return s
    return None


def normalize_spaces(s: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


# ===============================
# CORE FIELD EXTRACTORS
# ===============================
def extract_email(text: str) -> Optional[str]:
    m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return m.group(0).lower() if m else None


def extract_phone(text: str) -> Optional[str]:
    m = re.search(r"(\+?\d[\d\-\s]{7,}\d)", text)
    return re.sub(r"[\s\-]+", "", m.group(0)) if m else None


def extract_name(text: str) -> Optional[str]:
    first = _first_non_empty_line(text)
    if not first:
        return None

    if re.search(r"\b(resume|curriculum vitae|cv)\b", first, re.I):
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        return normalize_spaces(lines[1]).title() if len(lines) > 1 else None

    return normalize_spaces(first).title()


# ===============================
# SKILLS EXTRACTION
# ===============================
def extract_skills(text: str):
    skills_text = extract_section(
        text,
        headers=SECTION_HEADERS["skills"]
    )

    if not skills_text:
        return []

    skills = []
    seen = set()

    for line in skills_text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Split combined lines like: Git, Postman, VS Code
        parts = [p.strip() for p in re.split(r",|/|\||•", line) if p.strip()]

        for skill in parts:
            # Avoid long sentences accidentally slipping in
            if len(skill.split()) > 4:
                continue

            key = skill.lower()
            if key not in seen:
                seen.add(key)
                skills.append({
                    "skill_name": skill,
                    "skill_experience": ""
                })

    return skills

def extract_education(text: str):
    edu_text = extract_section(text, SECTION_HEADERS["education"])
    if not edu_text:
        return []

    education = []

    for line in edu_text.splitlines():
        degree_match = re.search(
            r"(B\.?Tech|M\.?Tech|BCA|MBA|MCA|12th|10th)",
            line,
            re.I
        )
        if not degree_match:
            continue

        year_match = re.search(r"((19|20)\d{2}).*((19|20)\d{2})", line)

        education.append({
            "degree_name": degree_match.group(1),
            "major": None,
            "minor": None,
            "score": None,
            "start_year": year_match.group(1) if year_match else None,
            "start_month": None,
            "end_year": year_match.group(3) if year_match else None,
            "end_month": None
        })
    return education

def extract_work_history(text: str):
    exp_text = extract_section(text, SECTION_HEADERS["experience"])
    if not exp_text:
        return []

    work_history = []

    for line in exp_text.splitlines():
        if not line.strip():
            continue

        year_match = re.search(r"(19|20)\d{2}", line)
        if not year_match:
            continue

        parts = [p.strip() for p in line.split(",")]

        designation = parts[0] if parts else None
        organization_raw = parts[1] if len(parts) > 1 else None

        organization = None
        if organization_raw:
            organization = re.sub(r"(19|20)\d{2}.*", "", organization_raw).strip()

        work_history.append({
            "organization": organization,
            "org_start_year": year_match.group(0),
            "org_start_month": None,
            "org_end_year": None,
            "org_end_month": None,
            "designations": [
                {
                    "designation": designation,
                    "start_year": year_match.group(0),
                    "start_month": None,
                    "end_year": None,
                    "end_month": None,
                    "responsibilities": ""
                }
            ] if designation else []
        })

    return work_history


# ===============================
# CERTIFICATIONS (RELAXED)
# ===============================
def extract_certifications(text: str):
    cert_text = extract_section(text, ["CERTIFICATION", "CERTIFICATE"])
    if not cert_text:
        return []

    certs = []

    for line in cert_text.splitlines():
        if len(line.strip()) < 5:
            continue
        certs.append({
            "certificate": line.strip(),
            "completion_year": None,
            "valid_upto": None
        })

    return certs


# ===============================
# CONFIDENCE SCORING (UNCHANGED)
# ===============================
def calculate_confidence(data: Dict[str, Any]) -> int:
    score = 0
    if not data.get("email"):
        return 0

    score += 20
    if data.get("phone"):
        score += 10
    if len(data.get("skills", [])) >= 5:
        score += 20
    if data.get("degrees"):
        score += 15
    if data.get("work_history"):
        score += 25

    return min(score, 90)


# ===============================
# MAIN PARSER (FIXED)
# ===============================
def parse_resume(file_path: str, cand_id: Optional[str] = None) -> Dict[str, Any]:
    try:
        text = extract_text(file_path)

        parsed = {
            "cand_id": cand_id,
            "name": extract_name(text),
            "email": extract_email(text),
            "phone": extract_phone(text),
            "skills": extract_skills(text),
            "degrees": extract_education(text),
            "work_history": extract_work_history(text),
            "certifications": extract_certifications(text),
        }

        parsed["parse_confidence"] = calculate_confidence(parsed)

        # 🔴 DO NOT DELETE EMPTY LISTS
        return parsed

    except Exception as e:
        return {"error": str(e)}

        
        """



# resume_parser.py

import re
from typing import Dict, Any, Optional
import pdfplumber
from Candidates.utils.ai_parser import parse_resume_ai


SECTION_HEADERS = {

    # ---------- PROFILE / SUMMARY ----------
    "summary": [
        "summary",
        "profile",
        "professional summary",
        "about",
        "career summary",
        "overview"
    ],

    # ---------- EXPERIENCE ----------
    "experience": [
        "experience",
        "experiences",
        "work experience",
        "professional experience",
        "employment history",
        "career history",
        "industry experience"
    ],

    # ---------- EDUCATION ----------
    "education": [
        "education",
        "academic background",
        "academics",
        "degrees",
        "qualifications",
        "educational qualifications"
    ],

    # ---------- SKILLS ----------
    "skills": [
        "skills",
        "technical skills",
        "skillset",
        "skill set",
        "core skills",
        "key skills",
        "technical expertise",
        "technical competencies",
        "technologies",
        "tech stack",
        "tools",
        "tools & technologies",
        "programming skills"
    ],

    # ---------- CERTIFICATIONS ----------
    "certifications": [
        "certification",
        "certifications",
        "certificate",
        "certificates",
        "licenses",
        "training",
        "courses",
        "professional certifications"
    ],

    # ---------- EXTRACURRICULAR ----------
    "extracurricular": [
        "extracurricular",
        "activities",
        "extra curricular activities",
        "co-curricular activities",
        "achievements",
        "accomplishments"
    ],

    # ---------- INTERESTS ----------
    "interests": [
        "interests",
        "hobbies",
        "personal interests"
    ]
}


# Flattened list for boundary detection
ALL_SECTION_TITLES = sorted(
    {h for group in SECTION_HEADERS.values() for h in group},
    key=len,
    reverse=True
)


# ===============================
# TEXT EXTRACTION
# ===============================
def extract_text(file_path: str) -> str:
    text = ""

    try:
        with pdfplumber.open(file_path) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception:
        pass

    if len(text.strip()) < 300:
        try:
            from tika import parser
            parsed = parser.from_file(file_path)
            text = parsed.get("content") or ""
        except Exception:
            pass

    return text.strip()


# ===============================
# SECTION EXTRACTION
# ===============================
def extract_section(text: str, headers: list) -> str:
    lines = [l.strip() for l in text.splitlines()]
    start = None
    end = None

    headers_lower = [h.lower() for h in headers]

    # -------- Find section start --------
    for i, line in enumerate(lines):
        line_lower = line.lower()

        if any(line_lower.startswith(h) for h in headers_lower):
            start = i + 1
            break

    if start is None:
        return ""

    # -------- Find section end --------
    for j in range(start, len(lines)):
        line_lower = lines[j].lower()

        if any(line_lower.startswith(h) for h in ALL_SECTION_TITLES):
            end = j
            break

    section_lines = lines[start:end] if end else lines[start:]

    return "\n".join(section_lines).strip()


# ===============================
# BASIC HELPERS
# ===============================
def _first_non_empty_line(text: str) -> Optional[str]:

    for line in text.splitlines():
        s = line.strip()

        if s:
            return s

    return None


def normalize_spaces(s: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


# ===============================
# CORE FIELD EXTRACTORS
# ===============================
def extract_email(text: str) -> Optional[str]:

    m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)

    return m.group(0).lower() if m else None


def extract_phone(text: str) -> Optional[str]:

    m = re.search(r"(\+?\d[\d\-\s]{7,}\d)", text)

    return re.sub(r"[\s\-]+", "", m.group(0)) if m else None


def extract_name(text: str) -> Optional[str]:

    first = _first_non_empty_line(text)

    if not first:
        return None

    if re.search(r"\b(resume|curriculum vitae|cv)\b", first, re.I):
        lines = [l.strip() for l in text.splitlines() if l.strip()]

        return normalize_spaces(lines[1]).title() if len(lines) > 1 else None

    return normalize_spaces(first).title()


# ===============================
# SKILLS EXTRACTION
# ===============================
def extract_skills(text: str):

    skills_text = extract_section(
        text,
        headers=SECTION_HEADERS["skills"]
    )

    if not skills_text:
        return []

    skills = []
    seen = set()

    for line in skills_text.splitlines():

        line = line.strip()

        if not line:
            continue

        parts = [
            p.strip()
            for p in re.split(r",|/|\||•", line)
            if p.strip()
        ]

        for skill in parts:

            if len(skill.split()) > 4:
                continue

            key = skill.lower()

            if key not in seen:
                seen.add(key)

                skills.append({
                    "skill_name": skill,
                    "skill_experience": ""
                })

    return skills


# ===============================
# EDUCATION EXTRACTION
# ===============================
def extract_education(text: str):

    edu_text = extract_section(
        text,
        SECTION_HEADERS["education"]
    )

    if not edu_text:
        return []

    education = []

    for line in edu_text.splitlines():

        degree_match = re.search(
            r"(B\.?Tech|M\.?Tech|BCA|MBA|MCA|12th|10th)",
            line,
            re.I
        )

        if not degree_match:
            continue

        year_match = re.search(
            r"((19|20)\d{2}).*((19|20)\d{2})",
            line
        )

        education.append({
            "degree_name": degree_match.group(1),
            "major": None,
            "minor": None,
            "score": None,
            "start_year": year_match.group(1) if year_match else None,
            "start_month": None,
            "end_year": year_match.group(3) if year_match else None,
            "end_month": None
        })

    return education


# ===============================
# WORK HISTORY EXTRACTION
# ===============================
def extract_work_history(text: str):

    exp_text = extract_section(
        text,
        SECTION_HEADERS["experience"]
    )

    if not exp_text:
        return []

    work_history = []

    for line in exp_text.splitlines():

        if not line.strip():
            continue

        year_match = re.search(r"(19|20)\d{2}", line)

        if not year_match:
            continue

        parts = [p.strip() for p in line.split(",")]

        designation = parts[0] if parts else None
        organization_raw = parts[1] if len(parts) > 1 else None

        organization = None

        if organization_raw:
            organization = re.sub(
                r"(19|20)\d{2}.*",
                "",
                organization_raw
            ).strip()

        work_history.append({
            "organization": organization,
            "org_start_year": year_match.group(0),
            "org_start_month": None,
            "org_end_year": None,
            "org_end_month": None,
            "designations": [
                {
                    "designation": designation,
                    "start_year": year_match.group(0),
                    "start_month": None,
                    "end_year": None,
                    "end_month": None,
                    "responsibilities": ""
                }
            ] if designation else []
        })

    return work_history


# ===============================
# CERTIFICATIONS
# ===============================
def extract_certifications(text: str):

    cert_text = extract_section(
        text,
        ["CERTIFICATION", "CERTIFICATE"]
    )

    if not cert_text:
        return []

    certs = []

    for line in cert_text.splitlines():

        if len(line.strip()) < 5:
            continue

        certs.append({
            "certificate": line.strip(),
            "completion_year": None,
            "valid_upto": None
        })

    return certs


# ===============================
# CONFIDENCE SCORING
# ===============================
def calculate_confidence(data: Dict[str, Any]) -> int:

    score = 0

    if not data.get("email"):
        return 0

    score += 20

    if data.get("phone"):
        score += 10

    if len(data.get("skills", [])) >= 5:
        score += 20

    # SUPPORT BOTH
    if data.get("degrees") or data.get("education"):
        score += 15

    if data.get("work_history"):
        score += 25

    return min(score, 90)


# ===============================
# MAIN PARSER
# ===============================
def parse_resume(file_path: str, cand_id: Optional[str] = None):

    # =====================================
    # TRY AI PARSER FIRST
    # =====================================
    try:

        ai_result = parse_resume_ai(file_path)

        if ai_result and not ai_result.get("error"):

            # SAFETY DEFAULTS
            ai_result.setdefault("name", "")
            ai_result.setdefault("email", "")
            ai_result.setdefault("phone", "")

            ai_result.setdefault("skills", [])
            ai_result.setdefault("education", [])
            ai_result.setdefault(
                "degrees",
                ai_result.get("education", [])
            )

            ai_result.setdefault("work_history", [])
            ai_result.setdefault("certifications", [])

            ai_result["parser_source"] = "groq_ai"

            print("✅ AI Parser Used")

            return ai_result

    except Exception as e:

        print("❌ AI Parser Failed:", str(e))

    # =====================================
    # FALLBACK TO DEFAULT PARSER
    # =====================================
    try:

        text = extract_text(file_path)

        education_data = extract_education(text)

        parsed = {
            "cand_id": cand_id,
            "name": extract_name(text),
            "email": extract_email(text),
            "phone": extract_phone(text),

            "skills": extract_skills(text),

            # KEEP BOTH FOR SAFETY
            "education": education_data,
            "degrees": education_data,

            "work_history": extract_work_history(text),

            "certifications": extract_certifications(text),
        }

        parsed["parse_confidence"] = calculate_confidence(parsed)

        parsed["parser_source"] = "default_parser"

        print("✅ Default Parser Used")

        return parsed

    except Exception as e:

        return {"error": str(e)}