# Cooper — PartSelect AI Assistant

Cooper is a multi-agent AI chatbot for PartSelect. It can look up appliance parts and models, provide repair guidance, and check order status. The backend is a LangGraph agent graph served via FastAPI. The frontend is a Next.js chat UI.

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- An OpenAI API key

---

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd Cooper
```

### 2. Create a Python virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your OpenAI API key

Create a `.env` file inside the `cooperMAS/` directory:

```bash
echo "OPENAI_API_KEY=sk-..." > cooperMAS/.env
```

### 5. Seed the database

The orders database needs to be populated before the backend starts:

```bash
cd cooperMAS
python database_seeder.py
cd ..
```

### 6. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

---

## Running the app

You need two terminals running simultaneously.

### Terminal 1 — Backend

```bash
source venv/bin/activate
cd cooperMAS
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

The chat UI will be available at `http://localhost:3000`.

---

## Using Cooper

Open `http://localhost:3000` in your browser. Type a message and press Enter.

Cooper can handle four types of requests:

**Part lookup**
> "Look up part PS11752778"
> "What is part WPW10321304?"

**Model lookup**
> "My WDT780SAEM1 dishwasher won't drain, what parts should I check?"
> "Look up model WRS325SDHZ"

**Repair guidance**
> "My fridge is leaking water from the bottom"
> "My dishwasher is not cleaning properly"

**Order status**
> "Check my order ORD-10042 for jones.oscar@hotmail.com"

Cooper will ask for clarification if it needs more information (e.g. a model number without a symptom). Multiple lookups can be requested in a single message.

---

## Project structure

```
Cooper/
├── requirements.txt
├── cooperMAS/
│   ├── server.py           # FastAPI server
│   ├── graph.py            # LangGraph agent graph
│   ├── cooper.py           # CLI interface
│   ├── database_seeder.py  # Seeds orders.db with sample data
│   ├── data/
│   │   ├── orders.db       # SQLite orders database
│   │   └── repair_info.txt # Repair knowledge base
│   ├── prompts/
│   │   ├── cooper_system.md
│   │   └── cooper_compiler.md
│   └── functions/
│       ├── state.py         # Shared graph state + output schema
│       ├── config.py        # LLM clients
│       ├── context.py       # Shared _fired tracker
│       ├── utils.py         # LLM response text helper
│       ├── prompts.py       # Prompt loader
│       ├── vectorstore.py   # RAG vector store (repair knowledge)
│       ├── cooper_node.py   # Entry node — intent routing
│       ├── part_node.py     # Part lookup node
│       ├── part_func.py     # PartSelect part scraper
│       ├── model_node.py    # Model lookup node
│       ├── model_func.py    # PartSelect model scraper
│       ├── repair_node.py   # RAG repair guidance node
│       ├── order_node.py    # Order lookup node
│       ├── compiler_node.py # Response synthesis node
│       └── summarize_node.py# Conversation summarisation node
└── frontend/
    └── src/app/
        ├── page.tsx         # Chat UI
        └── api/chat/
            └── route.ts     # Next.js proxy to backend
```

---

## CLI mode

You can also run Cooper directly in the terminal without the frontend:

```bash
source venv/bin/activate
cd cooperMAS
python cooper.py
```
