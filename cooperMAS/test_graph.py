"""
Thorough test suite for the Cooper graph.
Run from cooperMAS/:  python test_graph.py
"""
import sys, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from graph import graph
from nodes import _fired
from nodes.summarize import SUMMARIZE_AFTER, KEEP_RECENT

# ── helpers ──────────────────────────────────────────────────────────────────

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"

def tid():
    return str(uuid.uuid4())

def invoke(thread_id, message):
    _fired.clear()
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke({"messages": [{"role": "user", "content": message}]}, config=config)

def last_reply(result):
    last_human = max(i for i, m in enumerate(result["messages"]) if m.type == "human")
    msgs = [m for m in result["messages"][last_human + 1:] if m.type == "ai"]
    return msgs[-1].content if msgs else ""

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{status}] {label}{suffix}")
    return condition

# ── Test 1: Chat path (no specialist nodes) ───────────────────────────────────

print("\n=== 1. Chat path — greeting ===")
t = tid()
r = invoke(t, "hello")
reply = last_reply(r)
check("Returns a reply",        bool(reply))
check("Intent is empty",        r["intent"] == [])
check("No specialist nodes ran", _fired == [])
check("summary is None",        r.get("summary") is None)

# ── Test 2: Part lookup ────────────────────────────────────────────────────────

print("\n=== 2. Part lookup ===")
t = tid()
r = invoke(t, "Can you look up part PS11752778?")
reply = last_reply(r)
check("Returns a reply",         bool(reply))
check("part_lookup intent",      "part_lookup" in r["intent"])
check("[PART] node fired",       "[PART]" in _fired)
check("part_number in state",    r.get("part_number") == "PS11752778")
check("part_info cleared",       r.get("part_info") is None)

# ── Test 3: Entity injection — implicit follow-up ─────────────────────────────

print("\n=== 3. Entity injection — implicit follow-up ===")
# Same thread as test 2; part_number is in state from last turn.
# The LLM should answer directly from context (price is already in the reply),
# NOT re-trigger the lookup — that would be wasteful.
r2 = invoke(t, "What was the price of that part?")
reply2 = last_reply(r2)
check("Returns a reply",              bool(reply2))
check("Reply contains the price",     "47.40" in reply2,
      f"reply={reply2[:80]}")
check("Answered from context (no re-lookup)", r2["intent"] == [],
      f"intent={r2['intent']}")
check("part_number preserved in state", r2.get("part_number") == "PS11752778")

# ── Test 4: Model lookup ───────────────────────────────────────────────────────

print("\n=== 4. Model lookup ===")
t = tid()
r = invoke(t, "Tell me about model WDT780SAEM1")
check("model_lookup intent",     "model_lookup" in r["intent"])
check("[MODEL] node fired",      "[MODEL]" in _fired)
check("model_number in state",   r.get("model_number") == "WDT780SAEM1")
check("model_info cleared",      r.get("model_info") is None)

# ── Test 5: Order lookup ───────────────────────────────────────────────────────

print("\n=== 5. Order lookup ===")
t = tid()
r = invoke(t, "What's the status of order ORD-10042? My email is jones.oscar@hotmail.com")
reply = last_reply(r)
check("order_lookup intent",     "order_lookup" in r["intent"])
check("[ORDER] node fired",      "[ORDER]" in _fired)
check("order_id in state",       r.get("order_id") == "ORD-10042")
check("order_email in state",    r.get("order_email") == "jones.oscar@hotmail.com")
check("reply mentions Oscar",    "Oscar" in reply or "ORD-10042" in reply, f"reply={reply[:80]}")

# ── Test 6: Guard — part intent without part number ───────────────────────────

print("\n=== 6. Guard — vague part question (no PS number) ===")
t = tid()
r = invoke(t, "Can you look up a part for me?")
check("part_lookup stripped",    "part_lookup" not in r["intent"],
      f"intent={r['intent']}, part_number={r.get('part_number')}")

# ── Test 7: Summarization triggers at threshold ───────────────────────────────

print(f"\n=== 7. Summarization — fires after {SUMMARIZE_AFTER} messages ===")
t = tid()
# Fill up to just below threshold with simple chat turns
for i in range(SUMMARIZE_AFTER // 2):
    r = invoke(t, f"Hello, this is filler message number {i + 1}")

msg_count_before = len(r["messages"])
summary_before   = r.get("summary")
check("No summary yet",          summary_before is None,
      f"msg_count={msg_count_before}")

# One more turn pushes us over
r = invoke(t, "Hello again, final filler")
summary_after   = r.get("summary")
msg_count_after = len(r["messages"])
check("Summary now populated",   bool(summary_after),
      f"summary={str(summary_after)[:80]}")
check(f"Messages trimmed to ≤{KEEP_RECENT + 2}",
      msg_count_after <= KEEP_RECENT + 2,
      f"msg_count={msg_count_after}")

# ── Test 8: Conversation continues correctly after summarization ───────────────

print("\n=== 8. Post-summarization — context still works ===")
# Continue the thread from test 7 (which has a summary now)
r = invoke(t, "Can you look up part PS11752778?")
check("Lookup works after summary", "part_lookup" in r["intent"],
      f"intent={r['intent']}")
check("part_number extracted",      r.get("part_number") == "PS11752778")

r2 = invoke(t, "And what was the price again?")
reply_followup = last_reply(r2)
check("Returns a reply post-summary",         bool(reply_followup))
check("Reply contains the price",             "47.40" in reply_followup,
      f"reply={reply_followup[:80]}")
check("part_number still in state",           r2.get("part_number") == "PS11752778",
      f"part_number={r2.get('part_number')}")

# ── Test 9: Summary accumulates (second summarization fold) ───────────────────

print("\n=== 9. Summary folds — second summarization incorporates first ===")
for i in range(SUMMARIZE_AFTER // 2 + 1):
    r = invoke(t, f"Another filler {i}")

second_summary = r.get("summary")
check("Second summary exists",   bool(second_summary))
check("Second summary is longer or different from first",
      second_summary != summary_after,
      f"len={len(second_summary or '')}")

# ── Done ──────────────────────────────────────────────────────────────────────
print()
