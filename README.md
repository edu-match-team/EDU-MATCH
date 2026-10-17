# 🎓 EduMatch — Academic Project Matching & Mentorship Ecosystem

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Backend-Flask%20Framework-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Supabase](https://img.shields.io/badge/Cloud%20Sync-Supabase-3ECF8E?logo=supabase&logoColor=white)](https://supabase.com/)
[![DSA Engine](https://img.shields.io/badge/DSA%20Engine-8%20Custom%20Structures-8A2BE2)](#-dsa-engine-deep-dive)
[![Tests](https://img.shields.io/badge/Tests-Pytest%20Passing-success?logo=pytest)](https://docs.pytest.org/)

> **Academic Program:** BCA — Artificial Intelligence & Data Science  
> **Project Type:** Full-Stack Academic Collaboration Platform with Custom DSA Engine  
> **Authors:** Vishwajeet Rawat & Team  

---

## 📖 Table of Contents
- [🌟 Platform Overview](#-platform-overview)
- [⚡ Key Features & Portals](#-key-features--portals)
- [🏗️ System Architecture](#-system-architecture)
- [🧠 Custom DSA Engine Deep-Dive](#-custom-dsa-engine-deep-dive)
- [💻 Tech Stack](#-tech-stack)
- [📁 Project Directory Structure](#-project-directory-structure)
- [🚀 Quick Start & Installation](#-quick-start--installation)
- [🧪 Running Automated Tests](#-running-automated-tests)
- [📚 Full Technical & Viva Guide](#-full-technical--viva-guide)

---

## 🌟 Platform Overview

**EduMatch** is a peer-to-peer academic collaboration and mentorship ecosystem connecting university students with vetted peer developers, technical researchers, and subject-matter mentors.

Instead of unvetted messaging groups, EduMatch features:
- **Intelligent DSA Matching & Semantic Search**: Direct relevance scoring for queries like `"Senior AI"`, `"Web Developer"`, and `"App Developer"`, placing exact matches and domain experts at the top of search results.
- **Strict Role-Isolated Real-Time Chat**: Students and mentors communicate with private message threads, deliverable file downloads, and photo attachments.
- **Requirement Lifecycle & Acceptance Exclusivity**: When a provider accepts a project, it transitions to `in_progress` and is automatically removed from open browse feeds.
- **Cloud Resiliency**: Fast local SQLite storage paired with asynchronous Supabase cloud backup.

---

## ⚡ Key Features & Portals

### 🎓 1. Student Portal (`/student`)
- **DSA Search & Autocomplete**: Real-time prefix suggestions via Trie and instant ranking via Binary Max-Heap.
- **Multi-Filter Engine**: Filter by Project Category, Required Tech Stack, and Maximum Budget.
- **Provider Showcase**: Inspect mentor ratings, hourly rates, verified badges, past projects, and portfolios.
- **Order Service & Custom Proposals**: Direct milestone booking with escrow-style budget tracking.
- **Isolated Messaging & Deliverable Viewer**: Receive finished project deliverables and view download links directly in chat.

### 💼 2. Provider Portal (`/provider`)
- **Professional Portfolio & Services**: Publish custom gig offerings (e.g., "Full Stack Web App", "ML Model Training").
- **Open Project Requirements Feed**: Browse student project requests and submit bids.
- **Order Management**: Track pending, in-progress, and completed contracts.
- **Deliverables Modal**: Submit milestone code repositories, documentation, and Google Drive links directly to students.

### 🛡️ 3. Admin Portal (`/admin`)
- **Platform Analytics**: Live KPI counters for active users, students, providers, orders, and messages.
- **User Moderation**: Verify providers, manage student records, and toggle account statuses.
- **Dispute Resolution**: Arbitrate project issues between students and mentors.

---

## 🏗️ System Architecture

```
                                  +-----------------------------+
                                  |     EduMatch Frontend UI    |
                                  |  (Vanilla HTML5 / CSS3 / JS)|
                                  +--------------+--------------+
                                                 |
                                     HTTP / REST API (JSON)
                                                 |
                                  +--------------v--------------+
                                  |     Python Flask Backend    |
                                  |           (app.py)          |
                                  +--------------+--------------+
                                                 |
                   +-----------------------------+-----------------------------+
                   |                                                           |
     +-------------v-------------+                               +-------------v-------------+
     |     Core DSA Engine       |                               |      Persistence Layer    |
     | - Max-Heap Priority Queue |                               | - SQLite (edumatch.db)    |
     | - Trie (Prefix Tree)      |                               | - Supabase Cloud Sync     |
     | - Stable Merge Sort       |                               |                           |
     | - LRU Cache               |                               |                           |
     | - Separate Chaining Hash  |                               |                           |
     | - Graph BFS & Dijkstra    |                               |                           |
     +---------------------------+                               +---------------------------+
```

---

## 🧠 Custom DSA Engine Deep-Dive

EduMatch does **not** rely on slow database table scans for search and ranking. It implements **8 native Data Structures & Algorithms** in Python:

| # | Data Structure / Algorithm | Source File | Usage in EduMatch | Time Complexity | Space Complexity |
|---|---|---|---|---|---|
| **1** | **Binary Max-Heap Priority Queue** | [`dsa/priority_queue.py`](dsa/priority_queue.py) | Match ranking and urgent student project scheduling | $O(\log N)$ push/pop, $O(N \log K)$ Top-$K$ | $O(N)$ |
| **2** | **Trie (Prefix Tree)** | [`dsa/searching.py`](dsa/searching.py) | Google-like search autocomplete for skills, categories, and titles | $O(L)$ where $L = \text{query length}$ | $O(\Sigma \cdot L \cdot N)$ |
| **3** | **Stable Merge Sort** | [`dsa/sorting.py`](dsa/sorting.py) | Divide-and-conquer chronological ordering of orders & requests | $O(N \log N)$ (Best, Avg, Worst) | $O(N)$ |
| **4** | **LRU Cache** | [`dsa/lru_cache.py`](dsa/lru_cache.py) | Doubly-linked list + hash map caching of match query payloads | $O(1)$ get, $O(1)$ put, $O(1)$ eviction | $O(\text{Capacity})$ |
| **5** | **Separate Chaining Hash Table** | [`dsa/hash_table.py`](dsa/hash_table.py) | Fast in-memory user/provider profile caching | $O(1)$ average lookup, $O(N)$ worst | $O(N + B)$ |
| **6** | **Bipartite Interaction Graph** | [`dsa/graph_matching.py`](dsa/graph_matching.py) | Peer recommendations using BFS & shortest matching path via Dijkstra | BFS: $O(V + E)$, Dijkstra: $O((V+E)\log V)$ | $O(V + E)$ |
| **7** | **Binary Search** | [`dsa/searching.py`](dsa/searching.py) | Boundary cutoff analysis in pre-sorted provider score lists | $O(\log N)$ | $O(1)$ |
| **8** | **Set Theory & Semantic Concept Graph** | [`dsa/matching.py`](dsa/matching.py) | Query relevance, semantic domain expansion & Jaccard skill overlap | $O(N \cdot M)$ | $O(M)$ |

---

## 💻 Tech Stack

- **Backend**: Python 3, Flask, Werkzeug, Flask-CORS
- **Frontend**: Vanilla HTML5, Modern CSS3 (CSS Variables, Flexbox/Grid, Glassmorphism), ES6 JavaScript
- **Database**: SQLite3 (Embedded zero-latency relational engine)
- **Cloud & Realtime**: Supabase (PostgreSQL Cloud Sync, Real-time Webhooks & Notifications)
- **Testing**: Pytest

---

## 📁 Project Directory Structure

```
EDU MATCH/
├── dsa/                       # Custom Data Structures & Algorithms Library
│   ├── matching.py            # Multi-criteria scoring, semantic expansion & ranking
│   ├── priority_queue.py      # Binary Max-Heap and Priority Queue
│   ├── searching.py           # SkillTrie (Prefix Tree) & Binary Search
│   ├── sorting.py             # Stable MergeSort
│   ├── lru_cache.py           # Doubly-Linked List + Hash Map LRU Cache
│   ├── hash_table.py          # Separate-chaining Hash Table with polynomial hash
│   └── graph_matching.py      # Bipartite Adjacency List Graph (BFS & Dijkstra)
│
├── backend/                   # Python Flask REST API
│   ├── app.py                 # Application factory & blueprint registration
│   ├── config.py              # App configuration
│   ├── database/              # SQLite queries & Supabase cloud sync
│   └── routes/                # Auth, Chat, Matching, Providers, Requests, Admin
│
├── frontend/                  # Web Client Portals
│   ├── student/               # Student search, orders, chat, profile
│   ├── provider/              # Provider dashboard, requests, services, chat
│   └── admin/                 # Admin dashboard, users, orders, reports
│
├── database/                  # SQLite schema & initialization script
│   ├── schema.sql
│   ├── seed_db.py
│   └── edumatch.db
│
├── tests/                     # Pytest automated test suite
├── README.md                  # This file
└── DSA_AND_PROJECT_GUIDE.md   # Complete viva voce and technical mentor manual
```

---

## 🚀 Quick Start & Installation

### 1. Prerequisites
- Python 3.10+ installed
- Git installed

### 2. Clone Repository
```bash
git clone https://github.com/rawatvishwajeet9-ship-it/EDU-MATCH.git
cd "EDU MATCH"
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Flask Server
```bash
python backend/app.py
```
The server will boot at: **`http://127.0.0.1:5000`**

### 5. Access Portals
- **Landing Page**: `http://127.0.0.1:5000/index.html`
- **Student Search**: `http://127.0.0.1:5000/student/search.html`
- **Student Chat**: `http://127.0.0.1:5000/student/chat.html`
- **Provider Dashboard**: `http://127.0.0.1:5000/provider/dashboard.html`
- **Admin Dashboard**: `http://127.0.0.1:5000/admin/dashboard.html`

---

## 🧪 Running Automated Tests

Run the full pytest suite to verify all DSA structures and backend routes:

```bash
python -m pytest tests/ -v
```

Expected output:
```
tests/backend/test_auth.py::test_auth_flow PASSED
tests/backend/test_profile_and_chat.py::test_student_profile_photo_and_completion PASSED
tests/backend/test_search_and_matching.py::test_senior_ai_ranking PASSED
tests/backend/test_search_and_matching.py::test_web_developer_ranking PASSED
tests/backend/test_search_and_matching.py::test_app_developer_ranking PASSED
tests/dsa/test_dsa_structures.py::test_priority_queue_ordering PASSED
tests/dsa/test_dsa_structures.py::test_top_k_elements PASSED
tests/dsa/test_dsa_structures.py::test_lru_cache_operations PASSED
tests/dsa/test_dsa_structures.py::test_graph_bfs_and_dijkstra PASSED
tests/dsa/test_dsa_structures.py::test_hash_table PASSED
tests/dsa/test_matching.py::test_calculate_match_score_perfect PASSED
tests/dsa/test_matching.py::test_merge_sort_descending PASSED
================ 12 passed in 1.2s =================
```

---

## 📚 Full Technical & Viva Guide

For project evaluators, college professors, and viva voce preparation, consult the dedicated companion guide:  
👉 **[`DSA_AND_PROJECT_GUIDE.md`](DSA_AND_PROJECT_GUIDE.md)**

It includes:
- Architectural breakdowns with ASCII and Mermaid flowcharts.
- Step-by-step mathematical proofs of the matching formula.
- Exact line-by-line file references for every algorithm.
- Frequently asked viva voce questions with model answers.

---
© 2026 EduMatch · Built with ❤️ by Vishwajeet Rawat & Team (BCA AI & Data Science)
