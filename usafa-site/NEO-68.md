# Summary

Add a linked USAFA website entry to the developer resources page.

---

# Change

Add the following block to the developer resources page in the appropriate site-listing section (e.g., alongside other official links or external resources):

```html
<!-- USAFA Official Website -->
<li class="resource-item">
  <a
    href="https://www.usafa.edu"
    target="_blank"
    rel="noopener noreferrer"
    aria-label="U.S. Air Force Academy official website (opens in new tab)"
  >
    U.S. Air Force Academy
  </a>
  <span class="resource-meta">Official USAFA website — usafa.edu</span>
</li>
```

If the page uses a `<ul>` or `<ol>` resource list, drop this `<li>` into that list. If the page uses a card/grid layout instead, use the equivalent pattern below:

```html
<!-- USAFA Official Website (card variant) -->
<div class="resource-card">
  <a
    href="https://www.usafa.edu"
    target="_blank"
    rel="noopener noreferrer"
    aria-label="U.S. Air Force Academy official website (opens in new tab)"
  >
    <h3 class="resource-title">U.S. Air Force Academy</h3>
  </a>
  <p class="resource-description">
    Official USAFA website — <code>usafa.edu</code>
  </p>
</div>
```

---

# Notes

| Item | Detail |
|---|---|
| **URL** | Confirm `https://www.usafa.edu` resolves correctly and redirects are stable before merging. |
| **`target="_blank"`** | Paired with `rel="noopener noreferrer"` to prevent tab-napping security risk. |
| **`aria-label`** | Announces "(opens in new tab)" to screen-reader users per WCAG 2.1 SC 2.4.4 (Link Purpose). |
| **Mobile** | No layout-specific changes required; entry inherits existing list/card responsive styles. |
| **Section 508** | Link text is descriptive and unique on the page — no "click here" patterns used. |
| **Approver action** | Click the link in a staging environment to verify destination before shipping. |