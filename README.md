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


## Key Features

### 1. Watch-History Upload

EchoShield accepts a Google Takeout YouTube watch-history export and creates a pseudonymised local profile for analysis.

Supported input formats depend on parser support, but the intended input is:

* YouTube watch-history HTML export
* YouTube watch-history JSON export

The uploaded file is processed locally by the backend pipeline.

---

### 2. Viewing Session Detection

Raw watch events are grouped into viewing sessions based on timestamps and gaps between watched videos.

This makes the analysis more meaningful than treating each video as an isolated event.

A viewing session captures:

* session start and end time
* number of videos watched
* session duration
* dominant topic
* channel diversity
* repeated exposure patterns

---

### 3. Session Bubble Timeline

The main dashboard visualises viewing sessions as interactive bubbles.

| Visual Element    | Meaning                              |
| ----------------- | ------------------------------------ |
| X-axis            | Time                                 |
| Y-axis            | Dominant topic                       |
| Bubble size       | Session duration                     |
| Bubble opacity    | Channel diversity                    |
| Bubble border     | Echo / concentration signal          |
| Click interaction | Shows videos watched in that session |

This gives users a fast visual overview of how their attention moved across topics over time.

---

### 4. Semantic Video Embeddings

EchoShield generates semantic embeddings from available video metadata such as:

* title
* description
* tags
* topic categories

These embeddings allow videos to be compared by meaning rather than exact keyword overlap.

For example, videos about discipline, habits, and consistency may belong to the same semantic cluster even if their titles use different wording.

---

### 5. Content Clustering

Videos are grouped into semantic clusters based on embedding similarity.

This helps identify repeated exposure to related content, even when the videos come from different creators or use different titles.

Clusters are then labelled and mapped to broader topic categories.

---

### 6. Topic Exposure

Topic exposure measures how much of the user’s viewing belongs to each broad content category.

This helps answer:

* Which topics dominate my viewing?
* Is my attention spread across many categories?
* Am I spending more time in a few narrow areas?
* Which topics are increasing or decreasing over time?

---

### 7. Echo Chamber Score

The echo chamber score measures repeated exposure to a narrow cluster of semantically similar content.

It acts as a concentration signal based on repeated cluster exposure, recent viewing share, and trend behaviour.

The score is not a judgement. It simply highlights areas where viewing behaviour may be becoming repetitive or highly concentrated.

---

### 8. Temporal Drift

Temporal drift measures how content exposure changes across time windows.

It helps identify:

* emerging interests
* sudden topic changes
* gradual narrowing of attention
* movement from one dominant category to another

This turns watch history into a time-based behavioural map.

---

## Metrics Explained

| Metric             | Meaning                                          | Why It Matters                                              |
| ------------------ | ------------------------------------------------ | ----------------------------------------------------------- |
| Watch events       | Individual video interactions from watch history | Provides the raw behavioural signal                         |
| Unique videos      | Count of distinct watched videos                 | Separates viewing volume from variety                       |
| Viewing sessions   | Groups of videos watched close together in time  | Shows how attention flows during real viewing periods       |
| Dominant topic     | Main topic within a session or time window       | Makes large watch histories easier to interpret             |
| Topic exposure     | Share of viewing assigned to each category       | Shows the user’s content mix                                |
| Channel diversity  | Spread of viewing across different creators      | Distinguishes broad exploration from repetitive consumption |
| Echo chamber score | Repeated exposure to similar content clusters    | Highlights concentration and attention loops                |
| Temporal drift     | Change in topics and clusters over time          | Reveals how viewing behaviour shifts                        |



## Architecture Diagram

<img width="2880" height="1732" alt="echoshield_architecture" src="https://github.com/user-attachments/assets/8c084837-a304-4ed5-b8ce-fd449f09327d" />



