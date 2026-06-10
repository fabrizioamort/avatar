---
title: Cloud and Google Cloud Platform
category: expertise
tags:
  - gcp
  - vertex-ai
  - cloud-native
  - cloud-run
  - architecture
priority: 1
updated: 2026-06-02
---

# Cloud and Google Cloud Platform

## Overview

Google Cloud is my primary cloud, and cloud-native architecture is one of my top skills alongside LLMOps. I am a Google Professional Cloud Architect, certified February 2025, and I hold the Architecting with Google Kubernetes Engine specialization. My GenAI work sits on Vertex AI and the surrounding Google Cloud services.

## How I Use Google Cloud For AI

My AI work centers on Vertex AI: the Gemini models in their Flash and Pro variants, the Vertex embedding models, and the managed evaluation and observability services. For deployment I work with two main targets, which I have studied in depth through the agent-starter-pack:

- Cloud Run: stateless, containerized agents with fast cold start, good for request-response APIs, with the image built by Cloud Build.
- Agent Engine: managed agent hosting on Vertex AI, with built-in session management, scaling, and tracing, where ADK agents deploy directly.

I also build directly on Google Cloud primitives in my own projects. The Avatar, for example, runs on Cloud Run with Firestore in Native mode as the database, secrets in Secret Manager, and authentication via Application Default Credentials and a dedicated service account. Its RAG layer uses Firestore Vector Search with Vertex AI embeddings.

## Cloud-Native Foundations

My cloud-native credentials build on a long history of large-scale platform work. Before AI, I designed and ran web platforms serving tens of thousands of users, with a constant focus on scalability, reliability, and time-to-market. That experience means I treat AI systems as production systems: they need the same discipline around availability, cost, security, and operations that any enterprise platform does.

## Authentication And Operations

I use Application Default Credentials locally and service accounts in production, rather than long-lived credential files. For Gemini I have used a dual-auth pattern: an API key for local development and Vertex AI ADC for GCP production. Secrets live in Secret Manager. This keeps the same code working across environments without embedding credentials.

## Key Takeaway

Google Cloud is my home platform: Professional Cloud Architect and GKE certified, building real AI systems on Vertex AI, Cloud Run, Firestore, and Secret Manager, with a cloud-native discipline that predates AI by many years.
