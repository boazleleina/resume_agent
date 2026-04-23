"""
Skill name normalization for match computation.

The alias map catches ~80% of false negatives from trivial formatting
differences (Node.js vs NodeJS, Postgres vs PostgreSQL). For the
remaining ~20% (semantic synonyms like "machine learning" ≈ "ML"),
upgrade to sentence-transformers cosine similarity.
"""

SKILL_ALIASES = {
    "postgres": "postgresql",
    "node": "node.js",
    "nodejs": "node.js",
    "react.js": "react",
    "reactjs": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "next.js": "nextjs",
    "amazon web services": "aws",
    "google cloud platform": "gcp",
    "google cloud": "gcp",
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "llm": "large language model",
    "llms": "large language model",
    "k8s": "kubernetes",
    "tf": "terraform",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "fast api": "fastapi",
    "ci/cd": "ci cd",
    "ci cd": "ci cd",
    "mongo": "mongodb",
    "dot net": ".net",
    "dotnet": ".net",
    "c sharp": "c#",
    "golang": "go",
}


def normalize_skill(skill: str) -> str:
    """Lowercase, strip, and apply alias normalization."""
    normalized = skill.lower().strip()
    return SKILL_ALIASES.get(normalized, normalized)