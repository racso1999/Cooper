# Cooper — PartSelect AI Assistant

Cooper is a multi-agent AI chatbot for PartSelect, handling appliance part lookups, model diagnostics, repair guidance, and order status.

---

## Running Cooper

### Step 1 — Install Docker Desktop

Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/) for your operating system. Once installed, open it and wait until the Docker icon in your menu bar (Mac) or taskbar (Windows) shows it is running.

### Step 2 — Download this repository

Click the green **Code** button on GitHub and select **Download ZIP**. Unzip the folder somewhere on your computer.

Alternatively, if you have Git installed:

```bash
git clone <repo-url>
cd Cooper
```

### Step 3 — Add your API key

Inside the project folder, create a file called `.env` (note the dot at the start) and add your OpenAI API key:

```
OPENAI_API_KEY=sk-...
```

You can get an API key from [platform.openai.com](https://platform.openai.com/api-keys).

### Step 4 — Start the app

Open a terminal, navigate to the project folder, and run:

```bash
docker compose up --build
```

The first time this runs it will take a few minutes to download and build everything. You will see logs scrolling — wait until you see:

```
✓ Ready in ...ms
```

### Step 5 — Open Cooper

Go to **http://localhost:3000** in your browser.

---

To stop Cooper, press `Ctrl+C` in the terminal, then run:

```bash
docker compose down
```

Next time you want to start it again, just run `docker compose up` (no `--build` needed).

---

## Local Setup (without Docker)

**Requirements:** Python 3.11+, Node.js 18+, OpenAI API key.

```bash
# 1. Install Python dependencies
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Add your API keys
cat > cooperMAS/.env << EOF
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...        # optional, only needed for Gemini models
EOF

# 3. Seed the database
python cooperMAS/database_seeder.py

# 4. Install frontend dependencies
cd frontend && npm install && cd ..
```

---

## Running

Open two terminals:

```bash
# Terminal 1 — backend
source venv/bin/activate && cd cooperMAS
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

```bash
# Terminal 2 — frontend
cd frontend && npm run dev
```

Open `http://localhost:3000`.

---

## CLI mode

```bash
source venv/bin/activate && cd cooperMAS
python cooper.py
```
