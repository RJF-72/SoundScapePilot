SoundScape Pilot
Your music industry, on autopilot.
SoundScape Pilot is a self-hosted command center for independent artists, labels, and managers. One desktop app runs the business side of a music career — radio promotion, venue booking, press outreach, and tour routing — from your own machine, under your own accounts, with your data staying yours.
No SaaS subscription. No middleman taking a cut of your hustle. You install it, you own it.

The Four Autopilots
📻 Radio Promotion
Finds real stations that fit your sound, scores them by match, and runs your radio campaign from one screen — station discovery, contact management, and follow-up, built for the indie and Red Dirt / Texas country world where relationships still matter.
🎤 Venue Booking Agent
A tireless booking agent with a built-in venue library — including a pre-seeded network of Texas church contacts (Taylor and Jones County) with an include_churches switch, because in Texas a church hall is a tour stop. Search venues, pitch dates, and track holds and confirmations.
📰 PR Wire
Press outreach without a publicist's retainer. Search real outlets (from wire services to Rolling Stone), build targeted press lists, and send pitches through your own mail setup — with real DKIM signing (RFC 6376 RSA-SHA256) when you configure your key, so your pitches land in inboxes, not spam folders.
🗺️ Tour Autopilot
Tell it where you're anchored and it suggests a workable route with real venues — routing, dates, and logistics in one view, so a two-week run stops being a spreadsheet nightmare.
Plus: a streaming promotion module, a full contact/venue database, and a dashboard that runs your whole operation at a glance.

Why Self-Hosted?
Your data stays on your machine — contacts, campaigns, and routes live in a local database, not on someone else's cloud.
Your accounts, your sending reputation — email goes out through your own SMTP setup; streaming and social integrations use your own keys.
No monthly rent — one license, your hardware, your rules.
Zero-config first run — the launcher sets itself up, picks a port, and opens the app in its own desktop window.

Getting Started
Requirements: Python 3.11+, Windows 10/11 for the desktop build (the backend runs anywhere Python does).
git clone https://github.com/RJF-72/SoundScapePilot.git
cd SoundScapePilot/SoundScapePilot
pip install -r requirements.txt
python launcher.py
First launch creates a config.json, starts the backend on an available port, and opens the SoundScape Pilot window. Set your owner credentials in the environment before first run (see backend.env.example) — the app refuses to start on default credentials, by design. Startup issues are logged to launcher.log.
A Windows installer can be built from source with build_msi.bat (PyInstaller spec: SoundScapePilot.spec).

Architecture
Layer
Tech
Backend
FastAPI (Python) — 100+ API routes across 20+ modules
Frontend
Static single-page app served by the backend, opened in a pywebview desktop window
Auth
Owner login with JWT sessions; credentials required via environment, fail-fast
Data
Local database on your machine
Mail
Your SMTP server; optional DKIM signing with your own key
Payments (optional)
Stripe-ready — connect your own keys to sell with it; endpoints stay dormant until you do

Pricing
SoundScape Pilot is commercial software from Redemption Road Music Group:
Single-user license — $497 one-time (lifetime, one machine)
Label license — $1,497 one-time (up to 10 machines)
24-month payment plans available on the store
👉 Store: https://pilot.redemptionroadmg.com
The complete asset — full source code, brand, and store — is also currently listed at auction on BidSmith.

Status — the honest part
SoundScape Pilot is a brand-new product: first public launch October 2026, $0 revenue and no user base yet — priced and sold as a finished, verified product, not as traction. The codebase was independently test-run end to end before launch: clean install with pinned dependencies, backend boot and login verified, all 102 API routes swept, live radio search, PR search, and tour routing exercised against real data, and DKIM signing cryptographically verified. Email dispatch endpoints refuse safely (with a clear message) until you configure your own SMTP — nothing sends on anyone's behalf out of the box.

License
Copyright © 2026 Ray Flanary / Redemption Road Music Group. All rights reserved.
SoundScape Pilot is proprietary commercial software. This repository is the product's home for documentation and release information; purchasing a license (or the asset) is what grants use and source rights.
Contact: redemptionroadmg@gmail.com
