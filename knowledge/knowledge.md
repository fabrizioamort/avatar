# Fabrizio Amort

Fabrizio is a software engineer with 30 years of experience in the software industry. He is passionate about software development and artificial intelligence.

## Professional Identity

**Role:** GenAI Architect  
**Employer:** TIM (Telecom Italia) — large Italian Telco  
**Experience:** 30+ years in software engineering and system architecture  
**Career arc:** Low-level systems → web platforms → cloud-native → AI architectures  
**Primary cloud:** Google Cloud Platform / Vertex AI  
**Primary language:** Python  

I operate as a bridge between business, engineering, and operations — end-to-end from requirement analysis and architectural design through evaluation, deployment, and observability. My work spans PoC to production-ready agentic systems.

**Domain expertise:** Enterprise AI platforms for large Telco organizations. I understand both the technology and the organizational dynamics: long specification cycles, multi-stakeholder alignment, regulatory constraints, legacy system integration.

---

## Key Original Ideas

**Vibe Specifying** — using LLMs to translate messy business conversations (meeting notes, transcripts) into precise, testable specifications before coding agents implement them. The insight: agents fail because we don't give them the right context, not because they can't code. Enterprise context is usually not AI-ready by default.

**Enterprise knowledge quality** — "No high-quality knowledge → no effective agents." Enterprise documentation is written for humans, inconsistent, contradictory, and outdated. AI adoption stalls because knowledge bases aren't designed for AI, not because the models aren't capable.

**Multi-model strategy** — GPT feels disciplined and precise for clear specs; Claude/Sonnet is more creative and exploratory. Enterprise should route different tasks to different models based on their behavioral strengths, not standardize on one vendor.

---

## Current Projects

| Project | Context | Status | Key page |
|---|---|---|---|
| **FAT2** | TIM POC — AI-assisted billing document verification (Fatturazione Automatizzata). 7-stage pipeline, 17 doc types, Gemini Flash/Pro, HITL, Golden Dataset eval. | Active | [projects/fat2.md](projects/fat2.md) |
| **RLM-RAG** | Recursive filesystem RAG — code-writing agent explores structured document hierarchy | Active | [projects/rlm_rag.md](projects/rlm_rag.md) |
| **RAG Evaluator** | Platform comparing 4 RAG strategies (ChromaDB, Qdrant, Neo4j, agentic) with DeepEval | Active | [projects/rag_evaluator.md](projects/rag_evaluator.md) |
| **Veritasloop** | Adversarial multi-agent news verification via dialectical debate (LangGraph) | Active | [projects/veritasloop.md](projects/veritasloop.md) |
| **agent-starter-pack** | Fork of GoogleCloudPlatform's production agent template CLI | Active | [projects/agent_starter_pack.md](projects/agent_starter_pack.md) |
| **finally** | Ed Donner course capstone — AI trading workstation built entirely by coding agents | Completed | [projects/finally_trading.md](projects/finally_trading.md) |

---

## Knowledge Map

### Solid (can explain, apply, evaluate tradeoffs confidently)

**Enterprise AI & Agentic Platforms** — this is my primary professional domain. I design enterprise AI platforms, understand the organizational dynamics, and have production experience at TIM. My "Vibe Specifying" workflow and enterprise knowledge quality insights are original contributions.

**RAG & Retrieval** — built four strategies from scratch (vector semantic, hybrid, graph, filesystem/agentic), built a full evaluation platform comparing them, implemented recursive code-writing retrieval in RLM-RAG.

**LLM Pipeline Design** — built a full 7-stage enterprise pipeline in FAT2: parser-first/LLM-fallback, partial failure resilience, YAML-driven configuration, Jinja2 prompt templates, confidence scoring, HITL escalation, cost guard, multi-format document loading.

### Learning (actively building depth)

**Agentic Patterns** — built REPL code-writing agent (RLM-RAG), debate loop (Veritasloop), multi-stage pipeline (FAT2). Know ReAct and budget-constrained execution well. Less experience with long-horizon planning (MCTS, tree-of-thought applied to tasks).

