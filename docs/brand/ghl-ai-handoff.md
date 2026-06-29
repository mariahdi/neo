# GHL AI — Handoff Brief (paste this into GoHighLevel's AI)

You are helping set up GoHighLevel for **Aria**. GHL's job is the **front door**:
the marketing landing page, lead capture (CRM), and email/SMS follow-up. A
separate app called **Neo** is the product; it handles its own accounts and
billing — **GHL does NOT create accounts or send logins.** Build only the GHL side.

## The business
- **Aria** — parent brand. Tagline: "Advancing Real-world Intelligence & Autonomy"
  (it's "infinitely re-definable").
- **Neo** — the flagship product: a private "personal operating system" that helps
  people organize their whole life. Core promise: **own your data.**
- **Pricing:** $9.99/month, **14-day free trial**, cancel anytime.
- **Audience:** everyday people who want to get organized without feeling nagged
  or surveilled. Tone: warm, intelligent, a little playful — confident, not corporate.

## What I want you (GHL) to build
1. **A landing page** that sells Neo (sections + copy below).
2. **Lead capture** — add visitors/buyers to the CRM.
3. **Follow-up automation** — a friendly nurture sequence (email/SMS) for leads
   who don't buy, and a short "thanks for joining" note for buyers (but NOT their
   login — the app emails that).

## Landing page — sections (in order)
1. **Hero** — wordmark "ARIA"; headline "Your life, organized — and your data
   stays yours."; subline "Meet Neo, your private personal OS."; buttons
   "Get Neo" (primary) + "See how it works". Spacious, premium.
2. **What is Neo** — "Neo — No Effort Organization. A private personal OS for your
   whole life: recipes, goals, wins, money, wellness, and more — modular, fast,
   and yours." Trust badges: Own your data · Private by design · Modular.
3. **Features** — cards: Own your data (export anytime, never sold); Encrypted &
   private; No noise (no streaks, no badges, no busywork); Modular; Works
   everywhere (web, app, desktop).
4. **The Aria family** — Neo (available now); Aria Finance — budgeting dialed in;
   Aria Robotics (coming soon).
5. **Pricing** — $9.99/month, 14-day free trial; button "Start free trial".
6. **Trust & privacy** — "We don't sell your data. Sensitive entries are
   encrypted. You can export or delete everything, anytime."
7. **Footer** — Aria; Privacy / Terms / Contact; "Made with love."

## The buy flow (important — wire it exactly)
- Every **Get Neo / Start free trial** button links to my **Stripe Payment Link**
  (I will paste the URL): `__STRIPE_PAYMENT_LINK__`
- **Do not build a GHL order form or send account logins.** After payment, the app
  (Neo) automatically creates the account and emails the buyer their login.
- Optionally, sync Stripe customers into the GHL CRM so I can do email/SMS
  follow-up — but never include a password or login link in GHL emails.

## Brand styling
- **Accent:** warm gold **#E8A87C** (sparingly, on buttons + headings)
- **Background:** deep warm dark (**#0e0a07**), cream text (**#f5ede0**)
  — or a clean light theme if it sells better; keep it warm and premium either way.
- **Headings:** Georgia / elegant serif. **Body:** DM Mono (or clean monospace).
- **Logo wordmark:** "ARIA" with the final **A** in gold. Rounded cards, soft
  shadows, generous spacing. Mobile-first.

## Values to fill in
- Stripe Payment Link: `__STRIPE_PAYMENT_LINK__`
- App login URL (for reference only; do not email it): https://neo-dashboard-dmae.onrender.com/login
- Landing domain: `__YOUR_GHL_DOMAIN__`
