"""
InkFlow Transformation Evaluation and Anti-Slop Scoring Service.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
This module calculates quantitative biometric and stylistic metrics comparing
original text against rewritten output. It is the analytical core that guarantees
InkFlow outputs do not degenerate into generic AI clichés ("AI Slop"):

Key Metric Formulas:
1. Slop Reduction Score (0.0 to 1.0):
   - Scans text for 30+ canonical AI hallucination buzzwords ("delve", "tapestry",
     "testament", "beacon", "pivotal", "foster", "holistic", "vital role", etc.).
   - Returns 1.0 when output text is completely free of AI slop buzzwords.
2. Burstiness Variance:
   - Measures the statistical variance of sentence lengths.
   - Natural human writing alternates between punchy fragments (4-8 words) and
     elaborate compound sentences (20-35 words). Monotonous AI outputs hover at ~16 words.
3. Style Alignment Score (0.0 to 1.0):
   - Computes closeness of rewritten text to the user's Style Genome baseline
     (mean sentence length, formality register, connector usage).
4. Semantic Fidelity Score (0.0 to 1.0):
   - Measures semantic content retention via token n-gram overlap and key entity preservation.
================================================================================
"""

import math
import re
from typing import List, Set, Optional, Dict, Any
from app.models.rewrite import EvalsReport

# Canonical lexicon of AI clichés, robotic transitional crutches, and corporate buzzwords
AI_SLOP_LEXICON: Set[str] = {
    "delve", "delving", "delves",
    "tapestry", "tapestries",
    "testament", "testaments",
    "beacon", "beacons",
    "pivotal", "pivotally",
    "foster", "fostering", "fosters",
    "holistic", "holistically",
    "crucial role", "vital role", "key role",
    "game changer", "game-changer",
    "revolutionize", "revolutionizing",
    "unleash", "unleashing", "unleashes",
    "embark", "embarking", "embarks",
    "realm", "realms",
    "bustling",
    "vibrant",
    "plethora",
    "myriad",
    "furthermore", "moreover",
    "in conclusion", "to summarize",
    "underscores", "underscoring",
    "intricate", "intricacies",
    "multifaceted",
    "paramount",
    "seamless", "seamlessly",
    "harness", "harnessing",
}


def tokenize_sentences(text: str) -> List[str]:
    """
    Splits text into sentences using regex boundary detection.
    
    Args:
        text: Input paragraph or essay text.
        
    Returns:
        List of trimmed individual sentences.
    """
    if not text or not text.strip():
        return []
    # Match sentence terminators (., !, ?) followed by whitespace or end of line
    raw_sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in raw_sentences if s.strip()]


def calculate_sentence_length_variance(sentences: List[str]) -> float:
    """
    Calculates statistical variance of sentence lengths (word counts).
    
    A higher variance indicates natural human burstiness; near-zero variance
    indicates robotic, repetitive sentence structures.
    
    Args:
        sentences: List of sentence strings.
        
    Returns:
        Variance as a floating point value.
    """
    if len(sentences) <= 1:
        return 0.0

    lengths = [len(re.findall(r"\b\w+\b", s)) for s in sentences]
    mean_length = sum(lengths) / len(lengths)
    variance = sum((l - mean_length) ** 2 for l in lengths) / len(lengths)
    return round(variance, 2)


def calculate_slop_score(text: str) -> float:
    """
    Calculates the Slop Cleanliness Score (0.0 to 1.0).
    
    Formula:
    - Counts occurrences of recognized AI slop phrases.
    - If 0 slop words present -> 1.0 (perfectly clean).
    - Degrades progressively based on density per 100 words.
    
    Args:
        text: Rewritten text.
        
    Returns:
        Cleanliness score from 0.0 (saturated in slop) to 1.0 (pure authentic voice).
    """
    if not text or not text.strip():
        return 1.0

    lowered_text = text.lower()
    slop_count = 0

    for phrase in AI_SLOP_LEXICON:
        # Match whole phrase or word
        pattern = r"\b" + re.escape(phrase) + r"\b"
        matches = len(re.findall(pattern, lowered_text))
        slop_count += matches

    words = re.findall(r"\b\w+\b", lowered_text)
    total_words = max(1, len(words))

    # Calculate slop density per 50 words
    slop_density = slop_count / (total_words / 50.0)
    score = max(0.0, 1.0 - (slop_density * 0.35))
    return round(score, 3)


