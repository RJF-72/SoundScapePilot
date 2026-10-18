# SOUNDSCAPE PILOT - Technical Specification & Functional Requirements

## 1. Project Overview
SoundScape Pilot is a specialized, self-hosted "Command Center" browser designed for music industry professionals. It is not a general-purpose web browser but a modular orchestration platform that combines automated research (scraping), AI-driven content generation, and a persistent dispatch engine to manage radio promotion, venue booking, and press distribution.

The system architecture consists of a **FastAPI backend** (handling database persistence, AI agents, and SMTP mailing) and a **High-Tech Glassmorphism Frontend** (acting as a real-time dashboard for asynchronous micro-agents).

---

## 2. Core Module Specifications

### 2.1 Multi-Vector Radio Autopilot
**Purpose:** To discover and contact radio stations that fit a specific musical genre.
- **Input:** Target Genre (e.g., "Cyberpunk Industrial").
- **Workflow:**
    - **Multi-Vector Search:** Concurrent scraping across 6 vectors: College, Military, Satellite, FM, AM, and Internet radio.
    - **Target Identification:** Extracting station names, frequency/stream, and contact emails.
    - **Library Persistence:** Saving discovered stations to a local SQLite library to avoid duplicate outreach.
    - **AI Pitching:** Using TinyML/AI to draft genre-specific pitches.
    - **Dispatch:** Routing emails through the Titan Mailer with DKIM signing.
- **UI Indicators:** Vector badges (Scanning $\rightarrow$ Found), real-time crawler logs, and a dispatch queue showing owner assignments (Ray, Keith, Joni, Paige).

### 2.2 Autonomous Booking Agent
**Purpose:** To identify bookable venues in a specific state and execute a persistent booking sequence.
- **Input:** Target State (e.g., "Texas").
- **Workflow:**
    - **Venue Discovery:** Scraping venue directories and calendars to find bookable spaces.
    - **Filtering:** Applying constraints (e.g., capacity between 200-2000).
    - **Asset Generation:** Dynamically generating tailored PDF EPKs (Electronic Press Kits) based on venue demographics.
    - **Contract Engine:** Drafting legally sound performance agreements.
    - **Persistence Engine:** Scheduling automated follow-ups (e.g., Day 3, Day 7) until a confirmation or rejection is received.
- **UI Indicators:** Venue pipeline, contract status (Sent $\rightarrow$ Negotiating $\rightarrow$ Booked), and agent PIDs.

### 2.3 SOTA Press Release Wire
**Purpose:** To distribute professional press releases to a tiered list of media outlets.
- **Input:** PR Topic / Release Name (e.g., "Debut Album 'Neon Horizon'").
- **Workflow:**
    - **Copywriting:** Using AI to craft "journalistic-grade" copy (avoiding marketing clichés).
    - **Tiered Targeting:** Identifying outlets across three tiers: Local, Niche, and Major.
    - **Anti-Spark Distribution:** Staggered dispatch to avoid spam filters and trigger organic "buzz."
    - **Tracking:** Arming tracking pixels to monitor open rates and engagement.
- **UI Indicators:** PR Crafting logs and a staggered delivery timeline.

### 2.4 Master Tour Autopilot (DAG Orchestrator)
**Purpose:** To automate the entire tour lifecycle from routing to financial settlement using a Directed Acyclic Graph (DAG).
- **Workflow:**
    - **Route Optimization:** Analyzing origin/destination and identifying "dead zones" (geographic gaps).
    - **Gap-Filling:** Automatically waking micro-agents to find and book venues in gap cities.
    - **Town Takeover:** Triggering a coordinated blast of Radio and PR activity in a target city 14 days before the show.
    - **Financial Ledger:** Calculating Gross vs. Net, applying house deductions, and generating settlement sheets.
- **UI Indicators:** DAG status (Routing $\rightarrow$ Booked $\rightarrow$ Settlement), Tour Manifest, and financial payout breakdowns.

### 2.5 Aegis Security Center
**Purpose:** To provide a "military-grade" browsing environment for sensitive industry operations.
- **Features:**
    - **Kernel Driver Simulation:** Intercepting traffic to bypass geo-blocks and tracking.
    - **Ghost Protocol:** Randomizing MAC addresses and packet TTL to prevent fingerprinting.
    - **Encrypted Tunneling:** AES-256-GCM multi-hop routing for anonymity.

---

## 3. System-Wide Technical Requirements

### 3.1 Backend (FastAPI)
- **Database:** SQLite for storing:
    - Radio/Venue/Media libraries.
    - Sent email logs (tracking IDs, timestamps).
    - Learning stats (which genres/states yield the most contacts).
- **AI Engine:** Integration for bio generation, one-sheets, and press release drafting.
- **SMTP Bridge:** Support for self-hosted mail servers (Postfix/Dovecot) with custom domain routing.

### 3.2 Frontend (HTML/CSS/JS)
- **Visual Style:** "Cyber-Industrial" aesthetic: dark backgrounds, neon accents (Magenta/Cyan), glassmorphism, and monospace fonts.
- **Dynamic UI:** Use of `async/await` fetch calls to keep the UI responsive while background agents work.
- **Resource Monitoring:** Simulated CPU/RAM/Task metrics to enhance the "Command Center" feel.

---

## 4. Success Metrics
- **Zero Manual Entry:** The user defines the "What" (Genre/State), and the system handles the "How" (Search $\rightarrow$ Pitch $\rightarrow$ Follow-up).
- **Persistence:** The system must remember every contact made to prevent harassment and ensure a professional outreach cadence.
- **SOTA Delivery:** High delivery rates via Aegis routing and AI-optimized copy.
