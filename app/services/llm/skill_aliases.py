"""
Skill name normalization for match computation.

The alias map catches ~80% of false negatives from trivial formatting
differences (Node.js vs NodeJS, Postgres vs PostgreSQL). For the
remaining ~20% (semantic synonyms like "machine learning" ≈ "ML"),
upgrade to sentence-transformers cosine similarity.
"""
import re

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


def expand_skill(skill: str) -> list[str]:
    """
    Expand one skill string into 1-N normalized canonical forms.

    Handles:
      - Parenthetical expansions: "AWS (EC2, S3)" → ["aws"]
      - API suffix:               "OpenAI API"    → ["openai"]
      - Slash compounds (both parts ≥3 chars): "JavaScript/TypeScript" → ["javascript", "typescript"]
      - Space-surrounded plus:    "REST + GraphQL" → ["rest", "graphql"]

    Does NOT split:
      - "CI/CD"      (CD is 2 chars)
      - "A/B testing" (A is 1 char)
      - "C++"        (+ not space-surrounded)
    """
    s = re.sub(r'\s*\(.*?\)', '', skill).strip()          # drop "(ec2, s3, ...)"
    s = re.sub(r'\s+apis?$', '', s, flags=re.IGNORECASE)  # drop trailing " API"

    # Split on space-surrounded "+" only (avoids C++, C#)
    parts = re.split(r'\s+\+\s+', s)

    # For each part, split on "/" only when both sides are ≥3 chars (avoids CI/CD, A/B)
    expanded = []
    for part in parts:
        slash_parts = re.split(r'\s*/\s*', part)
        if len(slash_parts) > 1 and all(len(p.strip()) >= 3 for p in slash_parts):
            expanded.extend(p.strip() for p in slash_parts)
        else:
            expanded.append(part.strip())

    return [normalize_skill(p) for p in expanded if p.strip()]