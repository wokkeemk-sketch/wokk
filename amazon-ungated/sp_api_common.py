"""Shared SP-API credential loading and restriction-check helper."""
import os
import sys

from dotenv import load_dotenv
from sp_api.api import ListingsRestrictions
from sp_api.base import SellingApiException

load_dotenv()

REQUIRED_ENV_VARS = [
    "SP_API_REFRESH_TOKEN",
    "SP_API_LWA_APP_ID",
    "SP_API_LWA_CLIENT_SECRET",
    "SP_API_SELLER_ID",
]


def build_credentials() -> dict:
    missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
    if missing:
        sys.exit(
            "Missing required environment variables: "
            + ", ".join(missing)
            + "\nCopy .env.example to .env and fill in your SP-API credentials."
        )
    return {
        "refresh_token": os.environ["SP_API_REFRESH_TOKEN"],
        "lwa_app_id": os.environ["SP_API_LWA_APP_ID"],
        "lwa_client_secret": os.environ["SP_API_LWA_CLIENT_SECRET"],
    }


def check_asin_restriction(client: ListingsRestrictions, asin: str, seller_id: str,
                            condition_type: str) -> dict:
    try:
        response = client.get_listings_restrictions(
            asin=asin,
            sellerId=seller_id,
            conditionType=condition_type,
        )
        restrictions = response.payload.get("restrictions", [])
        if not restrictions:
            return {"asin": asin, "restricted": False, "reasons": "", "error": ""}

        reason_texts = []
        for r in restrictions:
            for reason in r.get("reasons", []):
                message = reason.get("message", reason.get("reasonCode", ""))
                reason_texts.append(message)
        return {
            "asin": asin,
            "restricted": True,
            "reasons": " | ".join(reason_texts),
            "error": "",
        }
    except SellingApiException as e:
        return {"asin": asin, "restricted": "unknown", "reasons": "", "error": str(e)}