**Multi-Agent Systems** — built adversarial debate system with LangGraph (Veritasloop). Course exposure to CrewAI, AutoGen, MCP. Less experience with A2A protocol in production.

**Agent Memory & State** — built filesystem-as-memory, REPL namespace, caching strategies. Less experience with long-term persistent memory (mem0, MemGPT-style).

**Frameworks** — real production experience with LangGraph and LangChain. Course labs on OpenAI Agents SDK, CrewAI, AutoGen, MCP. ADK via agent-starter-pack fork study. Forming honest opinions on when each is right.

**Agent Evaluation** — built DeepEval-based RAG evaluation platform + Golden Dataset framework (FAT2). Gap: LLM-as-judge calibration, trajectory evaluation, eval set design beyond RAG.

**Production & MLOps** — real experience with FastAPI/WebSocket, Docker, Arize Phoenix, circuit breaker, structlog, GitHub Actions CI/CD. Certified Google Professional ML Engineer (LLMOps). Gap: OpenTelemetry from scratch, production cost tracking at scale.

### Priority Gaps

1. **Agent evaluation** — LLM-as-judge calibration, trajectory scoring, building eval sets for non-RAG agents
2. **Production observability** — OpenTelemetry + Cloud Trace from scratch (not just via scaffolding)
3. **Agent Engine internals** — session management, built-in tracing, cost model (used via templates, not directly)
4. **A2A protocol** — beyond conceptual; need to implement
5. **Cost tracking at scale** — real EUR-per-task tracking in production

---

## Certifications & Completed Learning

| Credential | Issuer | Date |
|---|---|---|
| Professional ML Engineer (LLMOps, GenAI) | Google | March 2025 |
| Professional Cloud Architect | Google | February 2025 |
| AI Agents Fundamentals | Hugging Face | March 2025 |
| Complete Agentic AI Engineering | Ed Donner / Udemy | Early 2026 |
| AI Coder: From Vibe Coder to Agentic Engineer | Ed Donner / Udemy | Early 2026 |

---

## Tech Stack (Regular Use)

**AI/LLM:** Google Gemini (Flash/Pro), Claude (Sonnet/Opus), OpenAI GPT, Vertex AI  
**Agent frameworks:** LangGraph, LangChain, ADK (via agent-starter-pack)  
**Evaluation:** DeepEval, custom Golden Dataset framework  
**Backend:** FastAPI, Python 3.11+, Pydantic, Typer  
**Document processing:** PyMuPDF, pdfplumber, pytesseract, openpyxl, python-docx  
**Vector/Graph:** ChromaDB, Qdrant, Neo4j  
**Frontend:** Streamlit (primary), React (RAG Evaluator, Veritasloop, FAT2 experiments)  
**Observability:** Arize Phoenix, structlog, Streamlit inspector (custom)  
**Infra:** Google Cloud, Docker, GitHub Actions, uv  
**Prompts:** Jinja2 templates  

---

## Learning Goals (Current)

**Competitive edge** — stay ahead of a fast-moving field. This is not gap-filling for a specific project; it's continuous investment in being one of the best GenAI architects in the enterprise space.

**Next priority reads:**
- *AI Engineering* by Chip Huyen (O'Reilly, 2025) — top priority book
- ReAct paper (Yao et al., 2022) — read the original
- Tree of Thoughts paper (Yao et al., 2023)
- DocETL paper (Shankar et al., VLDB 2025)

**Next skills to build:** see [learning/backlog.md](learning/backlog.md)

---

## People Following (Key)

Full profiles in [learning/people_to_follow.md](learning/people_to_follow.md).

Daily: Simon Willison (simonwillison.net)  
Weekly: Nate B Jones (Substack), swyx (Latent Space)  
On-demand: Hamel Husain + Shreya Shankar (evals), Jason Liu (context engineering), Jerry Liu (enterprise docs)  
Books: Chip Huyen, AI Engineering  
Research: Shunyu Yao (ReAct, Tree of Thoughts)  

---

## Contact / Profiles

- **LinkedIn:** linkedin.com/in/fabrizio-amort-0196839
- **GitHub:** github.com/fabrizioamort
- **Language:** Italian (native), English (B2.2 certified)

---