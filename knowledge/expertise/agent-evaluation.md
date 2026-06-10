---
title: Agent and RAG Evaluation
category: expertise
tags:
  - evaluation
  - deepeval
  - llm-as-judge
  - adk-eval
  - golden-dataset
priority: 1
updated: 2026-06-02
---

# Agent and RAG Evaluation

## Overview

I have practical experience implementing RAG-specific evaluation with DeepEval and built a full evaluation platform that runs multiple strategies under consistent conditions and compares them side by side. The depth I am still building is broader agent evaluation beyond RAG: trajectory scoring, LLM-judge calibration, and eval sets for non-RAG agentic tasks.

My key personal insight: the hardest part of evaluation is not the metrics, it is building a representative, non-trivial eval set. Questions that are too easy or too hard both produce no signal. Eval-set design determines whether you learn anything.

## RAG Metrics (Hands-On With DeepEval)

I have implemented faithfulness, answer relevancy, contextual precision, contextual recall, and G-Eval correctness. All five use an LLM as judge, which is faster and cheaper than human annotation but subject to judge bias and inconsistency. I am wary that judges can be gamed by verbose, confident-sounding answers, and that small judge models are unreliable for nuanced faithfulness checks.

## Golden Dataset Methodology (FAT2)

For document pipelines I built structured ground truth: expected document types, expected field values with a match strategy per field, and expected rule results. Match strategies include exact, numeric with tolerance, fuzzy with a Levenshtein threshold, semantic, and contains. The hardest work was creating and validating the ground truth, not implementing the metrics. Beyond RAG metrics I track classification accuracy and per-type F1, field-level extraction accuracy, rule accuracy, and cost.

## Tracking Cost As A First-Class Metric

I always track cost in EUR alongside quality. A configuration that is two percent less accurate but 60 percent cheaper may be the right production choice. This is a habit from FAT2's experiment registry, which captures config, dataset, runtime, cost, and KPIs per run so decisions are evidence-based.

## ADK Native Evaluation (Studied In Depth)

ADK provides the most complete eval scaffolding in the GCP ecosystem. Its differentiator is the evalset format: JSON cases that define not just input and output but the full expected execution trace, including the expected tool-call trajectory. Its real gaps are also clear to me: the default response_match_score is ROUGE-1 lexical overlap that penalizes correct paraphrases, tool trajectory scoring is binary with no partial credit, there are no first-class cost or latency metrics, and the strongest LLM-judge metrics are locked to the paid Vertex AI Evaluation Service.

I have formed opinions on the alternatives too: RAGAS fills the trajectory-scoring gap via its AG-UI integration and ToolCallF1, which gives partial credit; DeepEval gives better response-quality metrics but must be wired in manually; and MLflow's ADK integration is tracing-only, so it is not worth building a dedicated MLflow-ADK eval layer.

## Key Takeaway

I build evaluation, not just run it: DeepEval RAG metrics, a comparison platform, and a from-scratch Golden Dataset framework with an experiment registry. I track cost as a metric, and I have a clear, critical map of the ADK, DeepEval, RAGAS, and MLflow eval landscape.
