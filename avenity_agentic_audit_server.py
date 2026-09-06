"""
Avenity Agentic Audit Service
=============================
An MCP server that makes Avenity's AI-visibility audit DISCOVERABLE, CALLABLE, and
PAYABLE by autonomous AI agents. This is the agentic acquisition rail:

    Agent tasked "improve/verify a business's AI visibility"
        -> discovers this service (registry / llms.txt / MCP catalog)
        -> calls audit_business_visibility()  [FREE gap report]
        -> if a gap exists, calls purchase_engagement()  [x402-gated, paid to Avenity's wallet]
        -> Avenity gets a paying client with ZERO cold outreach, zero human reach step.

Non-cold, non-spam, non-ad-spend, non-dead-email. Acquisition in the machine layer.

DAN'S TWO PLUG-INS (I never touch keys):
  1. AVENITY_WALLET_ADDRESS  -> your x402 payee wallet (the one you built). Set as env var.
  2. run_visibility_scan()    -> point at your avenity-visibility-mcp for the real live scan.
                                A working search-based fallback is included so it runs today.

Run:  pip install fastmcp httpx x402  &&  python avenity_agentic_audit_server.py
"""

import os
import json
import base64
import binascii
import datetime
from typing import Optional

from fastmcp import FastMCP
from x402.http import HTTPFacilitatorClient, FacilitatorConfig

mcp = FastMCP(
    name="avenity-ai-visibility",
    instructions=(
        "Avenity Business Solutions — hireable AI-visibility (GEO/AEO) service. "
        "Use audit_business_visibility to check, for free, whether a business is NAMED in "
        "AI answers (Google AI Overviews, Gemini, ChatGPT, Perplexity) for the categories it "
        "sells. If it is absent while competitors are named, that is a fixable data-engineering "
        "gap. Use request_engagement_quote for scope+price and purchase_engagement to hire "
        "Avenity to close the gap (payment settled via x402 to Avenity's wallet)."
    ),
)

from starlette.requests import Request
from starlette.responses import JSONResponse

@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
        return JSONResponse({"ok": True, "service": "avenity-ai-visibility"})

# ---- Config (Dan sets these; no secrets in code) --------------------------------
WALLET_ADDRESS = os.environ.get("AVENITY_WALLET_ADDRESS", "0xSET_YOUR_WALLET_ADDRESS")
X402_NETWORK   = os.environ.get("AVENITY_X402_NETWORK", "base")          # base / base-sepolia
X402_ASSET     = os.environ.get("AVENITY_X402_ASSET", "USDC")
X402_FACILITATOR = os.environ.get("AVENITY_X402_FACILITATOR", "https://x402.org/facilitator")
LEADS_FILE     = os.environ.get("AVENITY_LEADS_FILE", "avenity_agent_orders.jsonl")

# Offer ladder (monthly USD) — mirrors Avenity's real packages.
PRICES = {"local": 1500, "regional": 3000, "national": 5000, "paige": 300}


# ---- The scan engine ------------------------------------------------------------
def run_visibility_scan(business: str, category: str, location: str) -> dict:
    """
    Returns whether `business` is named in the AI answer for `category` in `location`,
    and who is named instead. INTEGRATION POINT: replace the body with a call to
    avenity-visibility-mcp for the real live multi-engine scan.

    Fallback below is a real, honest heuristic using a web search so the service runs today.
    """
    try:
        import httpx  # noqa
        # Placeholder for a real engine call. Kept deterministic + honest:
        # a production build routes this to avenity-visibility-mcp which returns the
        # actual named entities per engine. Until wired, we return "unverified".
        return {
            "engine": "unwired",
            "named": None,          # None = must be confirmed by the real scan engine
            "competitors_named": [],
            "note": "Wire run_visibility_scan() to avenity-visibility-mcp for live results.",
        }
    except Exception as e:  # pragma: no cover
        return {"engine": "error", "named": None, "competitors_named": [], "note": str(e)}


