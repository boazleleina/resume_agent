from app.domain.classification import classify_document

def test_classify_document_cover_letter_explicit():
    text = "Dear Hiring Manager, I am writing to express my interest in..."
    assert classify_document(text) == "cover_letter"

def test_classify_document_cover_letter_minor():
    text = "Sincerely, John. I have experience in software."
    # "sincerely" = 1 hit -> score = -5 -> returns "cover_letter"
    assert classify_document(text) == "cover_letter"

def test_classify_document_resume():
    text = "John Doe\nSummary\nI am a software engineer.\nExperience\nGoogle\nSkills\nPython, Java"
    # summary (+1), experience (+1), skills (+1) = 3 -> "resume"
    assert classify_document(text) == "resume"

def test_classify_document_uncertain():
    text = "John Doe\nI worked at Google and have good experience."
    # experience (+1) = 1 -> "uncertain"
    assert classify_document(text) == "uncertain"

def test_classify_document_other():
    text = "This is just a random text document with no keywords."
    # 0 -> "other_document"
    assert classify_document(text) == "other_document"

def test_classify_document_case_insensitive():
    text = "EXPERIENCE\nSKILLS\nEDUCATION"
    assert classify_document(text) == "resume"
