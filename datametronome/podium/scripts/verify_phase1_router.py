#!/usr/bin/env python3
"""
Verify Phase 1 router + Phase 2 sub-agents.

Phase 1: intent classification, quick→fast model
Phase 2: intent→agent routing (config, investigation, report)

Prerequisites:
  - Podium running (make start-podium or docker compose up)
  - .env: ADK_MODEL_QUICK=ollama_chat/qwen2.5, ADK_MODEL=gemini-2.0-flash
  - Ollama running if using quick path; valid API key for Gemini

Usage:
  python scripts/verify_phase1_router.py [--base-url URL] [--phase 1|2|all]
"""

import argparse
import json
import sys

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Verify Phase 1 intent router")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8001",
        help="Podium API base URL",
    )
    parser.add_argument(
        "--user",
        default="admin",
        help="Login username",
    )
    parser.add_argument(
        "--password",
        default="admin",
        help="Login password",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only test intent classifier + agent resolution (no API calls)",
    )
    parser.add_argument(
        "--phase",
        choices=["1", "2", "3", "all"],
        default="all",
        help="Phase to verify: 1 (router), 2 (sub-agents), 3 (orchestrator/chain), all (default)",
    )
    args = parser.parse_args()

    if args.dry_run:
        from datametronome_podium.services.intent_router import (  # type: ignore[unresolved-import]
            classify_intent,
            evaluate_classifier_against_dataset,
        )

        print("Dry run: intent classifier + Phase 2 agent resolution\n")
        result = evaluate_classifier_against_dataset()
        print(f"Dataset accuracy: {result.get('accuracy', 0):.1%} ({result.get('correct')}/{result.get('total')})")
        from datametronome_podium.services.orchestrator import plan_orchestration  # type: ignore[unresolved-import]

        print("\nIntent → Agent mapping:")
        for msg, exp_intent, exp_agent in [
            ("Hi", "quick", "report"),
            ("Why did check X fail?", "investigation", "investigation"),
            ("Create a new stave", "config", "config"),
            ("Show me the quality report", "report", "report"),
            ("What tables are in stave X?", "exploration", "investigation"),
        ]:
            got_intent = classify_intent(msg)
            mode, agent_types = plan_orchestration(got_intent, msg)
            got_agent = agent_types[-1] if agent_types else "report"
            ok_i = "✅" if got_intent == exp_intent else "❌"
            ok_a = "✅" if got_agent == exp_agent else "❌"
            chain = f" chain={agent_types}" if mode == "chain" else ""
            print(f"  {ok_i}{ok_a} \"{msg[:40]}...\" → intent={got_intent}, agent={got_agent}{chain}")

        print("\nPhase 3 chain trigger:")
        for msg in [
            "Why did X fail and how do I fix it?",
            "Investigate the failure and suggest checks",
        ]:
            got_intent = classify_intent(msg)
            mode, agents = plan_orchestration(got_intent, msg)
            ok = "✅" if mode == "chain" and "config" in agents else "❌"
            print(f"  {ok} \"{msg[:45]}...\" → mode={mode} agents={agents}")
        print("\n✅ Dry run OK. Run without --dry-run to test full API.")
        return

    base = args.base_url.rstrip("/")

    # Login
    print("1. Logging in...")
    login_resp = httpx.post(
        f"{base}/api/v1/auth/login",
        json={"username": args.user, "password": args.password},
        timeout=10.0,
    )
    if login_resp.status_code != 200:
        print(f"   ❌ Login failed: {login_resp.status_code} {login_resp.text}")
        sys.exit(1)
    token = login_resp.json().get("access_token")
    if not token:
        print("   ❌ No access_token in login response")
        sys.exit(1)
    print("   ✅ Logged in")
    headers = {"Authorization": f"Bearer {token}"}

    # Test cases: (message, expected_intent, expected_agent, model_hint)
    phase1_tests = [
        ("Hi", "quick", "report", "ollama"),
        ("What's the status?", "quick", "report", "ollama"),
        ("Why did check X fail?", "investigation", "investigation", "gemini"),
    ]
    phase2_tests = [
        ("Create a new stave for PostgreSQL", "config", "config", None),
        ("Suggest quality checks for the orders table", "config", "config", None),
        ("Show me the quality report", "report", "report", None),
        ("What tables are in the bigquery stave?", "exploration", "investigation", None),
    ]
    phase3_tests = [
        ("Why did check X fail and how do I fix it?", "investigation", "config", None),
        ("Investigate the failure and suggest quality checks", "investigation", "config", None),
    ]
    if args.phase == "1":
        tests = phase1_tests
    elif args.phase == "2":
        tests = phase2_tests
    elif args.phase == "3":
        tests = phase3_tests
    else:
        tests = phase1_tests + phase2_tests + phase3_tests

    print(f"\n2. Sending chat messages (phase={args.phase})...\n")
    all_ok = True
    for row in tests:
        msg = row[0]
        exp_intent = row[1]
        exp_agent = row[2]
        model_hint = row[3] if len(row) > 3 else None
        print(f"   Message: \"{msg}\"")
        resp = httpx.post(
            f"{base}/api/v1/chat/",
            headers=headers,
            json={"message": msg},
            timeout=120.0,
        )
        if resp.status_code != 200:
            print(f"   ❌ Chat failed: {resp.status_code} {resp.text[:200]}")
            all_ok = False
            continue
        data = resp.json()
        intent = data.get("intent")
        agent_type = data.get("agentType")
        model = data.get("model")
        snippet = (data.get("message") or "")[:80]
        orch_mode = data.get("orchestrationMode")
        chain = data.get("agentChain")
        orch = f" mode={orch_mode}" + (f" chain={chain}" if chain else "")
        print(f"   Response: intent={intent or '?'}, agent={agent_type or '?'}{orch}, model={model or '?'}")
        print(f"   Message: {snippet}...")
        if intent is None:
            print(f"   ⚠️  intent missing - restart Podium to load Phase 1+2 code")
            all_ok = False
        elif intent != exp_intent:
            print(f"   ⚠️  Expected intent={exp_intent}, got {intent}")
            all_ok = False
        elif agent_type and agent_type != exp_agent:
            # Phase 3 chain: final agent is config, chain=[investigation,config]
            if orch_mode == "chain" and chain and exp_agent in chain:
                pass  # OK
            else:
                print(f"   ⚠️  Expected agent={exp_agent}, got {agent_type}")
                all_ok = False
        elif model_hint == "ollama" and model and "ollama" not in model.lower():
            print(f"   ⚠️  Quick should use Ollama, got model={model}")
            all_ok = False
        elif model_hint == "gemini" and model and "gemini" not in model.lower():
            print(f"   ⚠️  Non-quick should use Gemini, got model={model}")
            all_ok = False
        else:
            print(f"   ✅ OK")
        print()

    if all_ok:
        print("3. ✅ Phase 1 + Phase 2 verification passed")
    else:
        print("3. ❌ Some checks failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
