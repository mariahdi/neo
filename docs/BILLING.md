# Billing pipeline (Stripe) — free beta, test-first

Neo's pay flow is wired early so the whole sign-up + billing pipeline can be
tested end-to-end **before anyone is ever charged**. It runs in two modes.

## Demo mode (default — zero setup)

With no Stripe keys set, the app is in **demo mode**: clicking **Join the beta**
on `/billing` instantly marks you active in the store. Use this to click through
the entire flow (plan → join → success → status) with no Stripe account at all.

Try it: open `/billing`, click Join, land on the success page, see status flip to
active. "Reset (testing)" clears it so you can run it again.

## Test mode (real Stripe, still $0)

1. Make a free **Stripe** account and **stay in TEST mode** (toggle, top of the
   Stripe dashboard).
2. Create a **Product** + a **recurring Price**, and set the amount to **$0**
   (or attach a 100%-off coupon) so nothing is charged during the prototype.
3. Set these env vars (alongside the other `NEO_*` keys):
   - `NEO_STRIPE_SECRET_KEY=sk_test_...`
   - `NEO_STRIPE_PRICE_ID=price_...`
   - `NEO_APP_URL=http://127.0.0.1:8000`  (your app's base URL)
   - `NEO_STRIPE_WEBHOOK_SECRET=whsec_...`  (from step 5)
   - optional: `NEO_PLAN_NAME`, `NEO_PLAN_PRICE` (display text)
4. Run the app. `/billing` now uses real **Stripe Checkout**; pay with the test
   card `4242 4242 4242 4242`, any future date + any CVC.
5. Forward webhooks to your local app with the **Stripe CLI**:
   ```
   stripe listen --forward-to 127.0.0.1:8000/api/billing/webhook
   ```
   Copy the `whsec_...` it prints into `NEO_STRIPE_WEBHOOK_SECRET`.

The webhook (`/api/billing/webhook`) is the **source of truth** for subscription
status; the success page also marks active optimistically so testing works even
without the CLI running. The webhook route is exempt from login auth so Stripe
can reach it.

## Notes / going live later

- Subscription status is stored **per-instance** for now (one record). Generalize
  to **per-user** once real accounts land (NEO-77).
- To charge for real: switch to **live** keys, set a real price, and gate
  features on the `active` status.
- App stores (iOS/Android) require **their** in-app purchase for digital
  subscriptions (15–30% cut) — sell on the web via Stripe first. See the product
  roadmap.
