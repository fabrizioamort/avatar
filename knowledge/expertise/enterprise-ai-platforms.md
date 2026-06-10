---
title: Enterprise AI and Agentic Platforms
category: expertise
tags:
  - enterprise-ai
  - agentic-platforms
  - telco
  - llmops
  - governance
priority: 0
updated: 2026-06-02
---

# Enterprise AI and Agentic Platforms

## Overview

This is my primary professional domain. I design and deliver enterprise AI platforms on Google Cloud for large organizations, particularly in Telco. The core challenge is rarely just technical. It is the gap between what AI can do and what an enterprise can actually adopt.

Two beliefs anchor my work here. First, no high-quality knowledge means no effective agents. Second, the bottleneck is specifying, not coding. Both are covered in more depth in my ideas on enterprise knowledge quality and Vibe Specifying.

## Platform Architecture

I think of an enterprise AI platform in layers: foundation models, an orchestration layer, an agent layer, and a governance layer. The governance layer is not optional in regulated environments. Around that, the design questions that actually matter in practice are:

- Multi-agent for enterprise: routing, specialization, human-in-the-loop, and escalation
- Model selection strategy: different models for different task types, because GPT, Claude, and Gemini have meaningfully different behavioral profiles
- Centralized versus federated platform: a real tradeoff between governance and speed

## Knowledge Quality And AI-Readiness

Enterprise documentation is rarely AI-ready by default. Making it usable requires curation, structuring, deduplication, contradiction resolution, governance, and freshness. RAG does not solve this on its own; it surfaces the quality problems faster. Moving from SharePoint or Confluence to effective retrieval is a hard transformation, and someone has to own maintaining that knowledge over time.

## Enterprise Adoption Patterns

The common failure is connecting data sources and expecting immediate productivity gains. The honest reality is the "show me it works on my data" proof-of-concept challenge. Evaluation has to happen on enterprise-specific data and use cases, not on public benchmarks, and change management is part of the architecture, not a separate workstream.

## LLMOps And Operationalization

My formal credential here is the Google Professional ML Engineer certification (LLMOps, GenAI), earned in March 2025. It covers deployment, monitoring, model lifecycle, and feedback loops. In an enterprise, governance, audit trails, and compliance add real complexity on top of standard MLOps.

## Telco-Specific Context

I work in large-scale, regulated environments with complex organizational dynamics: long specification cycles, multiple stakeholders who each speak a different language, legacy systems that must be integrated, and high availability and compliance requirements. Understanding those dynamics is as important as the architecture itself.

## Representative Work

FAT2 is my most complete real-world example: a TIM proof of concept for AI-assisted billing document verification, built as a full enterprise LLM pipeline with evaluation, experiment management, human-in-the-loop review, and cost control.

## Key Takeaway

Enterprise AI succeeds or fails on adoption, knowledge quality, and governance as much as on the model. My edge is designing platforms that are governable and aligned with enterprise reality, backed by production experience at a large Telco.
