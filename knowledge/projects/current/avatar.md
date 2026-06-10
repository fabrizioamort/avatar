---
title: Avatar - This Digital Twin
category: projects
tags:
  - avatar
  - digital-twin
  - rag
  - firestore
  - cloud-run
priority: 0
updated: 2026-06-02
---

# Avatar - This Digital Twin

## Overview

Avatar is the application you are talking to right now. It is a web app that lets visitors interact with a Digital Twin of me, with a twist: I can join any conversation and weigh in, so the conversation can be three-way between the visitor, the Avatar, and me as the human.

The Avatar answers from my own knowledge using an agent with tools, and it streams its replies. When it cannot help, it notifies me. I built it both as something useful in its own right and as a hands-on exercise in the patterns I care about: retrieval-augmented generation, agentic tool use, evaluation, and clean cloud deployment.

## How It Works

The agent is built with the OpenAI Agents SDK, routed through OpenRouter so I can choose the model. It has tools to look up my proprietary knowledge and a tool to push a notification to me when a question needs a human. There is a fast path for frequently asked questions: typing a bare question shortcut returns a stored FAQ answer with no LLM call at all.

Answers stream to the visitor over Server-Sent Events, showing tool use as it happens. A lightweight poll picks up any messages I add asynchronously from the admin side, so the human-in-the-loop part feels live without a persistent socket.

## Retrieval-Augmented Knowledge

The knowledge about me is no longer a single static file in the prompt. It is a set of focused markdown documents that get chunked by heading, embedded, and stored in Firestore Vector Search using Vertex AI embeddings. At chat time the system retrieves the most relevant chunks for the visitor's question and injects only those into the system prompt, alongside style guidance and the three-way conversation rules. This keeps the prompt focused and makes the knowledge easy to extend by adding documents.

## Cloud Architecture

The app is a single container built by Cloud Build and deployed to Cloud Run. The database is Firestore in Native mode, secrets live in Secret Manager, and authentication uses Application Default Credentials with a dedicated service account. This is a deliberately clean, governable Google Cloud setup, the same discipline I bring to enterprise work, applied to a personal project.

## Why It Matters To Me

Avatar is a compact demonstration of my approach: treat a personal project as a production system, build retrieval and evaluation in properly, and keep the cloud architecture clean. It also embodies my belief about knowledge quality, since its usefulness depends entirely on how well the knowledge documents about me are written and structured.

## Key Takeaway

This very Digital Twin: an OpenAI Agents SDK app with Firestore Vector Search RAG, SSE streaming, a human-in-the-loop mode, and a clean Cloud Run deployment. A small, real demonstration of how I build.
