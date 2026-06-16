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


###Architecture Diagram 

## Architecture Diagram

```mermaid
flowchart LR
    %% =========================
    %% EchoShield Architecture
    %% =========================

    U[User<br/>YouTube Takeout<br/>watch-history export]

    subgraph FE[Frontend — React + TypeScript]
        LP[Landing Page<br/>Explains metrics and echo chambers]
        UP[Upload Component<br/>watch-history.html / JSON]
        DB[Dashboard<br/>Session timeline + topic exposure + echo signals]
        POLL[Polling Layer<br/>Import status + enrichment status]
    end

    subgraph API[Backend — Spring Boot API]
        IC[Import Controller<br/>Creates import job]
        PC[Profile Analytics APIs<br/>Overview / sessions / trajectory]
        EC[Enrichment APIs<br/>Start job / progress]
        JOB[Async Job Orchestrator<br/>Runs Python pipeline steps]
    end

    subgraph PIPE1[Fast UI-Ready Pipeline — Python]
        LWH[load_watch_history.py<br/>Parse raw watch events]
        FYM[fetch_youtube_metadata.py<br/>Fetch video metadata]
        BWS[build_watch_sessions.py<br/>Create viewing sessions]
    end

    subgraph PIPE2[Async Enrichment Pipeline — Python]
        EMB[generate_video_embeddings.py<br/>Semantic embeddings]
        SIM[build_similarity_edges.py<br/>Video similarity graph]
        CLU[discover_semantic_clusters.py<br/>Content clusters]
        LAB[label_clusters_keybert.py<br/>Cluster labels]
        TAX[map_clusters_to_taxonomy.py<br/>Parent topic mapping]
        ECHO[calculate_echo_chamber_scores.py<br/>Echo concentration signals]
        DRIFT[calculate_temporal_drift.py<br/>Attention drift over time]
    end

    subgraph DBSTORE[PostgreSQL]
        P[(profiles)]
        RWE[(raw_watch_events)]
        YV[(youtube_videos)]
        SESS[(profile_watch_sessions)]
        ASSIGN[(watch_event_session_assignments)]
        VE[(video_embeddings)]
        VCA[(video_cluster_assignments)]
        CC[(content_clusters)]
        ECS[(echo_chamber_scores)]
        TD[(temporal_drift)]
        JOBS[(import_jobs<br/>embedding_jobs)]
    end

    %% User flow
    U --> LP
    LP --> UP
    UP --> IC

    %% Import flow
    IC --> JOBS
    IC --> JOB
    JOB --> LWH
    LWH --> FYM
    FYM --> BWS

    %% Fast pipeline writes
    LWH --> RWE
    FYM --> YV
    BWS --> SESS
    BWS --> ASSIGN

    %% Dashboard loads early
    POLL --> IC
    POLL --> PC
    PC --> P
    PC --> RWE
    PC --> YV
    PC --> SESS
    PC --> ASSIGN
    PC --> DB

    %% Enrichment starts after dashboard
    DB --> EC
    EC --> JOBS
    EC --> JOB

    %% Enrichment flow
    JOB --> EMB
    EMB --> SIM
    SIM --> CLU
    CLU --> LAB
    LAB --> TAX
    TAX --> ECHO
    ECHO --> DRIFT

    %% Enrichment writes
    EMB --> VE
    CLU --> VCA
    CLU --> CC
    TAX --> CC
    ECHO --> ECS
    DRIFT --> TD

    %% Dashboard refresh
    POLL --> EC
    EC --> JOBS
    PC --> VE
    PC --> VCA
    PC --> CC
    PC --> ECS
    PC --> TD

    %% Styling
    classDef user fill:#0f172a,stroke:#38bdf8,color:#e0f2fe,stroke-width:1.5px;
    classDef frontend fill:#082f49,stroke:#38bdf8,color:#e0f2fe,stroke-width:1.5px;
    classDef backend fill:#312e81,stroke:#818cf8,color:#eef2ff,stroke-width:1.5px;
    classDef pipeline fill:#064e3b,stroke:#34d399,color:#ecfdf5,stroke-width:1.5px;
    classDef db fill:#422006,stroke:#facc15,color:#fefce8,stroke-width:1.5px;
    classDef job fill:#4a044e,stroke:#e879f9,color:#fdf4ff,stroke-width:1.5px;

    class U user;
    class LP,UP,DB,POLL frontend;
    class IC,PC,EC backend;
    class JOB job;
    class LWH,FYM,BWS,EMB,SIM,CLU,LAB,TAX,ECHO,DRIFT pipeline;
    class P,RWE,YV,SESS,ASSIGN,VE,VCA,CC,ECS,TD,JOBS db;

