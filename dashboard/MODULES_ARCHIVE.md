# Module archive — pre-9-category setup (backed up 2026-07-02)

Chuck's "9 Dashboards for Life" framing replaced the old free-form module set.
**No module code was deleted.** Retired modules still have their `.py` files and
their routers are still mounted in `main.py`, so their routes keep working
(e.g. `/stocks`, `/recipes`) — they're just no longer listed in the catalog
(`registry.py`) or on the launcher.

## The 9 categories now shown (registry.py order)
| # | Category | Module (key → route) | Status |
|---|----------|----------------------|--------|
| 1 | Health & Wellness | `wellness` → /wellness | real (renamed) |
| 2 | Finance & Wealth | `nominal` → /nominal | real (renamed) |
| 3 | Time & Habits | `goals` → /goals | real (renamed) |
| 4 | Career & Business Growth | `career` → /career | real (renamed) |
| 5 | Relationships & Connection | `relationships` → /relationships | scaffold (categories.py) |
| 6 | Personal Growth & Learning | `growth` → /growth | scaffold (categories.py) |
| 7 | Vision Board & Purpose | `vision` → /vision | scaffold (categories.py) |
| 8 | Recreation, Fun & Travel | `trips` → /trips | real (renamed) |
| 9 | Legacy & Contribution | `legacy` → /legacy | scaffold (categories.py) |

`about` stays registered but `hidden` (utility/story page at /about).

## Retired from the Aria product but still registered (hidden)
`recipes`, `stocks`, `wins`, `body`, `wealth`, `dailybread` are **still in
`registry.py`** (marked `hidden`) and their routers are still mounted — so other
instances that need them keep working (e.g. **Nessa's Recipes**, **Chuck's Daily
Bread**). They're simply not on the Aria demo/default profiles, and hidden means
they aren't advertised in the "add more" catalog.

## How to bring one onto the Aria dashboard
Add its `key` to the relevant profile's `"modules"` list
(`dashboard/profiles/demo.json`, `default.json`, etc.). The dict is already in
`registry.py` and the router is already mounted — nothing else needed. (Remove the
`"hidden": True` from its registry dict if you also want it offered in the catalog.)

## Original names of the renamed modules
- `wellness`: "Wellness" 🌸 → "Health & Wellness" 🌿
- `nominal`: "Nominal" 💰 → "Finance & Wealth" 💰
- `goals`: "Goals" 🎯 → "Time & Habits" ⏱️
- `career`: "Career" 💼 → "Career & Business Growth" 📈
- `trips`: "Trips" ✈️ → "Recreation, Fun & Travel" 🌴
