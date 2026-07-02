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

## Retired but preserved (code intact, not in catalog)
`recipes`, `stocks`, `wins`, `body`, `wealth`, `dailybread`.

## How to bring one back
1. Re-add its dict to `MODULES` in `registry.py` (originals below).
2. Add its `key` to the relevant profile's `"modules"` list
   (`dashboard/profiles/demo.json`, `default.json`, etc.).
That's it — routers are already mounted.

## Original module dicts (copy-paste to restore)
```python
{"key": "recipes", "icon": "🍴", "name": "Recipes", "path": "/recipes",
 "description": "Save your favorite recipes — bookmark any from the web with a tap.",
 "version": "1.0", "released": "2026-06-27", "requires": []},
{"key": "stocks", "icon": "📈", "name": "Stocks", "path": "/stocks",
 "description": "Sector watchlist with daily AI briefings.",
 "version": "1.0", "released": "2026-06-16", "requires": ["anthropic"]},
{"key": "wins", "icon": "🌟", "name": "Wins", "path": "/wins",
 "description": "Daily wins with AI recognition.",
 "version": "1.0", "released": "2026-06-16", "requires": ["anthropic"]},
{"key": "body", "icon": "🫀", "name": "Body", "path": "/body",
 "description": "Meds, weight journey, and habits — private by default.",
 "version": "1.0", "released": "2026-06-17", "requires": []},
{"key": "wealth", "icon": "📊", "name": "Wealth", "path": "/wealth",
 "description": "Investments + retirement projections, with audience masking.",
 "version": "1.0", "released": "2026-06-17", "requires": []},
{"key": "dailybread", "icon": "🕊️", "name": "Daily Bread", "path": "/daily-bread",
 "description": "A daily verse, a family photo wall, and a prayer list.",
 "version": "1.0", "released": "2026-06-21", "requires": [], "hidden": True},
```

## Original names of the renamed modules
- `wellness`: "Wellness" 🌸 → "Health & Wellness" 🌿
- `nominal`: "Nominal" 💰 → "Finance & Wealth" 💰
- `goals`: "Goals" 🎯 → "Time & Habits" ⏱️
- `career`: "Career" 💼 → "Career & Business Growth" 📈
- `trips`: "Trips" ✈️ → "Recreation, Fun & Travel" 🌴
