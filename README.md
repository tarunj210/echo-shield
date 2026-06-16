# EchoShield

**Personal echo-chamber analytics for YouTube watch history.**

EchoShield is a full-stack analytics project that transforms raw YouTube watch-history exports into an explainable dashboard of viewing sessions, topic exposure, semantic content clusters, repeated exposure patterns, and attention drift.

The project is designed to help users understand how their digital attention changes over time and where content-consumption patterns may be becoming narrow, repetitive, or highly concentrated.

EchoShield does not judge content, classify users, or make automated decisions. It focuses on explainable personal media-awareness through data engineering, semantic analysis, and interactive visualisation.

---

## Problem Statement

YouTube watch history usually exists as a long, flat list of watched videos. While this list can show what a user watched, it does not clearly explain how their attention moved across topics, sessions, creators, and repeated content patterns.

A flat watch-history list cannot easily answer questions such as:

* What topics dominate my recent viewing?
* Are my sessions broad or concentrated?
* Am I repeatedly watching semantically similar content?
* How has my content exposure changed over time?
* Where are attention echo chambers forming?

EchoShield addresses this by converting raw behavioural data into structured, session-level and topic-level insights.

---

## Core Concept: Attention Echo Chambers

In EchoShield, an **attention echo chamber** means repeated exposure to a narrow cluster of semantically similar content over time.

This does not imply that the content is harmful, false, or negative. Instead, it means the user’s viewing behaviour is becoming concentrated around similar topics, creators, or content themes.

EchoShield detects attention echo chambers using:

* viewing-session analysis
* semantic video embeddings
* content clustering
* topic exposure ratios
* repeated exposure signals
* temporal drift patterns

The result is an explainable view of how a user’s media consumption narrows, expands, or shifts over time.
