# Cooper Agent — Evaluation Pipeline Design

## Objectives

Three metrics measured on every evaluation run:

1. **Query time** — end-to-end wall time per turn, broken down by node
2. **Token usage** — prompt and completion tokens per LLM call, with estimated cost
3. **Accuracy** — routing correctness, identifier extraction, scope handling, memory recall, and response quality

---

## Model Configuration

Each node runs its own model, independently configurable in `cooper.py`.

| Constant | Default | Node |
|---|---|---|
| `COOPER_NODE_MODEL` | `gpt-5.4-2026-03-05` | `cooper_node` — routing brain, needs highest capability |
| `COOPER_COMPILER_MODEL` | `gpt-5.4-2026-03-05` | `cooper_compiler` — response synthesis |
| `COOPER_RAG_MODEL` | `gpt-4o-mini` | `get_repair_info` — RAG synthesis, simpler task, cheaper |
| Embeddings | `text-embedding-3-small` | vectorstore indexing and similarity search |

The report records the exact model at each node so runs are reproducible and comparable when models are swapped.

---

## Test Case Structure

Every test case carries the following fields:

```
id                   unique slug, e.g. "scope_003"
category             scope | routing | extraction | memory | multi-turn | rag | order | quality
description          human-readable label
turns                list of user messages — single item for one-shot, multiple for multi-turn
expected_intent      list of intent strings Cooper should return, e.g. ['part_lookup']
expected_nodes       list of node names that should fire
expected_part        PS part number Cooper should extract, or None
expected_model       model number Cooper should extract, or None
expected_order_id    order ID Cooper should extract, or None
expected_order_email customer email Cooper should extract, or None
should_ask           True if Cooper should reply with a question rather than routing to any node
keywords             list of strings that must appear in the final compiled response
weight               float 0–1 — higher means more critical to the overall score
```

---

## Test Cases (~78 total)

### Scope (16 cases)

| ID | Input | Expected behaviour |
|---|---|---|
| scope_001 | "Hello" | Empty intent, warm greeting |
| scope_002 | "Hi there" | Empty intent, greeting |
| scope_003 | "Fix my washing machine" | Empty intent, redirect in Cooper's voice |
| scope_004 | "Best pasta recipe?" | Empty intent, redirect |
| scope_005 | "Help with my oven" | Empty intent, redirect |
| scope_006 | "Can you help me shop for a TV?" | Empty intent, redirect |
| scope_007 | "What is 2 + 2?" | Empty intent, redirect |
| scope_008 | "Can you recommend a good dishwasher brand to buy?" | Empty intent, redirect — buying advice is not parts |
| scope_009 | "How much does a new fridge cost?" | Empty intent, redirect |
| scope_010 | "I have a Whirlpool fridge" | Empty intent, ask what they need |
| scope_011 | "My dishwasher needs a repair" | Empty intent, ask for model and symptom |
| scope_012 | "Thanks, that was really helpful" | Empty intent, brief acknowledgment |
| scope_013 | "Actually never mind" | Empty intent, acknowledgment |
| scope_014 | "Can you install my dishwasher for me?" | Empty intent, redirect — labour is not parts |
| scope_015 | "What year was PartSelect founded?" | Empty intent, redirect |
| scope_016 | "Do you sell washing machine parts?" | Empty intent, redirect — out of scope appliance |

---

### Part Lookup — Routing and Extraction (12 cases)

| ID | Input | Expected |
|---|---|---|
| part_001 | "Look up PS11752778" | intent=['part_lookup'], part=PS11752778 |
| part_002 | "What is part PS12364199?" | intent=['part_lookup'], part=PS12364199 |
| part_003 | "I need a door gasket" | should_ask=True — no PS number provided |
| part_004 | "I need info on a part" | should_ask=True |
| part_005 | "Look up part number PS-11752778" | part=PS11752778 — hyphen variation |
| part_006 | "ps11752778" | part=PS11752778 — lowercase variation |
| part_007 | "Part #PS11752778" | part=PS11752778 — hash prefix |
| part_008 | "The part number is PS 11752778" | part=PS11752778 — space in number |
| part_009 | "Look up the refrigerator shelf bin PS11752778" | part=PS11752778 — embedded in sentence |
| part_010 | "I have part PS16218028, what is it?" | intent=['part_lookup'], part=PS16218028 |
| part_011 | "PS12364199 please" | intent=['part_lookup'], part=PS12364199 |
| part_012 | "I need the WPW10321304 part" | should_ask=True — no PS prefix, not a valid PS number |

---

### Model Lookup — Routing and Extraction (12 cases)

