# Aria landing page — build spec for GoHighLevel

The public marketing site + "buy the app" funnel, built in GHL. GHL is the
**front door** (landing, checkout, CRM, email); **Neo** is the product it sells.
Reuse the look from `docs/brand/aria-portal.html` (warm dark palette, gold final
"A", Georgia headers, DM Mono body).

---

## Page sections (top → bottom)

### 1. Hero
- Wordmark: **ARI A** (gold final A)
- Headline: **Advancing Real-world Intelligence & Autonomy**
- Subhead (rotating/italic): *…but it's infinitely re-definable.*
- One-liner: **Your life, organized — and your data stays yours.**
- Primary button: **Get Neo →** (scrolls to pricing / opens checkout)
- Secondary: **See what it does ↓**

### 2. What is Neo
> **Neo — No Effort Organization.** A private personal OS for your whole life:
> recipes, goals, wins, money, wellness, and more — modular, fast, and yours.
- 3 trust badges: **🔒 Own your data** · **🙈 Private by design** · **🧩 Modular**

### 3. Feature tiles (3–6)
- **Own your data** — your life in one place; export it anytime; we never sell it.
- **Encrypted & private** — sensitive modules (like Wellness) are encrypted at rest.
- **No noise** — no streaks, no badges, no busywork. It stays out of your way.
- **Modular** — turn on only what you want; reset anytime without losing data.
- **Yours everywhere** — web + installable app (PWA) + desktop.

### 4. The Aria family (optional)
- **Neo** — personal OS (available)
- **Aria Finance / Nominal** — budgeting by Fixed · Loose · Float · Savings (link to nominalmoney.netlify.app)
- **Aria Robotics** — *coming soon*

### 5. Pricing + Buy  ← the conversion section
- Card(s) with plan + price + **Buy / Start** button wired to a **GHL checkout**
  (GHL → Stripe). (Today's pipeline runs at $0 to test the flow — see BILLING.md.)
- Microcopy: *Cancel anytime · Your data is exportable · Private by default.*

### 6. Trust / privacy strip
- "We don't sell your data. Sensitive entries are encrypted. You can export or
  delete everything, anytime." (Links to a short privacy page — also in GHL.)

### 7. Footer
- Aria · founders (optional) · contact · privacy · terms · social

---

## Buy → app-access flow (how a GHL sale becomes a working Neo login)

1. Visitor clicks **Buy** on the GHL landing → completes **GHL checkout** (Stripe).
2. On successful payment, GHL:
   - adds them to the CRM (so Dad's team can see/manage customers), and
   - triggers a **welcome workflow** → email with a **"Set up your Neo account" link**
     to the Neo app's **signup** page (`/signup`).
3. They create their Neo login → land in the product. Done.

**Connecting the two (pick one, simplest first):**
- **A. Manual/email link (MVP):** GHL emails the signup link on purchase. Zero
  code. Good enough to launch.
- **B. Automated entitlement (next):** GHL fires a **webhook** on purchase →
  a small Neo endpoint marks that email as "paid" so signup is gated to buyers.
  (Maps to the billing module + the API/webhook glue in the scalability plan.)

> Keep payments/customer records in GHL; keep the product + user data in Neo.
> The only thing that crosses is "this email paid" — never personal app data.

---

## Notes
- This **replaces** `aria-portal.html` as the *public* landing (that page can stay
  as the private family/preview portal).
- Match fonts/colors to the brand: DM Mono + Georgia, dark warm bg, gold accent.
- Mobile-first: GHL is responsive, but check the hero + pricing on phone.