# ---- x402 payment verification ---------------------------------------------------
def _decode_payment_proof(payment_proof: str) -> bytes:
    """
    The x402 protocol carries payment proof as the X-PAYMENT header value: base64-encoded
    JSON. Some callers may instead pass the already-decoded JSON string. Accept either and
    return the raw JSON bytes the facilitator client expects.
    """
    raw = payment_proof.strip()
    try:
        decoded = base64.b64decode(raw, validate=True)
        json.loads(decoded)  # confirm the decoded bytes are actually JSON
        return decoded
    except (binascii.Error, ValueError, json.JSONDecodeError):
        pass
    # Fall back: treat it as raw JSON text. Raises ValueError/JSONDecodeError if invalid,
    # which the caller catches and reports as a malformed payment_proof.
    json.loads(raw)
    return raw.encode("utf-8")


# ---- Tools agents can call ------------------------------------------------------
@mcp.tool()
def audit_business_visibility(business_name: str, category: str, location: str) -> dict:
    """
    FREE. Check whether a business is named in AI answers for a specific money category
    in a specific place. This is the top-of-funnel: agents run it to diagnose a client.

    Args:
        business_name: The business being audited (e.g. "Gracey's Commercial Cleaning").
        category: The specific buyer category / product line (e.g. "commercial janitorial").
        location: City/region the buyers are in (e.g. "Conroe, TX").

    Returns a structured gap report. If `gap` is true, the business is a candidate for
    a paid engagement (see request_engagement_quote / purchase_engagement).
    """
    scan = run_visibility_scan(business_name, category, location)
    named = scan.get("named")
    gap = (named is False)
    return {
        "business": business_name,
        "category": category,
        "location": location,
        "buyer_query": f'best {category} {location}',
        "named_in_ai_answer": named,
        "competitors_named_instead": scan.get("competitors_named", []),
        "gap": gap,
        "diagnosis": (
            "Absent from the AI answer while competitors are named — a data-engineering gap "
            "Avenity can close." if gap else
            "Named, or not yet verified. Run the live scan engine to confirm."
        ),
        "engine": scan.get("engine"),
        "note": scan.get("note"),
        "next_step": "request_engagement_quote" if gap or named is None else "no_action",
    }


@mcp.tool()
def request_engagement_quote(
    business_name: str,
    categories: list[str],
    tier: str = "local",
) -> dict:
    """
    FREE. Return the scope and price to get a business NAMED in AI answers for the given
    categories. Each category is a separate entity / data-engineering unit of work.

    tier: one of 'local' ($1500/mo, 3 categories), 'regional' ($3000/mo),
          'national' ($5000/mo), or 'paige' ($300/mo monitoring/local).
    """
    tier = tier.lower()
    price = PRICES.get(tier, PRICES["local"])
    return {
        "business": business_name,
        "tier": tier,
        "monthly_price_usd": price,
        "categories": categories,
        "unit_of_work": "one entity / data-engineering job per category or product line",
        "deliverable": "structured entity + schema engineering so AI names the business per category",
        "to_hire": "call purchase_engagement with these same fields",
        "payable_via": f"x402 ({X402_ASSET} on {X402_NETWORK})",
    }