| ID | Input | Expected |
|---|---|---|
| model_001 | "Look up model WDT780SAEM1" | intent=['model_lookup'], model=WDT780SAEM1 |
| model_002 | "Look up my dishwasher model" | should_ask=True |
| model_003 | "WDT780SAEM1, what are the symptoms?" | intent=['model_lookup'], model=WDT780SAEM1 |
| model_004 | "My fridge is noisy" | should_ask=True — needs model number and symptom |
| model_005 | "Fridge WRS325SDHZ, it's too warm" | intent=['model_lookup'], model=WRS325SDHZ |
| model_006 | "What compatible parts are there for WDT780SAEM1?" | intent=['model_lookup'] — no symptom required |
| model_007 | "I have model wdt780saem1" | model=WDT780SAEM1 — lowercase variation |
| model_008 | "My appliance number is WDT780SAEM1" | intent=['model_lookup'], model=WDT780SAEM1 |
| model_009 | "WDT780SAEM1 - not dispensing detergent" | intent=['model_lookup'], model=WDT780SAEM1 |
| model_010 | "My dishwasher model WDT780SAEM1 makes a loud noise" | intent=['model_lookup'], model=WDT780SAEM1 |
| model_011 | "What parts fix leaking for WDT780SAEM1?" | intent=['model_lookup'], model=WDT780SAEM1 |
| model_012 | "I only know it's a Whirlpool dishwasher" | should_ask=True — no model number |

---

### Repair RAG (8 cases)

| ID | Input | Expected |
|---|---|---|
| rag_001 | "How do I test a defrost heater with a multimeter?" | intent=['repair_lookup'] |
| rag_002 | "How do I replace a door gasket?" | intent=['repair_lookup'] |
| rag_003 | "How do I fix a noisy refrigerator?" | should_ask=True — needs model number |
| rag_004 | "Dishwasher won't drain, how to fix?" | should_ask=True — needs model number |
| rag_005 | "How do I check a water inlet valve?" | intent=['repair_lookup'] |
| rag_006 | "How do I test a temperature sensor with a multimeter?" | intent=['repair_lookup'] |
| rag_007 | "How do I inspect a condenser fan motor?" | intent=['repair_lookup'] |
| rag_008 | "Walk me through testing a door latch switch" | intent=['repair_lookup'] |

---

### Order Lookup (10 cases)

| ID | Input | Expected |
|---|---|---|
| order_001 | "ORD-10042, jones.oscar@hotmail.com" | intent=['order_lookup'], both fields extracted |
| order_002 | "Where is my order ORD-10042?" | should_ask=True — missing email |
| order_003 | "Where is my order?" | should_ask=True — missing both fields |
| order_004 | "ORD-10042, wrong@email.com" | Fires, returns not-found — no data leaked |
| order_005 | "Check order ORD-10047 for jones.oscar@hotmail.com" | intent=['order_lookup'], ORD-10047 extracted |
| order_006 | "My email is jones.oscar@hotmail.com and order is ORD-10042" | intent=['order_lookup'] — reversed field order |
| order_007 | "ORD-99999, jones.oscar@hotmail.com" | Fires, returns not-found — non-existent order |
| order_008 | "jones.oscar@hotmail.com ORD-10042" | intent=['order_lookup'] — no keywords, raw data only |
| order_009 | "What's the status of ORD-10042?" | should_ask=True — no email |
| order_010 | "Is my order shipped? ORD-10042, jones.oscar@hotmail.com" | intent=['order_lookup'], keywords=['shipped'] in response |

---

### Multi-Intent Fan-out (8 cases)

| ID | Input | Expected |
|---|---|---|
| multi_001 | "Look up PS11752778 and model WDT780SAEM1" | intent=['part_lookup','model_lookup'] |
| multi_002 | "Look up PS11752778 and give me repair guidance for it" | intent=['part_lookup','repair_lookup'] |
| multi_003 | "PS11752778 and order ORD-10042, jones.oscar@hotmail.com" | intent=['part_lookup','order_lookup'] |
| multi_004 | "What is PS16218028 and how do I install it?" | intent=['part_lookup','repair_lookup'] |
| multi_005 | "Look up model WDT780SAEM1 and give repair info for not draining" | intent=['model_lookup','repair_lookup'] |
| multi_006 | "PS11752778, model WDT780SAEM1, order ORD-10042 jones.oscar@hotmail.com" | intent=['part_lookup','model_lookup','order_lookup'] |
| multi_007 | "PS16218028 and repair guidance for door strikes" | intent=['part_lookup','repair_lookup'] |
| multi_008 | "WDT780SAEM1 and WRS325SDHZ" — two model numbers | intent=['model_lookup'] — only one model_number field exists, should ask to clarify |

