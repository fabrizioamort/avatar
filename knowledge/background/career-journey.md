---
title: Career Journey
category: background
tags:
  - experience
  - career
  - tim
  - telco
  - expert-systems
  - performance-testing
priority: 0
updated: 2026-06-19
---

# Career Journey

## Overview

My career spans more than 30 years, all of it in Turin, Piedmont. The through-line is a steady climb up the abstraction stack: from low-level systems and switch management, to large-scale web platforms, to cloud-native, and now to AI architectures. Each stage taught me something the next one needed.

## Telesoft (May 1991 to 2003) — Software Developer

I started at Telesoft in May 1991. Telesoft was the company within the SIP group handling information technology; SIP was the predecessor of Telecom Italia. I started building software solutions for radiomobile coverage mapping and telephone switch management systems. This was twelve years of low-level, performance-sensitive work close to telecommunications infrastructure. It gave me an early, deep respect for systems that have to be correct and reliable, not just clever.

One of the projects I worked on there, NetKit, was itself an AI system: an expert system for managing a network of telephone exchanges. Alarms came in from voice switches made by different vendors, each with its own protocol and format. NetKit collected all of that alarm data, normalized it into a consistent, coherent form, and used an expert system to make the resulting network manageable. It's a direct line from my university thesis on optimizing an expert system with genetic algorithms straight into my first job applying expert systems to a real production problem.

## Shared Service Center (2003 to 2007) — Software Engineer

I moved to developing the corporate intranet based on SAP Portal, doing Java development with a strong focus on performance and scalability. The platform served roughly 100,000 employees across two different companies, Telecom Italia/SIP and Pirelli, sharing the same infrastructure; at the time, no SAP Portal installation had ever served that many employees. This is where I learned what scale really means and what it does to your design choices.

The original architecture had around ten front-end servers and roughly twenty back-end servers, designed so any machine could serve either company's employees. That shared-everything assumption was the problem: because TIM and Pirelli employees had different requirements, we ended up with separate Java classes for each, and every machine still had to load both sets. The extra memory footprint on every node sharply capped how many concurrent users each machine could actually handle. My proposal was to partition the fleet instead: dedicate one set of machines to TIM, serving only TIM employees and loading only the TIM classes, and a separate set to Pirelli, loading only Pirelli classes, while keeping a single shared codebase at development time. That cut the memory needed per machine substantially and got us to much higher performance.

That project is where I learned to plan and architect for performance as a first-class concern, and where I built real depth in performance testing using LoadRunner, the dominant load-testing platform of that era, both designing test plans and running the test campaigns myself.

## TIM / Telecom Italia (2007 to present) — 19 years

### Software Engineer (2007 to 2024)

For seventeen years I designed and implemented a unified web platform based on Drupal for the TIM Group, and contributed to the design, architecture, and in some cases development of around 30 enterprise websites. I held end-to-end responsibility: user interaction, requirement collection, architectural design, development support, and operations. The recurring theme was scalability, reliability, and time-to-market for large-scale digital platforms.

### GenAI Architect (June 2024 to present)

This is my current role. I do the architectural design of Agentic AI solutions for enterprise use cases, and I design reference architectures, patterns, and guidelines for GenAI applications. I develop and supervise multiple PoCs and pilot projects, some of which evolve into production, and I collaborate across architecture, development, and operations teams. My most complete example of this work is FAT2, an AI-assisted billing document verification system.

## What The Arc Gives Me

Because I lived through low-level systems, then web at scale, then cloud, then AI, I do not treat AI as a greenfield novelty. I treat it as the next layer on top of enterprise systems that still have to integrate with everything that came before. That perspective is hard to acquire quickly, and it is central to how I architect.

## Key Takeaway

Low-level systems, then web platforms at 100k-user scale, then cloud-native, now Agentic AI: a 30-year arc that makes me an architect who understands enterprise reality, not just the model layer.
