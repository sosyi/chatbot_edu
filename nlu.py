import json
import re
from typing import Tuple, Optional, List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from db import list_faqs, get_intents
from config import FAQ_SIM_THRESHOLD

# Entity extractors:
# - Course codes like 158.780
COURSE_RE = re.compile(r"\b(\d{3}\.\d{3})\b")
# - Assignments like A1, Assignment 1
ASSIGN_RE = re.compile(r"\b(?:A(?:ssignment)?\s*\d+|A\d+)\b", re.I)

class FAQMatcher:
    """TF-IDF + cosine similarity FAQ retriever."""
    def __init__(self):
        self.faq_rows = list_faqs()
        self.questions = [f"{r.question} {r.tags or ''}" for r in self.faq_rows]
        self.vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1,2))
        self.matrix = self.vectorizer.fit_transform(self.questions) if self.questions else None

    def search(self, text: str) -> Tuple[Optional[int], float]:
        """Return (faq_id, similarity) if above threshold; otherwise (None, score)."""
        if not self.questions:
            return None, 0.0
        qv = self.vectorizer.transform([text])
        sims = cosine_similarity(qv, self.matrix)[0]
        best_idx = sims.argmax()
        score = float(sims[best_idx])
        if score >= FAQ_SIM_THRESHOLD:
            faq_id = int(self.faq_rows[best_idx].id)
            return faq_id, score
        return None, float(score)

class IntentDetector:
    """Simple rule-based intent classifier driven by regex patterns from DB."""
    def __init__(self):
        self.rules = []  # list of (intent_name, [compiled regex...])
        for row in get_intents():
            try:
                patterns = json.loads(row.patterns or "[]")
            except Exception:
                patterns = []
            self.rules.append((row.name, [re.compile(pat, re.I) for pat in patterns]))

    def detect(self, text: str) -> Optional[str]:
        t = text.strip()
        for name, regs in self.rules:
            for rg in regs:
                if rg.search(t):
                    return name
        return None

def extract_entities(text: str) -> Dict[str, Optional[str]]:
    """Extract basic entities (course code, assignment identifier)."""
    course = None
    m = COURSE_RE.search(text)
    if m:
        course = m.group(1)

    assignment = None
    m2 = ASSIGN_RE.search(text)
    if m2:
        assignment = m2.group(0).upper().replace("ASSIGNMENT", "A").replace(" ", "")

    return {"course": course, "assignment": assignment}

class NLU:
    """Orchestrates intent detection + FAQ retrieval + entity extraction."""
    def __init__(self):
        self.faq = FAQMatcher()
        self.intent = IntentDetector()

    def analyze(self, user_text: str) -> Tuple[Optional[str], Optional[int], float, Dict[str, Optional[str]]]:
        ents = extract_entities(user_text)

        it = self.intent.detect(user_text)
        if it:
            return it, None, 1.0, ents

        faq_id, score = self.faq.search(user_text)
        if faq_id is not None:
            return "faq", faq_id, score, ents

        return None, None, 0.0, ents
