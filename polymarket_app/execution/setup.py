#!/usr/bin/env python3
"""
Derive Polymarket API credentials. Run once and save output to .env.

Usage:
    python3 -m polymarket_app.execution.setup
"""
import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


def main() -> None:
    from dotenv import load_dotenv
    load_dotenv()
    key = os.environ.get("POLYMARKET_PRIVATE_KEY")
    funder = os.environ.get("POLYMARKET_FUNDER")
    if not key or not funder:
        print("Set POLYMARKET_PRIVATE_KEY and POLYMARKET_FUNDER in .env first.")
        sys.exit(1)
    try:
        from py_clob_client.client import ClobClient
    except ImportError:
        print("Run: pip install py-clob-client")
        sys.exit(1)
    client = ClobClient(
        "https://clob.polymarket.com",
        chain_id=137,
        key=key,
        signature_type=int(os.environ.get("POLYMARKET_SIGNATURE_TYPE", "1")),
        funder=funder,
    )
    creds = client.create_or_derive_api_creds()
    print("Add these to your .env file:")
    print(f"POLYMARKET_API_KEY={creds.api_key}")
    print(f"POLYMARKET_API_SECRET={creds.api_secret}")
    print(f"POLYMARKET_API_PASSPHRASE={creds.api_passphrase}")


if __name__ == "__main__":
    main()