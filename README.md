# EduMatch — Student Project Matching & Collaboration Platform

> **Academic Program:** BCA — Artificial Intelligence & Data Science  
> **Project Category:** Full-Stack Web Application with Data Structures & Algorithms (DSA) Engine  
> **Team Size:** 5 Members  

---

## 🌟 Executive Summary

**EduMatch** is a specialized web platform connecting academic students who require guidance, development assistance, or mentorship on technical projects with vetted project providers, developers, and skilled peers.

Instead of searching randomly or relying on unverified claims, EduMatch utilizes a **custom Data Structures and Algorithms (DSA) matching and ranking engine** that calculates composite compatibility based on skill overlap, budget constraints, availability, and reputation ratings.

---

## 🏗️ System Architecture

```
                                  +-----------------------------+
                                  |   EduMatch Client UI        |
                                  |  (HTML5/CSS3/JS & React)    |
                                  +--------------+--------------+
                                                 |
                                     HTTP / JSON REST API
                                                 |
                                  +--------------v--------------+
                                  |   Python Flask Backend      |
                                  |        (app.py)             |
                                  +--------------+--------------+
                                                 |
                   +-----------------------------+-----------------------------+
                   |                                                           |
     +-------------v-------------+                               +-------------v-------------+
     |   DSA Matching Engine     |                               |   SQLite Database         |
     | - Set Overlap: O(M)       |                               | - users                   |
     | - Strict Budget Filtering |                               | - student_profiles        |
     | - Stable MergeSort:       |                               | - provider_profiles       |
     |   O(N log N)              |                               | - skills & requirements   |
     +---------------------------+                               | - conversations & messages|
                                                                 +---------------------------+
```

---

## ⚡ DSA Matching Engine Explanation

### 1. Mathematical Scoring Formulation

For any candidate provider $P$ and student project requirement $R$:

1. **Skill Overlap Score ($S$):** Calculated via Set Theory:
   $$S = \left(\frac{|P_{\text{skills}} \cap R_{\text{required\_skills}}|}{|R_{\text{required\_skills}}|}\right) \times 100$$
2. **Budget Compatibility Score ($B$):**
   - If $P_{\text{price}} > R_{\text{budget}}$ and strict budget mode is enabled $\rightarrow$ Provider is filtered out.
   - If $P_{\text{price}} \le R_{\text{budget}}$, score rewards cost efficiency:
     $$B = \max\left(40.0, 100.0 - \left(\frac{P_{\text{price}}}{R_{\text{budget}}} \times 40.0\right)\right)$$
3. **Availability Score ($A$):**
   - `available`: $100$
   - `limited`: $60$
   - `busy`: $25$
4. **Rating Score ($R^*$):**
   $$R^* = \left(\frac{\text{Rating}}{5.0}\right) \times 100$$

### Composite Total Score:
$$\text{Total Score} = 0.55 \cdot S + 0.20 \cdot B + 0.15 \cdot A + 0.10 \cdot R^*$$

### 2. Algorithmic Complexity

- **Set Intersection:** $O(M)$ average time where $M$ is the number of skills.
- **Sorting Algorithm:** Divide-and-Conquer **Merge Sort** (`dsa/sorting.py`).
  - **Best Case:** $O(N \log N)$
  - **Average Case:** $O(N \log N)$
  - **Worst Case:** $O(N \log N)$
  - **Auxiliary Space:** $O(N)$
  - **Stability:** Stable (maintains predictable ordering for equal match scores).

---

## 👥 5-Member Team Responsibilities

| Role | Member Focus | Deliverables |
|---|---|---|
| **Member 1** | Frontend & UI/UX | HTML5/CSS3 layouts, DM Sans typography, responsive portal cards |
| **Member 2** | Backend & Authentication | Flask Blueprints, Werkzeug password hashing, session cookies, route protection |
| **Member 3** | Database Persistence | SQLite schema (`database/schema.sql`), queries, foreign key enforcement |
| **Member 4** | DSA & Algorithm Design | Set theory matching, budget cutoff, merge sort ranking, complexity metrics |
| **Member 5** | Chat, Testing & Integration | Persistent messaging, collaboration workflows, `pytest` validation suite |

---

## 🚀 How to Run the Website

### Option 1: Full-Stack Flask Web Server (Recommended)

1. Activate your virtual environment in PowerShell:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
2. Start the application:
   ```powershell
   python app.py
   ```
3. Open your browser and navigate to:
   - **Homepage:** [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
   - **Student Login:** [http://127.0.0.1:5000/student/login.html](http://127.0.0.1:5000/student/login.html)
   - **Provider Login:** [http://127.0.0.1:5000/provider/login.html](http://127.0.0.1:5000/provider/login.html)
   - **Admin Login:** [http://127.0.0.1:5000/admin/login.html](http://127.0.0.1:5000/admin/login.html)


### Option 2: React + Vite Frontend (Modern SPA)

The repository also includes a complete React 18 + Vite setup inside `frontend-react/`:
1. Ensure Node.js is installed (`winget install OpenJS.NodeJS` or from [nodejs.org](https://nodejs.org/)).
2. Navigate to `frontend-react/` and install dependencies:
   ```powershell
   cd frontend-react
   npm install
   npm run dev
   ```
3. Access the Vite dev server at `http://localhost:5173`. Vite automatically proxies `/api` calls to the Flask backend running on port `5000`.

---

## 🧪 Running Automated Tests

Run the test suite using pytest:
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```
All 6 tests verify authentication security, API health, score calculations, budget filtering, and stable sorting.
