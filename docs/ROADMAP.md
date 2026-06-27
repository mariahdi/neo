# Neo / Aria — Go-to-market roadmap

Epic: **NEO-85**. The path from prototype to a buyable, downloadable app.

> **Architecture note:** phones and app stores can't run the Python server on-device.
> So a phone version is a **thin client** (UI) talking to a **hosted Neo backend** +
> real accounts. "Own your data" = a **local file** on desktop; on mobile it becomes
> **"your account, encrypted, with export."** Real per-user auth (**NEO-77**) is the
> gateway to everything past the prototype.

## Phases

| Phase | Goal | Key tickets |
|---|---|---|
| **0 · Prototype** *(now)* | Desktop bundle (.exe/.app); share with family; validate it's loved | Desktop prototype ticket; Nessa instance (built); default profile (built) |
| **1 · Paid web** | First real product people can buy — no app stores needed | Real auth **NEO-77**, **SESSION_SECRET NEO-78**, RLS **NEO-76**, data export **NEO-79**, **Stripe billing (implemented)** |
| **2 · PWA** | Installable on phones ("Add to Home Screen"); cross-platform; free | PWA ticket; Aria portal **NEO-82** |
| **3 · App stores** | App Store + Google Play via Capacitor; in-app purchases | App-store ticket; needs NEO-77 + hosted backend |
| **4 · Native polish** | Push, biometrics, offline; possible RN/Flutter UI rewrite | (later) |

## Commerce strategy

- **Sell on the web first (Stripe, ~3% fees).** Stripe pipeline is wired now at **$0**
  so the flow is tested before anyone is charged (see `docs/BILLING.md`).
- App stores require **their** in-app purchase for digital subscriptions (**15–30%**
  cut) — add in Phase 3 for reach, after web proves people pay.
- Accounts/costs: Apple Developer **$99/yr**, Google Play **$25** one-time.
- Tooling: **RevenueCat** for cross-platform subscriptions; privacy policy + terms
  (extra care given health-adjacent data).

## What's already done toward this

- Nessa's gentle instance + a neutral **default** consumer profile (runnable today).
- Stripe billing pipeline (demo-verified end-to-end at $0).
- Hardening tickets queued: NEO-76/77/78/79.
