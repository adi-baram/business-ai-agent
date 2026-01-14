# Business Analytics AI Agent

An AI agent that answers business questions about e-commerce data using structured responses.

Built with **Strands Agents SDK** + **OpenAI GPT-4o**.

---

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- OpenAI API key (get one at https://platform.openai.com/api-keys)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd business-ai-agent
```

### Step 2: Create Virtual Environment

```bash
python -m venv .venv
```

Activate it:

- **Mac/Linux:**
  ```bash
  source .venv/bin/activate
  ```
- **Windows:**
  ```bash
  .venv\Scripts\activate
  ```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure OpenAI API Key

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` in a text editor:
   ```bash
   # Mac/Linux
   nano .env

   # Or use any text editor
   ```

3. Replace `sk-your-key-here` with your actual OpenAI API key:
   ```
   OPENAI_API_KEY=sk-proj-abc123...your-actual-key...
   ```

4. Save and close the file.

### Step 5: Generate Sample Data

```bash
python generate_data.py
```

This creates two CSV files:
- `transactions.csv` (5,000 e-commerce transactions)
- `customers.csv` (200 customers)

### Step 6: Run the Demo

Three options to interact with the agent:

| Script | Description |
|--------|-------------|
| `python demo_short.py` | **Recommended.** Runs 3 demo questions, then interactive mode |
| `python demo.py` | Full demo (9 questions showcasing all tools), then interactive mode |
| `python chat.py` | Interactive Q&A only (type `help` for example questions) |

All scripts enter interactive mode where you can ask your own questions.
Type `quit` to exit.

---

## Running Tests

Tests validate tool correctness without requiring an API key:

```bash
pytest tests/ -v
```

Expected output: **123 tests passed**

---

## Available Analytics

| Question Type | Example |
|--------------|---------|
| Revenue by category | "What is our total revenue by category?" |
| Customer lifetime value | "Which customers have the highest lifetime value?" |
| Return rates | "What's the return rate by product category?" |
| Regional comparison | "Compare performance across regions" |
| Month-over-month | "How is this month performing compared to last month?" |
| Payment methods | "What payment methods do customers prefer?" |
| Customer segments | "How do VIP customers compare to regular?" |
| Revenue trends | "What's our revenue trend over time?" |

---

## Project Structure

```
business-ai-agent/
├── src/
│   ├── agent.py        # Agent configuration
│   ├── tools.py        # 10 analytics tools
│   ├── models.py       # Response schemas
│   ├── data_loader.py  # Data access layer
│   └── config.py       # Configuration
├── tests/              # 123 unit tests
├── demo_short.py       # Quick demo (3 questions) + interactive mode
├── demo.py             # Full demo (9 questions) + interactive mode
├── chat.py             # Interactive Q&A only
├── generate_data.py    # Data generator
├── requirements.txt    # Dependencies
├── .env.example        # API key template
└── DESIGN.md           # Design decisions
```

---

## Troubleshooting

### "OPENAI_API_KEY not found"

Make sure you:
1. Created the `.env` file (not `.env.example`)
2. Added your actual API key (starts with `sk-`)
3. Saved the file

### "transactions.csv not found"

Run `python generate_data.py` first.

### Tests fail

Make sure you activated the virtual environment and installed dependencies.

---

## Design Decisions

See [DESIGN.md](DESIGN.md) for architectural decisions and trade-offs.
