from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
USERS_DIR = DATA_DIR / "users"
UPLOADS_DIR = DATA_DIR / "uploads"
OUTPUTS_DIR = ROOT_DIR / "outputs"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
)

# Deliberately curated to high-signal ATS skills for software/tech roles.
COMMON_SKILLS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "node.js",
    "node",
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "sql",
    "postgresql",
    "mysql",
    "mongodb",
    "redis",
    "graphql",
    "rest",
    "microservices",
    "ci/cd",
    "git",
    "linux",
    "terraform",
    "ansible",
    "machine learning",
    "data analysis",
    "pandas",
    "numpy",
    "pytorch",
    "tensorflow",
    "scikit-learn",
    "nlp",
    "agile",
    "scrum",
    "system design",
    "testing",
    "pytest",
    "selenium",
    "playwright",
}

STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "to",
    "of",
    "for",
    "in",
    "on",
    "with",
    "by",
    "at",
    "is",
    "are",
    "be",
    "as",
    "you",
    "we",
    "our",
    "will",
    "that",
    "this",
    "from",
    "your",
    "have",
    "has",
    "had",
    "can",
    "should",
    "must",
    "may",
    "about",
    "role",
    "job",
    "experience",
    "years",
}
