# FitFindr — planning.md

> Complete this document before writing any implementation code.

---

## Tools

### Tool 1: search_listings

**What it does:**
Searches the mock listings dataset for secondhand items matching the user's
description, optional size, and optional price ceiling. Returns a ranked list
of matching items sorted by relevance.

**Input parameters:**
- `description` (str): Keywords describing what the user wants (e.g. "vintage graphic tee")
- `size` (str | None): Size to filter by (e.g. "M", "W30 L30"), or None to skip size filtering
- `max_price` (float | None): Maximum price inclusive (e.g. 30.0), or None to skip price filtering

**What it returns:**
A list of matching listing dicts, sorted by relevance score (highest first).
Each dict contains: id, title, description, category, style_tags (list),
size, condition, price (float), colors (list), brand, platform.
Returns an empty list if nothing matches — never raises an exception.

**What happens if it fails or returns nothing:**
Agent sets session["error"] = "No listings found for '[description]' in size
[size] under $[max_price]. Try removing the size filter or raising your budget."
Then returns the session immediately — does NOT call suggest_outfit or create_fit_card.

---

### Tool 2: suggest_outfit

**What it does:**
Given a thrifted item and the user's wardrobe, calls the LLM to suggest
1-2 complete outfit combinations using the new item and existing wardrobe pieces.

**Input parameters:**
- `new_item` (dict): A listing dict (the item the user is considering buying)
- `wardrobe` (dict): A wardrobe dict with an 'items' key containing a list of
  wardrobe item dicts. May be empty.

**What it returns:**
A non-empty string with outfit suggestions. If wardrobe is empty, returns
general styling advice for the item instead of specific combinations.

**What happens if it fails or returns nothing:**
If wardrobe['items'] is empty, the LLM is prompted for general styling advice
(what styles pair well, what vibe it suits) rather than crashing or returning
an empty string.

---

### Tool 3: create_fit_card

**What it does:**
Generates a short, casual, shareable Instagram/TikTok-style caption for the
outfit. Sounds like a real OOTD post — not a product description.

**Input parameters:**
- `outfit` (str): The outfit suggestion string from suggest_outfit()
- `new_item` (dict): The listing dict for the thrifted item

**What it returns:**
A 2-4 sentence caption string that mentions the item name, price, and platform
naturally. Varies each time due to higher LLM temperature. If outfit is empty,
returns a descriptive error message string instead of crashing.

**What happens if it fails or returns nothing:**
If outfit is empty or whitespace-only, returns:
"Error: Cannot generate fit card — outfit description is missing."

---

## Planning Loop

The agent runs these steps in order, stopping early if any step fails:

1. Parse the user's query using the LLM to extract description, size, and max_price.
   Store in session["parsed"].

2. Call search_listings(description, size, max_price).
   Store results in session["search_results"].
   IF results is empty → set session["error"] and return early.
   Do NOT proceed to step 3.

3. Select results[0] as the top match.
   Store in session["selected_item"].

4. Call suggest_outfit(selected_item, wardrobe).
   Store result in session["outfit_suggestion"].

5. Call create_fit_card(outfit_suggestion, selected_item).
   Store result in session["fit_card"].

6. Return the completed session.

The agent never calls suggest_outfit or create_fit_card if search_listings
returned empty. That is the only branch — otherwise all three tools always run.

---

## State Management

All state lives in a single session dict initialized by _new_session().
Fields and when they are set:

- session["query"] — set at start, never changes
- session["parsed"] — set after query parsing (step 2)
- session["search_results"] — set after search_listings (step 3)
- session["selected_item"] — set to search_results[0] (step 4)
- session["wardrobe"] — passed in at start, used in suggest_outfit
- session["outfit_suggestion"] — set after suggest_outfit (step 5)
- session["fit_card"] — set after create_fit_card (step 6)
- session["error"] — set only when search_listings returns empty; None otherwise

Each tool receives its inputs directly from the session dict. No tool
re-prompts the user or re-loads data independently.

---

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Sets session["error"] = "No listings found for '[query]'. Try a broader description, different size, or higher budget." Returns session early. |
| suggest_outfit | Wardrobe is empty | Calls LLM with prompt for general styling advice instead of wardrobe-specific combos. Returns useful string either way. |
| create_fit_card | Outfit input is empty or whitespace | Returns "Error: Cannot generate fit card — outfit description is missing." Does not call LLM. |

---

## Architecture
User query

│

▼

Planning Loop (run_agent)

│

├─ Step 1: Parse query → session["parsed"] = {description, size, max_price}

│

├─► search_listings(description, size, max_price)

│       │

│       ├── results = [] ──► session["error"] = "No listings found..." → RETURN EARLY

│       │

│       └── results = [item, ...] ──► session["selected_item"] = results[0]

│

├─► suggest_outfit(selected_item, wardrobe)

│       │

│       ├── wardrobe empty → LLM gives general styling advice

│       │

│       └── wardrobe has items → LLM suggests specific combos

│               │

│               └──► session["outfit_suggestion"] = "..."

│

└─► create_fit_card(outfit_suggestion, selected_item)

│

├── outfit empty → return error string

│

└── outfit valid → LLM generates caption

│

└──► session["fit_card"] = "..."

│

▼

Return session
---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

For search_listings: Give Claude the Tool 1 spec (inputs, return value, failure
mode) and ask it to implement the function using load_listings() from data_loader.
Verify: check it filters by all 3 params, handles empty results, returns list of dicts.
Test with 3 queries before trusting.

For suggest_outfit: Give Claude the Tool 2 spec and ask it to implement using
Groq llama-3.3-70b-versatile. Verify: test with example wardrobe AND empty wardrobe.
Both must return a non-empty string.

For create_fit_card: Give Claude the Tool 3 spec. Verify: run 3 times on same
input and confirm outputs differ. Test with empty outfit string — must return
error message, not crash.

**Milestone 4 — Planning loop and state management:**

Give Claude the Architecture diagram and Planning Loop section. Ask it to implement
run_agent() in agent.py. Verify: confirm it branches on empty search results,
confirm session fields are populated in order, confirm suggest_outfit is never
called when search returns nothing.

---

## A Complete Interaction (Step by Step)

**Example user query:** "I'm looking for a vintage graphic tee under $30, size M"

**Step 1:**
Agent parses the query → description="vintage graphic tee", size="M", max_price=30.0
Calls search_listings("vintage graphic tee", size="M", max_price=30.0)
Returns 2 matches. Top result: "Faded Band Tee — $22, Depop, Good condition"
session["selected_item"] = that listing dict

**Step 2:**
Calls suggest_outfit(selected_item=<band tee dict>, wardrobe=<example wardrobe>)
LLM sees the tee + wardrobe items (baggy jeans, combat boots, denim jacket etc.)
Returns: "Pair with your baggy dark wash jeans and black combat boots for a 90s
grunge look. Layer the vintage denim jacket on top and leave it open."
session["outfit_suggestion"] = that string

**Step 3:**
Calls create_fit_card(outfit=<suggestion string>, new_item=<band tee dict>)
LLM generates a casual caption.
session["fit_card"] = "thrifted this faded band tee off depop for $22 and it was
made for my baggy jeans 🖤 grunge era loading, full look in stories"

**Final output to user:**
- Search result panel: "Faded Band Tee — $22, Depop, Good condition"
- Outfit suggestion panel: "Pair with your baggy dark wash jeans and black combat boots..."
- Fit card panel: "thrifted this faded band tee off depop for $22..."