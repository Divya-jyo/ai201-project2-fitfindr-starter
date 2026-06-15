"""
agent.py
FitFindr planning loop.
"""

import os
import re
from dotenv import load_dotenv
from groq import Groq
from tools import search_listings, suggest_outfit, create_fit_card

load_dotenv()


def _new_session(query: str, wardrobe: dict) -> dict:
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
    }


def _parse_query(query: str) -> dict:
    """Use simple regex to extract description, size, and max_price from query."""
    # Extract price (e.g. "under $30" or "$30")
    price_match = re.search(r'\$(\d+(?:\.\d+)?)', query)
    max_price = float(price_match.group(1)) if price_match else None

    # Extract size (e.g. "size M", "size XL", "size W30")
    size_match = re.search(r'\bsize\s+([A-Z0-9/]+)\b', query, re.IGNORECASE)
    size = size_match.group(1).upper() if size_match else None

    # Remove price and size mentions from description
    description = query
    description = re.sub(r'under\s+\$\d+(?:\.\d+)?', '', description, flags=re.IGNORECASE)
    description = re.sub(r'\$\d+(?:\.\d+)?', '', description)
    description = re.sub(r'\bsize\s+[A-Z0-9/]+\b', '', description, flags=re.IGNORECASE)
    description = re.sub(r"\bI'm looking for\b|\blooking for\b|\bfind me\b", '', description, flags=re.IGNORECASE)
    description = ' '.join(description.split()).strip()

    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


def run_agent(query: str, wardrobe: dict) -> dict:
    # Step 1: Initialize session
    session = _new_session(query, wardrobe)

    # Step 2: Parse query
    parsed = _parse_query(query)
    session["parsed"] = parsed

    # Step 3: Search listings
    results = search_listings(
        description=parsed["description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
    )
    session["search_results"] = results

    # If no results — set error and return early
    if not results:
        size_info = f" in size {parsed['size']}" if parsed["size"] else ""
        price_info = f" under ${parsed['max_price']}" if parsed["max_price"] else ""
        session["error"] = (
            f"No listings found for '{parsed['description']}'"
            f"{size_info}{price_info}. "
            f"Try a broader description, different size, or higher budget."
        )
        return session

    # Step 4: Select top result
    session["selected_item"] = results[0]

    # Step 5: Suggest outfit
    session["outfit_suggestion"] = suggest_outfit(
        new_item=session["selected_item"],
        wardrobe=wardrobe,
    )

    # Step 6: Create fit card
    session["fit_card"] = create_fit_card(
        outfit=session["outfit_suggestion"],
        new_item=session["selected_item"],
    )

    # Step 7: Return session
    return session


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")