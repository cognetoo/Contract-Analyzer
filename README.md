Overview

Contract Analyzer is an agentic AI system that analyzes legal contracts using a Planner–Executor–Reflector architecture, augmented with retrieval-augmented generation (RAG), tool calling, and long-term vector memory.

Unlike traditional LLM-based summarizers, this system:

Breaks down contract analysis into structured steps

Uses deterministic tools for critical legal logic

Reflects on its own output to identify missing or weak analysis

Improves over time using semantic memory

This project demonstrates real-world agentic AI design, not just prompt-based automation.

*Key Features*

--Planner–Executor–Reflector Agent Loop

--RAG-based Contract Retrieval

--Tool-Augmented Execution

--Long-Term Vector Memory (FAISS)

--Self-Reflection & Iterative Improvement

--Legal Risk Scoring & Clause Classification

System Architecture
User Query
   ↓
Planner Agent
   ↓
Executor Agent ──→ Tool Calls (Risk, Dates, Clauses)
   ↓
Reflector Agent
   ↓
Memory Update (Vector Store)
   ↺ (Iterative Loop)


The system continues iterating until:

The contract is fully analyzed, or

A maximum iteration limit is reached

Project Structure
CONTRACT-ANALYZER/
│
├── core/
│   ├── run_agent.py        # Agent loop orchestration
│   ├── state.py            # Shared agent state
│
├── agents/
│   ├── planner.py          # Task decomposition & planning
│   ├── executor.py         # Step execution & tool calling
│   ├── reflector.py        # Self-evaluation & feedback
│
├── memory/
│   └── vector_memory.py    # FAISS-based long-term memory
│
├── rag/
│   ├── contract_store.py   # Contract data source
│   └── rag.py              # Retrieval logic
│
├── tools/
│   ├── clause_classifier.py
│   ├── date_extractor.py
│   └── risk_calculator.py
│
├── llm.py                  # LLM interface (Gemini/OpenAI ready)
├── config.py               # Global configuration
├── main.py                 # Entry point
├── requirements.txt
├── README.md

Agent Roles Explained
1.Planner Agent

Breaks the user query into clear, actionable steps

Avoids repeating completed or weak steps

Uses past feedback and memory to improve planning

2.Executor Agent

Executes one step at a time

Decides whether a tool call is required

Uses RAG context + tools for accurate outputs

Handles failures and retries safely

3.Reflector Agent

Evaluates whether the contract analysis is complete

Identifies missing clauses, weak explanations, or risk gaps

Generates feedback for the next planning iteration

Decides whether to store knowledge in memory

Tooling Layer

The executor uses deterministic tools to prevent hallucinations:

Tool	Purpose
Clause Classifier	Identifies contract clause types
Date Extractor	Finds deadlines, terms, expiry dates
Risk Calculator	Scores legal and compliance risk

Tools are invoked only when needed, based on LLM reasoning.

Memory System

Uses FAISS vector storage

Stores summarized insights from completed analyses

Retrieved memory influences future planning and reflection

Enables the system to improve across multiple contracts

Why This Project Is Resume-Worthy

✔ Demonstrates agentic reasoning, not prompt engineering
✔ Uses stateful AI design
✔ Separates planning, execution, and evaluation
✔ Combines LLMs with deterministic tools
✔ Applies directly to legal tech, enterprise AI, and automation

Tech Stack

Python

Gemini / OpenAI (pluggable LLM backend)

FAISS

Sentence Transformers

Agentic Architecture (custom implementation)

How to Run
# Create environment
conda create -p venv python=3.10
conda activate ./venv

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env

# Run the analyzer
python main.py

Future Improvements

Clause-level chunking with metadata

Multi-document contract comparison

UI for visual risk breakdown

Streaming execution traces

Confidence scoring per clause

## Author

Tarun S  
GitHub: https://github.com/cognetoo 
Focus: Agentic AI, LLM Systems, RAG, Tool-Augmented Agents
