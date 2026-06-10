---
title: Multi-Model Strategy
category: ideas
tags:
  - multi-model
  - model-selection
  - gpt
  - claude
  - gemini
priority: 1
updated: 2026-06-02
---

# Multi-Model Strategy

## The Idea

Different models have meaningfully different behavioral profiles, and enterprises should route different tasks to different models based on those strengths rather than standardizing on a single vendor.

In my own practical experience: GPT feels disciplined and precise for clear specifications. Claude and Sonnet feel more creative and exploratory. Gemini brings strong document and multimodal handling and good domain coverage for finance and legal terminology, which is why I reached for it in FAT2 and in spec extraction.

## Why It Matters

The instinct in large organizations is to pick one vendor and standardize, for procurement and governance reasons. That is understandable, but it leaves capability on the table. The behavioral differences between frontier models are real enough that the right model for disciplined structured extraction is not always the right model for open-ended reasoning or creative drafting.

A multi-model architecture treats model choice as a routing decision per task type, not a one-time vendor commitment. This is closely related to how I think about pipeline design: the discipline is knowing which tool fits which job, whether that tool is a deterministic parser, a cheap worker model, or a frontier model.

## How It Shows Up In Practice

- Spec extraction and finance/legal terminology: Gemini
- Disciplined extraction against a clear schema: GPT-style precision
- Exploratory reasoning and drafting: Claude / Sonnet
- Cost-sensitive sub-tasks: a cheaper, faster worker model in a two-tier setup

Tools like LiteLLM and OpenRouter make this practical by giving a unified interface across providers, so application code does not change when the routing does. I used exactly this pattern in the "finally" project.

## The Honest Caveat

Behavioral profiles shift with every model release, so this is not a fixed mapping. It is a habit of evaluating models against your actual tasks rather than assuming one vendor wins everywhere. The strategy is the routing mindset, not any particular assignment.

## Key Takeaway

Models have distinct behavioral strengths, so route tasks to the model that fits rather than standardizing on one vendor. The strategy is a routing mindset kept honest by evaluation, not a fixed model-to-task map.
