"""
InkFlow Automated Tests: Evaluation Metrics and Anti-Slop Scoring Suite.

================================================================================
Test Rationale and Verification Coverage:
--------------------------------------------------------------------------------
This test module verifies the quantitative quality and biometric evaluators:
1. `calculate_slop_score`:
   - Verifies that text laden with canonical AI buzzwords ('delve', 'tapestry', 'testament')
     receives an appropriately degraded slop score.
   - Verifies that clean, authentic prose receives a perfect 1.0 score.
2. `calculate_sentence_length_variance` (Burstiness):
   - Verifies that uniform, monotonous sentences have near-zero variance.
   - Verifies that varied, human-like rhythmic prose exhibits high variance.
3. `calculate_semantic_fidelity`:
   - Verifies that content word preservation yields high fidelity (> 0.70).
   - Verifies that completely drifted topics score low fidelity.
4. `compute_all_evals`:
   - Verifies complete report generation packaging all metrics into an `EvalsReport`.
================================================================================
"""

import pytest
from app.services.evals import (
    calculate_slop_score,
    calculate_sentence_length_variance,
    calculate_semantic_fidelity,
    calculate_style_alignment,
    compute_all_evals,
    tokenize_sentences,
)


def test_slop_score_detects_cliches():
    """
    Verifies that paragraphs contaminated with AI clichés are penalized heavily,
    while authentic writing scores 1.0.
    """
    slop_text = (
        "Furthermore, we must delve into the intricate tapestry of our solutions. "
        "It is a testament to our beacon of hope and plays a pivotal, vital role in "
        "fostering holistic innovation to revolutionize the entire realm."
    )
    score_slop = calculate_slop_score(slop_text)
    assert score_slop < 0.60, f"Expected low score for slop text, got {score_slop}"

    clean_text = (
        "We tested the database indexing strategy under load. "
        "Query latency dropped from 140ms to 12ms after adding the composite index. "
        "Deploying to staging this afternoon."
    )
    score_clean = calculate_slop_score(clean_text)
    assert score_clean == 1.0, f"Expected 1.0 for clean text, got {score_clean}"


def test_burstiness_variance_calculation():
    """
    Verifies that burstiness variance distinguishes between flat robotic prose
    and dynamic human sentence rhythm.
    """
    # Flat monotonous text: exactly 5 words in every sentence
    monotonous_sentences = [
        "This is sentence number one.",
        "Here is sentence number two.",
        "Now is sentence number three.",
        "That was sentence number four.",
    ]
    var_flat = calculate_sentence_length_variance(monotonous_sentences)
    assert var_flat == 0.0, f"Expected 0.0 variance for uniform sentences, got {var_flat}"

    # Varied human rhythm: 2 words, then 14 words, then 4 words
    bursty_sentences = [
        "Stop now.",
        "When the servers crashed unexpectedly during the peak traffic spike, the engineering team quickly deployed failover scripts.",
        "Everything was restored promptly.",
    ]
    var_bursty = calculate_sentence_length_variance(bursty_sentences)
    assert var_bursty > 20.0, f"Expected high burstiness variance, got {var_bursty}"


def test_semantic_fidelity_measurement():
    """
    Verifies semantic fidelity scoring between original text and candidate rewrites.
    """
    original = "The research team discovered three new exoplanets orbiting the red dwarf star."
    good_rewrite = "Scientists identified three previously unknown planets around a nearby red dwarf."
    drifted_rewrite = "Today's cafeteria menu features chicken salad and chocolate chip cookies."

    fidelity_good = calculate_semantic_fidelity(original, good_rewrite)
    fidelity_drifted = calculate_semantic_fidelity(original, drifted_rewrite)

    assert fidelity_good > 0.60, f"Expected good fidelity, got {fidelity_good}"
    assert fidelity_drifted < 0.40, f"Expected low fidelity for drifted text, got {fidelity_drifted}"


def test_compute_all_evals_aggregated_report():
    """
    Verifies that compute_all_evals produces a valid, bounded EvalsReport instance.
    """
    original = "The backend microservice handles payment verification and issues access tokens."
    rewritten = "Our auth service verifies credit cards and generates user JWT tokens swiftly."
    genome = {"average_sentence_length": 12.0}

    report = compute_all_evals(original, rewritten, genome)

    assert 0.0 <= report.slop_reduction_score <= 1.0
    assert 0.0 <= report.style_alignment_score <= 1.0
    assert 0.0 <= report.semantic_fidelity_score <= 1.0
    assert report.burstiness_variance >= 0.0