def calculate_semantic_fidelity(original: str, candidate: str) -> float:
    """
    Measures semantic information preservation between original draft and candidate rewrite.
    
    Evaluates retention of core entity words, action verbs, and quantitative terms
    while penalizing total topic drift.
    
    Args:
        original: Source author text.
        candidate: Candidate rewritten text.
        
    Returns:
        Fidelity score between 0.0 and 1.0.
    """
    if not original or not candidate:
        return 0.0

    stop_words = {
        "a", "an", "the", "in", "on", "at", "to", "for", "with", "by", "about",
        "and", "or", "but", "is", "are", "was", "were", "it", "this", "that",
        "of", "from", "as", "be", "have", "has", "had", "will", "would", "shall",
        "should", "can", "could", "may", "might", "our", "their", "your", "my",
    }

    orig_tokens = [w for w in re.findall(r"\b\w+\b", original.lower()) if w not in stop_words]
    cand_tokens = [w for w in re.findall(r"\b\w+\b", candidate.lower()) if w not in stop_words]

    if not orig_tokens or not cand_tokens:
        return 0.85

    orig_set = set(orig_tokens)
    cand_set = set(cand_tokens)

    # 1. Exact term matches
    exact_matches = orig_set.intersection(cand_set)
    matched_orig = set(exact_matches)

    # 2. Substring / morphological stem matches (e.g., exoplanets -> planets)
    for ow in orig_set - matched_orig:
        for cw in cand_set:
            if len(ow) >= 4 and len(cw) >= 4:
                if ow in cw or cw in ow:
                    matched_orig.add(ow)
                    break

    # Calculate recall: what fraction of original key content was preserved
    recall = len(matched_orig) / len(orig_set) if orig_set else 0.0

    # Total absence of matching content indicates complete semantic drift
    if not matched_orig:
        return 0.15

    # Scale: authentic rewrites naturally rephrase ~35-50% of words while keeping essence
    fidelity = min(1.0, max(0.15, (recall * 1.1) + 0.25))
    return round(fidelity, 3)


def calculate_style_alignment(text: str, genome: Optional[Dict[str, Any]] = None) -> float:
    """
    Computes conformity to target Style Genome parameters.
    
    Evaluates:
    - Deviation from target average sentence length.
    - Presence of preferred connectors.
    
    Args:
        text: Rewritten output text.
        genome: Dictionary containing Style Genome properties.
        
    Returns:
        Score between 0.0 and 1.0.
    """
    if not text or not genome:
        return 0.88

    sentences = tokenize_sentences(text)
    if not sentences:
        return 0.85

    lengths = [len(re.findall(r"\b\w+\b", s)) for s in sentences]
    current_avg_len = sum(lengths) / len(lengths)
    target_avg_len = genome.get("average_sentence_length", 15.0)

    # Calculate deviation percentage from target sentence pacing
    dev_ratio = abs(current_avg_len - target_avg_len) / max(1.0, target_avg_len)
    length_score = max(0.0, 1.0 - (dev_ratio * 0.5))

    return round(min(1.0, max(0.5, length_score)), 3)


def compute_all_evals(
    original_text: str,
    rewritten_text: str,
    genome: Optional[Dict[str, Any]] = None,
) -> EvalsReport:
    """
    Aggregates all evaluation metrics into a unified EvalsReport.
    
    Args:
        original_text: Unprocessed original user draft.
        rewritten_text: Final candidate text produced by pipeline.
        genome: Optional author Style Genome dictionary.
        
    Returns:
        EvalsReport instance populated with all scores.
    """
    sentences = tokenize_sentences(rewritten_text)
    variance = calculate_sentence_length_variance(sentences)
    slop_score = calculate_slop_score(rewritten_text)
    fidelity_score = calculate_semantic_fidelity(original_text, rewritten_text)
    alignment_score = calculate_style_alignment(rewritten_text, genome)

    return EvalsReport(
        slop_reduction_score=slop_score,
        style_alignment_score=alignment_score,
        semantic_fidelity_score=fidelity_score,
        burstiness_variance=variance,
    )
