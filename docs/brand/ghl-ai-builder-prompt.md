# GHL AI Website Builder — prompt for the ARIA landing page

## Where to paste it in GoHighLevel
1. Left menu → **Sites** → **Websites** (or **Funnels**).
2. **+ New** → choose **"Design with AI" / "AI Website Builder"** (wording varies by GHL version).
3. Paste the **Prompt** below when it asks what to build.
4. If it asks for fields separately, use the **Quick fields** section.
5. Generate → then tweak colors/fonts to the brand spec at the bottom.

> Tip: generate first, then on each section click **Buy/Get Neo** buttons and
> point them at your GHL **checkout/order form** (that's the buy→app step).

---

## Prompt (paste this whole block)

Build a modern, warm, premium landing page for **Aria** — a technology company
whose tagline is "Advancing Real-world Intelligence & Autonomy," and whose idea
is that the name is "infinitely re-definable." The page sells our flagship
product, **Neo**, a private "personal operating system" that helps people
organize their whole life — and whose #1 promise is **"own your data."**

Tone: warm, intelligent, a little playful — it should make you smile and feel
in control, not corporate or salesy. Audience: everyday people who want to get
organized without feeling nagged or surveilled.

Create these sections in order:

1. **Hero** — Big wordmark "ARIA". Headline: "Your life, organized — and your
   data stays yours." Subline: "Meet Neo — your private command center." Two buttons:
   "Get Neo" (primary) and "See how it works" (scrolls down). Spacious, premium,
   confident feel.

2. **What is Neo** — Short paragraph: "Neo — No Effort Organization. A private
   personal OS for your whole life: recipes, goals, wins, money, wellness, and
   more — modular, fast, and yours." Three small trust badges: "Own your data",
   "Private by design", "Modular".

3. **Features** — A grid of 4–5 cards:
   - Own your data — your life in one place; export it anytime; never sold.
   - Encrypted & private — sensitive entries are encrypted; you stay in control.
   - No noise — no streaks, no badges, no busywork; it stays out of your way.
   - Modular — turn on only what you want; change it anytime without losing data.
   - Yours everywhere — works on web, installs like an app, runs on desktop.

4. **The Aria family** — Three items: "Neo — personal OS (available now)",
   "Aria Finance — budgeting, dialed in (by Fixed, Loose, Float & Savings)",
   "Aria Robotics — autonomy in the physical world (coming soon)".

5. **Pricing / Get Neo** — A clean pricing card with a "Start with Neo" button
   wired to checkout. Microcopy: "Cancel anytime · Your data is exportable ·
   Private by default."

6. **Trust & privacy** — One reassuring line: "We don't sell your data.
   Sensitive entries are encrypted. You can export or delete everything, anytime."

7. **Founders** — Two cards: "Mariah Dionne Harris — Co-Founder & CTO (conceived
   and builds Aria)" and "Charles 'Chuck' Harris — Co-Founder & CEO (network,
   revenue, and scaling the business)."

8. **Footer** — Aria, with links for Privacy, Terms, and Contact, and a small
   line: "Made with love."

Make it mobile-friendly and fast. Use generous spacing, rounded cards, and a
single warm gold accent color.

---

## Quick fields (if GHL asks separately)
- **Business name:** Aria
- **Product:** Neo (a private personal-OS app — "own your data")
- **Industry:** Software / productivity / personal apps
- **Tagline:** Advancing Real-world Intelligence & Autonomy
- **Primary CTA:** Get Neo
- **Audience:** Everyday people who want to organize their life privately

---

## Brand style to apply after generating
- **Accent / primary color:** warm gold **#E8A87C** (use sparingly, on buttons + headings)
- **Background:** deep warm dark (e.g. **#0e0a07** → **#1a120c**), light cream text **#f5ede0**
  - *(or a clean light theme if you prefer a brighter sell — your call)*
- **Heading font:** Georgia / elegant serif
- **Body font:** DM Mono (or a clean monospace) for a distinctive, techy-but-warm feel
- **Logo wordmark:** "ARIA" with the final **A** in gold
- Keep it spacious, rounded corners, soft shadows — premium and confident.

## After the page exists — buy → account flow (chosen: Stripe webhook)
- Point every **Get Neo / Start with Neo** button at your **Stripe Payment Link**
  (or Stripe Checkout) for **$9.99/mo with a 14-day free trial**.
- On payment, Stripe fires `checkout.session.completed` to Neo's webhook
  (`/api/billing/webhook`). Neo automatically **creates the account** and
  **emails the buyer** their login (URL + email + password). Zero manual steps.
- **GHL stays the marketing/landing + CRM layer** — host the page, capture leads,
  run email/SMS follow-up (you can sync Stripe customers into GHL). It does NOT
  create accounts.
- *Backup path:* `POST /api/provision` (with `NEO_PROVISION_SECRET`) can create an
  account manually, or from a GHL workflow, if you ever switch to GHL-driven checkout.

### Setup checklist
1. Stripe: create a **$9.99/mo Price** with a **14-day trial**, then a **Payment Link**.
2. Stripe → Webhooks: add `https://neo-dashboard-dmae.onrender.com/api/billing/webhook`,
   event `checkout.session.completed` → copy the `whsec_…`.
3. Render env: `NEO_STRIPE_SECRET_KEY`, `NEO_STRIPE_PRICE_ID`, `NEO_STRIPE_WEBHOOK_SECRET`,
   `NEO_APP_URL`, `NEO_EMAIL_FROM`, `NEO_EMAIL_PASSWORD` (Gmail App Password).
4. Landing buttons → the Stripe Payment Link. Done.
