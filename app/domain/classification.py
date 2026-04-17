def classify_document(text: str) -> str:
    text_lower = text.lower()
    score = 0
    
    # 1. Cover letter signals (subtract heavily)
    cover_letter_markers = [
        "dear hiring manager", "dear recruiter", "to whom it may concern", 
        "i am writing to express my interest", "thank you for considering my application", 
        "sincerely", "cover letter"
    ]
    cl_hits = sum(1 for marker in cover_letter_markers if marker in text_lower)
    score -= (cl_hits * 5)
    
    # If any strong cover letter signals hit, override and exit early
    if score <= -5:
        return "cover_letter"
        
    # 2. Resume-positive signals (add points)
    resume_markers = [
        "experience", "work experience", "education", "skills", 
        "projects", "certifications", "summary"
    ]
    r_hits = sum(1 for marker in resume_markers if marker in text_lower)
    score += r_hits
    
    # 3. Two-sided scoring classification
    if score >= 3:
        return "resume"
    elif score > 0:
        return "uncertain"
    else:
        return "other_document"