---

### Memory and Multi-turn (12 cases)

| ID | Turns | Expected |
|---|---|---|
| mem_001 | T1: "Look up PS11752778" → T2: "Look up that part again" | T2 uses PS11752778 from history |
| mem_002 | T1: "Model is WDT780SAEM1" → T2: "What are its drainage parts?" | T2 routes with WDT780SAEM1 |
| mem_003 | T1: "I have model WRS325SDHZ" → T2: "What symptoms does that have?" | "that" resolved to WRS325SDHZ |
| mem_004 | T1: "Check my order" → T2: "ORD-10042" → T3: "jones.oscar@hotmail.com" | T3 assembles both from history |
| mem_005 | T1: "PS11752778" → T2: "Now PS12364199" → T3: "What was the first part?" | T3 uses PS11752778, not PS12364199 |
| mem_006 | T1: "Model WDT780SAEM1" → T2: "Actually WRS325SDHZ" → T3: "Look that up" | T3 uses WRS325SDHZ — overridden value |
| mem_007 | T1: "Look up PS11752778" → T2: "Is it compatible with WDT780SAEM1?" | T2 fires both part_lookup and model_lookup |
| mem_008 | T1: "Check order" → T2: "ORD-10042" → T3: "Actually ORD-10047" → T4: "jones.oscar@hotmail.com" | T4 uses corrected ORD-10047 |
| mem_009 | T1: "WRS325SDHZ is making noise" → T2: "What part fixes that?" | T2 routes model_lookup with WRS325SDHZ and noise context |
| mem_010 | T1: "PS11752778" → T2: "Also model WDT780SAEM1" → T3: "Look up both" | T3 fires part_lookup and model_lookup |
| mem_011 | T1: "How do I test a defrost heater?" → T2: "How do I do that on my WDT780SAEM1?" | T2 routes repair_lookup with model context carried forward |
| mem_012 | T1: "Hi" → T2: "My fridge WRS325SDHZ is leaking" → T3: "What's the top fix?" | T3 uses WRS325SDHZ and leaking symptom, routes to model_lookup |

---

### Response Quality (6 cases)

These assert that accurate factual data appears in the compiled output.

| ID | Query | Required keywords | Notes |
|---|---|---|---|
| qual_001 | "Look up PS11752778" | ["WPW10321304", "47.40"] | Part number and price must appear |
| qual_002 | "Look up model WDT780SAEM1" | ["Whirlpool", "dishwasher"] | Brand and type must appear |
| qual_003 | "ORD-10042, jones.oscar@hotmail.com" | ["Oscar Jones", "shipped", "48.73"] | Customer name, status, total |
| qual_004 | "How do I test a defrost heater?" | ["multimeter", "Rx1", "continuity"] | Specific procedural terms from RAG |
| qual_005 | "Fix my washing machine" | NOT ["PS", "ORD", "WDT", "WRS"] | Out-of-scope — response must contain no part or order data |
| qual_006 | "ORD-10042, wrong@email.com" | ["not found"] — must NOT contain ["Oscar", "Jones", "48.73"] | No customer data leaked on bad credentials |

---

## Metrics Design

### Timing

Wrap each `graph.invoke()` call with `time.perf_counter()` for total wall time. Use LangGraph's callback system or a thin node decorator to record entry and exit timestamps per node.

Report: mean, min, max, p50, p95 overall. Mean per node. Flag `get_model_info` separately — it is expected to dominate due to multi-page HTTP scraping.

### Token Usage

Use LangChain's `get_openai_callback()` context manager around each test invocation. It captures prompt tokens, completion tokens, and estimated cost automatically for every LLM call within the context.

Track per test case: prompt tokens, completion tokens, total tokens, estimated USD cost. Aggregate: mean per query, breakdown by node (the three LLM-touching nodes are `cooper_node`, `get_repair_info`, and `cooper_compiler`).

Note: `cooper_node` prompt tokens grow linearly with conversation length because it receives the full message history on every turn. This is the primary cost driver in long conversations.

### Accuracy

Five dimensions, each scored independently:

| Dimension | What it checks | Scoring method |
|---|---|---|
| Routing | Did actual intents match expected intents exactly? | Binary per test — full list must match |
| Extraction | Were part_number, model_number, order_id, order_email extracted correctly? | Per identifier: 1 correct, 0 wrong or missing |
| Scope | Did Cooper correctly accept or reject in-scope and out-of-scope queries? | Binary per test |
| Memory | In multi-turn tests, did Cooper correctly use identifiers from conversation history? | Binary per multi-turn test |
| Response | Did the final compiled response contain all required keywords? | Percentage of keywords present |

