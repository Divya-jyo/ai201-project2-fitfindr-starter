# FitFindr

A multi-tool AI agent that helps users find secondhand clothing and figure out
how to wear it. The agent searches mock thrift listings, suggests outfit
combinations using the user's wardrobe, and generates a shareable fit card caption.

## How to Run

```bash
pip install -r requirements.txt
# Add your Groq API key to a .env file: GROQ_API_KEY=your_key_here
python app.py
```
Then open http://127.0.0.1:7860 in your browser.

## Tool Inventory

### search_listings(description: str, size: str | None, max_price: float | None) → list[dict]
Searches the mock listings dataset by keyword overlap with the description,
then filters by size and price. Returns a list of matching listing dicts sorted
by relevance score. Returns an empty list if nothing matches — never raises an exception.

### suggest_outfit(new_item: dict, wardrobe: dict) → str
Calls the Groq LLM to suggest 1-2 outfit combinations using the new item and
the user's existing wardrobe pieces. If the wardrobe is empty, returns general
styling advice instead of specific combinations.

### create_fit_card(outfit: str, new_item: dict) → str
Calls the Groq LLM to generate a 2-4 sentence casual Instagram-style caption
for the outfit. Uses higher temperature (1.2) so output varies each run.
Guards against empty outfit input — returns an error string instead of crashing.

## How the Planning Loop Works

The agent runs these steps in order, stopping early if search returns nothing:

1. Parse the user query with regex to extract description, size, and max_price
2. Call search_listings() — if results is empty, set session["error"] and return immediately. suggest_outfit and create_fit_card are never called with empty input.
3. Select results[0] as the top match → session["selected_item"]
4. Call suggest_outfit(selected_item, wardrobe) → session["outfit_suggestion"]
5. Call create_fit_card(outfit_suggestion, selected_item) → session["fit_card"]
6. Return the completed session

The only branch is at step 2 — if search returns nothing, the agent stops.
Otherwise all three tools always run in sequence.

## State Management

All state lives in a single session dict initialized at the start of each
run_agent() call. Each tool reads its inputs directly from the session and
writes its output back into it:

- session["parsed"] — description, size, max_price extracted from query
- session["search_results"] — full list returned by search_listings
- session["selected_item"] — results[0], passed into suggest_outfit
- session["outfit_suggestion"] — string from suggest_outfit, passed into create_fit_card
- session["fit_card"] — final caption string
- session["error"] — set only when search returns empty, None otherwise

No tool re-prompts the user or reloads data independently.

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match | Sets session["error"] = "No listings found for '...' Try a broader description, different size, or higher budget." Returns early — no further tools called. |
| suggest_outfit | Empty wardrobe | LLM is prompted for general styling advice instead of wardrobe-specific combos. Always returns a non-empty string. |
| create_fit_card | Empty outfit string | Returns "Error: Cannot generate fit card — outfit description is missing." No LLM call made. |

**Concrete example from testing:**
Running `search_listings("designer ballgown", size="XXS", max_price=5)` returns `[]`.
The agent sets session["error"] = "No listings found for 'designer ballgown' in size XXS under $5.0. Try a broader description, different size, or higher budget." and returns without calling suggest_outfit or create_fit_card.

## Spec Reflection

**One way the spec helped:** Writing the agent diagram in planning.md before
coding made the planning loop straightforward to implement — the conditional
branch at search_listings was already clearly defined, so there was no ambiguity
about when to stop early.

**One way implementation diverged:** The spec said query parsing could use the
LLM, but regex turned out to be simpler and faster for extracting size and price
patterns. The LLM would have added latency and an extra API call for something
that simple patterns handle reliably.

## AI Usage

**Instance 1 — tools.py implementation:**
I gave Claude the Tool 1, 2, and 3 spec blocks from planning.md (inputs, return
values, failure modes) and asked it to implement each function. I verified that
search_listings filtered by all three parameters and returned an empty list on
no matches before running it. For suggest_outfit I checked that both the empty
and non-empty wardrobe paths were handled. For create_fit_card I ran it three
times to confirm output varied.

**Instance 2 — agent.py planning loop:**
I gave Claude the Architecture diagram and Planning Loop section from planning.md
and asked it to implement run_agent(). I reviewed the generated code to confirm
it branched on empty search results, stored values in the session dict in order,
and never called suggest_outfit when search returned nothing.