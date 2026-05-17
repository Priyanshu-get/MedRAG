"""
Lightweight medical named entity recognition using regex + keyword matching.
For production, consider replacing with a dedicated bioNER model (e.g., scispaCy).
"""
from __future__ import annotations

import re
from typing import Dict, List, Set

# ── Medical concept dictionaries ──────────────────────────────────────────────

DRUG_PATTERNS = [
    r"\b\w+mab\b",          # Monoclonal antibodies (rituximab, pembrolizumab)
    r"\b\w+nib\b",          # Kinase inhibitors (imatinib, erlotinib)
    r"\b\w+pril\b",         # ACE inhibitors (lisinopril, ramipril)
    r"\b\w+sartan\b",       # ARBs (losartan, valsartan)
    r"\b\w+statin\b",       # Statins (atorvastatin, rosuvastatin)
    r"\b\w+cillin\b",       # Penicillins (amoxicillin, ampicillin)
    r"\b\w+mycin\b",        # Macrolides/aminoglycosides
    r"\b\w+olol\b",         # Beta blockers (metoprolol, atenolol)
    r"\b\w+dipine\b",       # Calcium channel blockers (amlodipine)
]

DISEASE_KEYWORDS: Set[str] = {
    "myocardial infarction", "heart attack", "stroke", "hypertension",
    "diabetes mellitus", "type 2 diabetes", "type 1 diabetes",
    "cancer", "carcinoma", "lymphoma", "leukemia", "tumor",
    "pneumonia", "tuberculosis", "sepsis", "covid-19", "sars-cov-2",
    "alzheimer", "parkinson", "multiple sclerosis", "epilepsy",
    "asthma", "copd", "chronic obstructive", "heart failure",
    "atrial fibrillation", "arrhythmia", "atherosclerosis",
    "rheumatoid arthritis", "lupus", "crohn", "ulcerative colitis",
    "kidney disease", "chronic kidney", "liver cirrhosis", "hepatitis",
}

CLINICAL_TERMS: Set[str] = {
    "randomized controlled trial", "rct", "meta-analysis",
    "systematic review", "cohort study", "case-control",
    "clinical trial", "placebo", "double-blind",
    "sensitivity", "specificity", "positive predictive value",
    "hazard ratio", "odds ratio", "confidence interval",
    "p-value", "statistical significance",
    "mortality", "morbidity", "incidence", "prevalence",
    "remission", "relapse", "recurrence", "survival",
}

_COMPILED_DRUG_PATTERNS = [re.compile(p, re.IGNORECASE) for p in DRUG_PATTERNS]


def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract medical entities from text.
    Returns dict with keys: drugs, diseases, clinical_terms.
    """
    text_lower = text.lower()
    entities: Dict[str, List[str]] = {
        "drugs": [],
        "diseases": [],
        "clinical_terms": [],
    }

    # Drug detection via suffix patterns
    for pattern in _COMPILED_DRUG_PATTERNS:
        matches = pattern.findall(text)
        entities["drugs"].extend(matches)

    # Disease detection via keyword matching
    for disease in DISEASE_KEYWORDS:
        if disease in text_lower:
            entities["diseases"].append(disease)

    # Clinical terms
    for term in CLINICAL_TERMS:
        if term in text_lower:
            entities["clinical_terms"].append(term)

    # Deduplicate
    for key in entities:
        entities[key] = list(dict.fromkeys(entities[key]))

    return entities


def is_medical_query(text: str) -> bool:
    """
    Heuristic check: does this text appear to be a medical query?
    Used as a pre-filter before expensive pipeline stages.
    """
    text_lower = text.lower()
    entities = extract_entities(text)

    # Has explicit medical entities
    if any(entities.values()):
        return True

    # Contains common medical question words
    medical_question_markers = [
        "treatment", "diagnosis", "symptom", "therapy", "drug",
        "medication", "dose", "dosage", "cure", "prevention",
        "risk factor", "guideline", "protocol", "prognosis",
        "side effect", "adverse", "contraindication", "mechanism",
        "pathophysiology", "etiology", "complication", "management",
    ]
    return any(m in text_lower for m in medical_question_markers)
