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
  - drupal
  - security
priority: 0
updated: 2026-06-20
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

I took on every TIM Group website except the commercial ones. The very first was an internal corporate blog, originally built on a custom platform from a French vendor; as more initiatives wanted their own site, running a different platform per initiative stopped making sense for development time and cost, so I standardized on Drupal for its flexibility across very different site types and its zero licensing cost as open source software. To make that scale, I built Multiblog, a shared Drupal base that could host many independent sites without standing up new infrastructure for each one: the base was always there, and a new site was just built on top of it, which cut delivery time dramatically. I worked daily on this LAMP stack (Linux, Apache, MySQL, PHP) and Drupal.

For seventeen years I designed and implemented this unified Drupal platform for the TIM Group, and contributed to the design, architecture, and in some cases development of around 30 enterprise websites, several of which tracked the rise and fall of initiatives inside Telecom Italia while a handful built for subsidiary companies in the group survived for years. I held end-to-end responsibility: user interaction, requirement collection, architectural design, development support, and operations, including deployment and security, up to handling real attacks against these sites. The recurring theme was scalability, reliability, and time-to-market for large-scale digital platforms.

On the people side, each project was small in scope, so the teams I led were small too, typically around two people at a time. Because the sites spanned the whole TIM Group, I regularly interfaced with business functions well beyond engineering: customer care, marketing and communications, institutional affairs, the teams running the network, and HR, among others — practically every function in the company at some point.

Attack attempts against these sites were essentially a daily occurrence, visible in the logs, and none of them ever succeeded. Most were automated scans for known vulnerabilities in major CMSs, especially WordPress but also Drupal itself. What made the difference was treating patching as time-critical rather than just policy-compliant: beyond following internal security policy, I watched Drupal's own security advisories closely, and when a particularly serious vulnerability was disclosed, I made sure every site was patched before attackers could act on it. My rule of thumb for a publicly disclosed, serious flaw is to reason in hours, not days or weeks: once a vulnerability is public, automated exploitation can start within hours, so it has to be treated like a zero-day, with remediation essentially immediate rather than queued behind a normal change cycle. That discipline is why no attack against any site I ran was ever successful, including the cases our SOC flagged as potentially dangerous; on investigation those were always caught in time.

### GenAI Architect (June 2024 to present)

This is my current role. I do the architectural design of Agentic AI solutions for enterprise use cases, and I design reference architectures, patterns, and guidelines for GenAI applications. I develop and supervise multiple PoCs and pilot projects, some of which evolve into production, and I collaborate across architecture, development, and operations teams. My most complete example of this work is FAT2, an AI-assisted billing document verification system.

As in my Drupal years, the teams I lead here are small, typically around two people, sized to each PoC or pilot, and I continue to work with the same breadth of business functions across the company.

## What The Arc Gives Me

Because I lived through low-level systems, then web at scale, then cloud, then AI, I do not treat AI as a greenfield novelty. I treat it as the next layer on top of enterprise systems that still have to integrate with everything that came before. That perspective is hard to acquire quickly, and it is central to how I architect.

## Key Takeaway

Low-level systems, then web platforms at 100k-user scale, then cloud-native, now Agentic AI: a 30-year arc that makes me an architect who understands enterprise reality, not just the model layer.
