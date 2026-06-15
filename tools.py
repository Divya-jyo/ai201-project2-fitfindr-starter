"""
tools.py
FitFindr tools — search_listings, suggest_outfit, create_fit_card
"""

import os
from dotenv import load_dotenv
from groq import Groq
from utils.data_loader import load_listings

load_dotenv()

def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to a .env file.")
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    listings = load_listings()

    # Filter by price
    if max_price is not None:
        listings = [l for l in listings if l["price"] <= max_price]

    # Filter by size (case-insensitive)
    if size is not None:
        listings = [l for l in listings if size.upper() in l["size"].upper()]

    # Score by keyword overlap with description
    keywords = description.lower().split()

    def score(listing):
        text = (
            listing["title"].lower() + " " +
            listing["description"].lower() + " " +
            " ".join(listing["style_tags"]).lower() + " " +
            listing["category"].lower()
        )
        return sum(1 for kw in keywords if kw in text)

    listings = [(score(l), l) for l in listings]
    listings = [(s, l) for s, l in listings if s > 0]
    listings.sort(key=lambda x: x[0], reverse=True)

    return [l for _, l in listings]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    client = _get_groq_client()

    if not wardrobe.get("items"):
        prompt = f"""A user just thrifted this item:
- {new_item['title']} ({new_item['category']}, {', '.join(new_item['colors'])}, style: {', '.join(new_item['style_tags'])})

They don't have a wardrobe set up yet. Give them 1-2 general outfit ideas — 
what kinds of pieces pair well with this item, what vibe it suits, and how to wear it.
Be specific and conversational, like a stylish friend giving advice."""

    else:
        wardrobe_text = "\n".join([
            f"- {item['name']} ({item['category']}, {', '.join(item['colors'])})"
            for item in wardrobe["items"]
        ])
        prompt = f"""A user just thrifted this item:
- {new_item['title']} ({new_item['category']}, {', '.join(new_item['colors'])}, style: {', '.join(new_item['style_tags'])})

Their current wardrobe includes:
{wardrobe_text}

Suggest 1-2 complete outfit combinations using the new item and specific pieces 
from their wardrobe. Be specific — name the actual wardrobe pieces. 
Sound like a stylish friend, not a stylist writing a report."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    if not outfit or not outfit.strip():
        return "Error: Cannot generate fit card — outfit description is missing."

    client = _get_groq_client()

    prompt = f"""Write a 2-4 sentence Instagram caption for this thrifted outfit.

Item: {new_item['title']} — ${new_item['price']} from {new_item['platform']}
Outfit: {outfit}

Rules:
- Sound casual and authentic, like a real person posting their OOTD
- Mention the item name, price, and platform once each, naturally
- Capture the vibe in specific terms (don't say "amazing" or "cute")
- No hashtags
- Do NOT start with "I"

Write only the caption, nothing else."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=1.2,
    )
    return response.choices[0].message.content.strip()