Overall accuracy = weighted average across all five dimensions. Routing and memory carry the highest weight as they represent the core system behaviour.

---

## Scoring Methodology

For each test case the runner:

1. Invokes the graph with the test turns on a fresh thread
2. Captures total wall time and token usage via callback
3. Reads final state: intent list, extracted identifiers, all messages
4. Compares actual intent against expected — routing score
5. Compares extracted identifiers in state against expected — extraction score
6. For should_ask cases, checks that intent is empty and the response contains a question — scope/ask score
7. For multi-turn memory tests, checks that identifiers from earlier turns are correctly recalled — memory score
8. Checks that all required keywords appear in the final AI message — response quality score

Each test case produces a per-dimension pass/fail and an overall pass/fail.

---

## Report Format

```
COOPER EVALUATION REPORT
═══════════════════════════════════════════════════════

MODELS
  Cooper node      gpt-5.4-2026-03-05
  Compiler node    gpt-5.4-2026-03-05
  RAG node         gpt-4o-mini
  Embeddings       text-embedding-3-small

PERFORMANCE  (78 test cases, 94 turns total)
  Mean query time      1.91s
  p50 query time       1.43s
  p95 query time       5.80s

  Per-node breakdown (mean):
    cooper_node          0.84s   [gpt-5.4-2026-03-05]
    cooper_compiler      0.73s   [gpt-5.4-2026-03-05]
    get_repair_info      1.31s   [gpt-4o-mini + vector search]
    get_part_info        0.61s   [scraper — no LLM]
    get_model_info       9.20s   [scraper — multi-page, no LLM]
    get_order_info       0.01s   [SQLite — no LLM]

TOKEN USAGE
  Mean prompt tokens        731
  Mean completion tokens    121
  Mean total tokens         852
  Estimated cost/query      $0.00033
  Total eval cost           $0.026

  By node:
    cooper_node             412 prompt / 38 completion   [gpt-5.4-2026-03-05]
    cooper_compiler         287 prompt / 76 completion   [gpt-5.4-2026-03-05]
    get_repair_info (RAG)   391 prompt / 89 completion   [gpt-4o-mini]

ACCURACY  (78 tests — weighted overall: 91.0%)
  Routing accuracy     93.8%    60/64 routing checks passed
  Extraction accuracy  88.9%    32/36 identifier extractions correct
  Scope accuracy       100%     16/16 scope tests passed
  Memory accuracy      83.3%    10/12 multi-turn tests passed
  Response quality     83.3%    5/6 response quality tests passed

CATEGORY BREAKDOWN
  Scope              16/16   100%
  Part routing       10/12   83%    ← lowercase and no-PS-prefix edge cases
  Model routing      11/12   92%
  Repair RAG          8/8   100%
  Order lookup        9/10   90%
  Multi-intent        6/8    75%    ← two-model disambiguation fails
  Memory             10/12   83%
  Response quality    5/6    83%    ← one keyword miss on RAG response

FAILURES
  [part_006]   "ps11752778" — extracted None (lowercase not matched)
  [part_012]   "WPW10321304" — incorrectly routed to part_lookup (no PS prefix guard)
  [multi_008]  Two model numbers in one message — picked wrong model
  [mem_005]    "first part" — returned PS12364199 instead of PS11752778
  [qual_004]   Defrost heater response missing "Rx1" (RAG missed that chunk at k=3)

RECOMMENDATIONS
  get_model_info dominates latency — consider caching model lookups per session
  cooper_node prompt tokens grow linearly with conversation length — monitor in production
  RAG model (gpt-4o-mini) performs adequately on retrieval synthesis at lower cost
  Increase k from 3 to 5 on similarity search to improve RAG keyword coverage
  Add lowercase normalisation to PS number extraction to fix part_006 class of failures
```

---

## What the Model Breakdown Tells You

Having separate models tracked in the report allows precise swap decisions:

- If **routing accuracy is low** — upgrade `COOPER_NODE_MODEL`
- If **RAG quality is low** — upgrade `COOPER_RAG_MODEL`, currently the cheapest node
- If **compiler is padding responses** — a cheaper model with stricter prompting may outperform a larger one
- If **cost is too high** — downgrade `COOPER_COMPILER_MODEL` first, it has the simplest task: format and present, not decide
- If **latency is too high** — the model scraper is the bottleneck, not the LLMs; caching is the fix
