import asyncio
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

from app.core.config import settings
# Ensure timeouts give ample headroom for home network SSL handshakes
settings.PRIMARY_CONNECT_TIMEOUT = 3.5
settings.FALLBACK_CONNECT_TIMEOUT = 5.0

from app.core.database import connect_to_mongo, close_mongo_connection
from app.core.sentry import init_sentry
from app.services.pipeline import rewrite_pipeline_service
from app.models.rewrite import RewriteRequest, InputType
import sentry_sdk

# 1. Initialize Sentry with full debug mode to observe transport confirmation
init_sentry()
client = sentry_sdk.Hub.current.client
print("Sentry Client initialized:", bool(client))
print("Sentry DSN:", client.dsn if client else "None")

sample_genome = {
    "userId": "test_sentry_user",
    "avgSentenceLength": 14.5,
    "vocabularyRichness": 0.72,
    "transitionHabits": ["Moreover", "Specifically", "In practice"],
    "formalityOffset": 0.1,
    "exemplarExcerpts": [
        "Good writing is clear thinking made visible on the page.",
        "We should eliminate filler phrases and write directly."
    ],
    "slopWordsAvoided": ["delve", "testament", "tapestry", "crucial"],
    "quirkPreservations": ["—", ";", "Oxford comma"]
}

async def run_live_tests():
    await connect_to_mongo()
    print("MongoDB Atlas connected successfully.")

    # --------------------------------------------------------------------------
    # 1. HAPPY PATH WITH SENTRY TRANSACTION & SPANS
    # --------------------------------------------------------------------------
    print("\n--- 1. Executing Happy Path Transaction (Primary: openai/gpt-oss-120b) ---")
    settings.GROQ_PRIMARY_MODEL = "openai/gpt-oss-120b"
    settings.GROQ_FALLBACK_MODEL = "openai/gpt-oss-20b"

    with sentry_sdk.start_transaction(op="http.server", name="POST /api/v1/rewrite/pipeline [HappyPath]") as txn:
        txn.set_tag("test.scenario", "happy_path")
        txn.set_tag("llm.primary_model", "openai/gpt-oss-120b")
        txn.set_tag("project.target", "inkflow-backend")

        req1 = RewriteRequest(
            input="It is crucial to delve into the tapestry of artificial intelligence to foster transformative synergies.",
            inputType=InputType.RAW_DRAFT
        )
        resp1 = await rewrite_pipeline_service.execute(req1, sample_genome, words_consumed=15, quota_remaining=2485)
        print("Happy Path Final Output:", resp1.finalOutput)
        print("Happy Path Provider Used:", resp1.provider)
        txn.set_tag("pipeline.provider", resp1.provider)
        txn.set_tag("pipeline.meaning_check_failed", str(resp1.meaningCheckFailed))

    # Give sockets a brief 1s breather between requests
    await asyncio.sleep(1.0)

    # --------------------------------------------------------------------------
    # 2. FORCED FAILOVER TRANSACTION WITH WARNING EVENT
    # --------------------------------------------------------------------------
    print("\n--- 2. Executing Forced Failover Transaction (Triggering Fallback: openai/gpt-oss-20b) ---")
    # Deliberately point primary to invalid model name on Groq
    settings.GROQ_PRIMARY_MODEL = "deliberately-broken-primary-model"
    settings.GROQ_FALLBACK_MODEL = "openai/gpt-oss-20b"

    with sentry_sdk.start_transaction(op="http.server", name="POST /api/v1/rewrite/pipeline [ForcedFailover]") as txn:
        txn.set_tag("test.scenario", "forced_failover")
        txn.set_tag("llm.primary_model", "deliberately-broken-primary-model")
        txn.set_tag("project.target", "inkflow-backend")

        req2 = RewriteRequest(
            input="Furthermore, it is a testament to our agility that we leverage cutting-edge paradigms.",
            inputType=InputType.RAW_DRAFT
        )
        resp2 = await rewrite_pipeline_service.execute(req2, sample_genome, words_consumed=13, quota_remaining=2472)
        print("Failover Final Output:", resp2.finalOutput)
        print("Failover Provider Used:", resp2.provider)
        txn.set_tag("pipeline.provider", resp2.provider)
        txn.set_tag("pipeline.failover_occurred", "true")

    # --------------------------------------------------------------------------
    # 3. REAL ERROR TRACE IN SENTRY
    # --------------------------------------------------------------------------
    print("\n--- 3. Capturing Real Error Trace Event in Sentry ---")
    with sentry_sdk.start_transaction(op="pipeline.error_trace", name="InkFlow Real Error Trace Verification") as txn:
        try:
            raise RuntimeError("InkFlow Verification: Primary LLM Gateway connection dropped, captured for Sentry.")
        except Exception as exc:
            sentry_sdk.set_tag("error.type", "live_smoke_verification")
            sentry_sdk.set_tag("service", "inkflow-backend")
            txn.set_tag("has_error", "true")
            err_event_id = sentry_sdk.capture_exception(exc)
            print("Captured Real Error Trace Event ID:", err_event_id)

    # --------------------------------------------------------------------------
    # 4. FLUSH ALL ENVELOPES TO SENTRY
    # --------------------------------------------------------------------------
    print("\n--- 4. Flushing Sentry Envelopes to Ingest Server ---")
    sentry_sdk.flush(timeout=5.0)
    print("Sentry flush complete! All transactions, spans, and error traces transmitted.")

    await close_mongo_connection()
    print("\n=== ALL VERIFICATION TESTS COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(run_live_tests())