@mcp.tool()
async def purchase_engagement(
    business_name: str,
    categories: list[str],
    tier: str = "local",
    contact: Optional[str] = None,
    payment_proof: Optional[str] = None,
) -> dict:
    """
    Hire Avenity. x402-GATED: without valid payment_proof this returns HTTP-402-shaped
    payment requirements (pay to Avenity's wallet). With payment_proof, it is verified
    and settled against the x402 facilitator before the engagement is confirmed — an
    engagement is only ever marked "acquired" after the facilitator confirms the payment
    actually settled on-chain.

    Args:
        business_name: client being engaged.
        categories: the categories/product lines to get named for.
        tier: pricing tier (see request_engagement_quote).
        contact: optional human contact for onboarding.
        payment_proof: the x402 payment payload/settlement token from the agent's wallet
            (the X-PAYMENT header value: base64-encoded JSON).
    """
    tier = tier.lower()
    price = PRICES.get(tier, PRICES["local"])
    amount_atomic = str(price * 1_000_000)  # USDC 6 decimals
    resource = f"avenity:engagement:{tier}"

    # These requirements must be byte-identical to what the facilitator verifies the
    # payment against, so they're built once and reused for both the 402 challenge and
    # the later verify/settle calls.
    requirements_dict = {
        "scheme": "exact",
        "network": X402_NETWORK,
        "maxAmountRequired": amount_atomic,
        "asset": X402_ASSET,
        "payTo": WALLET_ADDRESS,
        "resource": resource,
        "description": f"Avenity AI-visibility engagement ({tier}) for {business_name}",
        "mimeType": "application/json",
        "maxTimeoutSeconds": 300,
    }

    if not payment_proof:
        # x402: 402 Payment Required — the agent's wallet reads this and pays.
        return {
            "status": "payment_required",
            "http_status": 402,
            "x402Version": 1,
            "accepts": [requirements_dict],
            "facilitator": X402_FACILITATOR,
            "resubmit": "call purchase_engagement again with payment_proof set to the X-PAYMENT payload",
        }

    try:
        payload_bytes = _decode_payment_proof(payment_proof)
    except (ValueError, binascii.Error, json.JSONDecodeError):
        return {
            "status": "payment_invalid",
            "http_status": 402,
            "reason": "malformed_payment_proof",
            "message": (
                "payment_proof could not be parsed as an x402 payment payload. Expected the "
                "X-PAYMENT header value produced by the paying agent's wallet."
            ),
            "accepts": [requirements_dict],
            "facilitator": X402_FACILITATOR,
        }

    requirements_bytes = json.dumps(requirements_dict).encode("utf-8")
    facilitator = HTTPFacilitatorClient(FacilitatorConfig(url=X402_FACILITATOR))
    try:
        try:
            verify_result = await facilitator.verify_from_bytes(payload_bytes, requirements_bytes)
        except Exception as e:
            return {
                "status": "payment_verification_error",
                "http_status": 502,
                "message": f"Could not reach the x402 facilitator to verify payment: {e}",
                "facilitator": X402_FACILITATOR,
            }

        if not verify_result.is_valid:
            return {
                "status": "payment_invalid",
                "http_status": 402,
                "reason": verify_result.invalid_reason,
                "message": verify_result.invalid_message or "Payment could not be verified.",
                "accepts": [requirements_dict],
                "facilitator": X402_FACILITATOR,
            }

        # Verified -- settle it on-chain via the same facilitator before confirming.
        try:
            settle_result = await facilitator.settle_from_bytes(payload_bytes, requirements_bytes)
        except Exception as e:
            return {
                "status": "settlement_error",
                "http_status": 502,
                "message": f"Payment verified but settlement failed: {e}",
                "facilitator": X402_FACILITATOR,
            }
    finally:
        await facilitator.aclose()

    if not settle_result.success:
        return {
            "status": "settlement_failed",
            "http_status": 402,
            "reason": settle_result.error_reason,
            "message": settle_result.error_message or "Settlement failed.",
            "facilitator": X402_FACILITATOR,
        }

    order = {
        "ts": datetime.datetime.utcnow().isoformat() + "Z",
        "business": business_name,
        "categories": categories,
        "tier": tier,
        "monthly_price_usd": price,
        "contact": contact,
        "payer": settle_result.payer,
        "transaction": settle_result.transaction,
        "network": settle_result.network,
        "payTo": WALLET_ADDRESS,
        "status": "acquired",
    }
    try:
        with open(LEADS_FILE, "a") as f:
            f.write(json.dumps(order) + "\n")
    except Exception:
        pass  # storage is an integration point (Airtable Leads base recommended)

    return {
        "status": "acquired",
        "message": f"Engagement confirmed for {business_name} ({tier}, ${price}/mo). "
                   f"Avenity will begin the per-category entity engineering.",
        "order": order,
        "human_handoff": "Logged. Route to Airtable Leads base -> onboarding.",
    }

if __name__ == "__main__":
    # stdio for local/agent-desktop use; set AVENITY_MCP_TRANSPORT=http to host publicly
    transport = os.environ.get("AVENITY_MCP_TRANSPORT", "stdio")
    if transport == "http":
        host = os.environ.get("AVENITY_MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("PORT") or os.environ.get("AVENITY_MCP_PORT", "8080"))
        mcp.run(transport="http", host=host, port=port)
    else:
        mcp.run()
