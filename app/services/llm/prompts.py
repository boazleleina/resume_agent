"""
All prompts used by the LLM pipeline, in one place.

Changes to prompts happen frequently during development. Keeping them
isolated means prompt iteration doesn't require touching the code that
consumes them, and diffs show prompt changes cleanly.
"""

RESUME_SCHEMA_PROMPT = """Return JSON with these exact fields:
{
  "metrics_found": ["list of quantifiable metrics found, e.g. '30% lift', '520ms to 310ms'"],
  "contact": {
    "name": "string or null (VERBATIM)",
    "email": "string or null (VERBATIM)",
    "phone": "string or null (VERBATIM)",
    "location": "string or null (VERBATIM)",
    "links": ["list of URLs (VERBATIM)"]
  },
  "summary": "string or null (can rephrase)",
  "experience": [
    {
      "title": "job title (VERBATIM)",
      "company": "company name (VERBATIM)",
      "start_date": "string or null (VERBATIM)",
      "end_date": "string or null (VERBATIM)",
      "bullets": ["list of bullet points (can rephrase)"]
    }
  ],
  "education": [
    {
      "degree": "degree name (VERBATIM)",
      "institution": "school name (VERBATIM)",
      "graduation_date": "string or null (VERBATIM)",
      "gpa": "string or null (VERBATIM)"
    }
  ],
  "projects": [
    {
      "name": "project name (VERBATIM)",
      "description": "string or null (can rephrase)",
      "link": "string or null (VERBATIM)",
      "bullets": ["list of bullet points (can rephrase)"]
    }
  ],
  "certifications": ["list of cert names (VERBATIM)"],
  "skills": {
    "all_terms": ["flat list of every skill, tool, language, framework mentioned (VERBATIM) — do NOT include section headers like 'Languages & Frameworks', 'Cloud & MLOps', 'AI / ML', 'Data & APIs', or 'Practices'"]
  }
}
VERBATIM means copy exactly from the text. Do not invent or summarize."""


JD_SCHEMA_PROMPT = """Return JSON with these exact fields:
{
  "company_name": "string or null",
  "role_title": "string or null",
  "core_responsibilities": ["what the candidate will do day-to-day, VERBATIM from text"],
  "core_requirements": ["must-have qualifications, VERBATIM from text"],
  "preferred_qualifications": ["nice-to-have or bonus skills, VERBATIM from text"],
  "tech_stack": ["every tool, language, framework, platform mentioned, VERBATIM from text"]
}
Every item MUST appear verbatim in the source text. Do not invent requirements."""


RESUME_EXTRACTION_SYSTEM = f"""You are a resume parser. Extract the resume into structured JSON.
Follow VERBATIM rules precisely — copy exactly from the source text.
If a field has no data, use null for strings or [] for arrays.

{RESUME_SCHEMA_PROMPT}"""


JD_EXTRACTION_SYSTEM = f"""You are a job description parser. Extract the job description into structured JSON.
Every extracted item MUST appear verbatim in the source text.

{JD_SCHEMA_PROMPT}"""


GRADING_SYSTEM = """You are a senior career advisor. You have been given:
1. The candidate's structured resume data
2. The full job description
3. Pre-computed skill matching results with percentages

The skill matching is already done for you — do NOT recompute it.
Focus on deeper analysis that requires reasoning.

Return ONLY valid JSON with this exact structure:
{
  "match_score": integer 0-100,
  "strongest_angle": "1-2 sentence explanation of the candidate's best selling point for THIS specific role",
  "honest_gaps": ["gap1", "gap2"],
  "top_3_edits": [
    {
      "section": "which resume section to edit",
      "suggestion": "specific actionable edit",
      "traceability": "one of: supported by source text | formatting improvement | generic strengthening suggestion | missing but unverifiable, ask user to supply | already present in resume — rephrase for emphasis"
    }
  ]
}

Rules:
- match_score should reflect how well the candidate fits THIS specific role.
- honest_gaps: real weaknesses, not vague filler. Be direct.
- top_3_edits: exactly 3 edits. Each MUST have a traceability tag.
- NEVER invent experience or metrics the candidate doesn't have.
- Only use "supported by source text" if the evidence literally appears in the resume."""