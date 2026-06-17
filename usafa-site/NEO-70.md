# Add Hero Image to Landing Page

## Summary
Add a hero photograph to the top of the USAFA website landing page to create a stronger visual first impression for prospective cadets and visitors.

---

## Change

### 1. Add the image asset
Place the image file in the assets folder:

```
/assets/images/hero-landing.jpg
```

> **Reviewer:** Swap `hero-landing.jpg` for the actual filename/path once the photo is selected and approved.

---

### 2. HTML — Insert the hero section

Add the following block **immediately after the opening `<main>` tag** (or after the top navigation bar, before the existing page content):

```html
<!-- Hero Image Section -->
<section class="hero" aria-label="Welcome to the United States Air Force Academy">
  <img
    src="/assets/images/hero-landing.jpg"
    alt="Aerial view of the United States Air Force Academy campus, Colorado Springs, Colorado"
    class="hero__image"
    width="1920"
    height="800"
    loading="eager"
    fetchpriority="high"
  />
  <div class="hero__overlay">
    <h1 class="hero__headline">Integrity First. Service Before Self. Excellence in All We Do.</h1>
  </div>
</section>
```

---

### 3. CSS — Style the hero section

Add the following to your main stylesheet (e.g., `styles.css` or `main.css`):

```css
/* ── Hero Section ─────────────────────────────────── */
.hero {
  position: relative;
  width: 100%;
  max-height: 800px;
  overflow: hidden;
  display: block;
}

.hero__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center top;
  display: block;
}

.hero__overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: flex-end;
  padding: 2.5rem 3rem;
  background: linear-gradient(
    to top,
    rgba(0, 0, 0, 0.65) 0%,
    transparent 60%
  );
}

.hero__headline {
  color: #ffffff;
  font-size: clamp(1.25rem, 3vw, 2.25rem);
  font-weight: 700;
  max-width: 800px;
  margin: 0;
  text-shadow: 0 2px 6px rgba(0, 0, 0, 0.55);
  line-height: 1.3;
}

/* ── Responsive ───────────────────────────────────── */
@media (max-width: 768px) {
  .hero {
    max-height: 480px;
  }

  .hero__overlay {
    padding: 1.5rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero__image {
    animation: none;
    transition: none;
  }
}
```

---

## Notes

### ✅ Reviewer Checklist

| Item | Detail |
|---|---|
| **Image selection** | Confirm the chosen photo is cleared for public web use (DoD/USAFA public affairs approval). Recommended minimum resolution: **1920 × 800 px**. |
| **Alt text** | Update the `alt` attribute to accurately describe the specific photo chosen. Alt text must be descriptive for Section 508 compliance. |
| **Headline copy** | The Core Values are used as placeholder text. Replace or remove if the brand/comms team wants different copy — or remove `.hero__headline` entirely if the photo speaks for itself. |
| **Mobile** | Verify the image crops acceptably on phones (portrait orientation). Consider supplying a separate mobile-optimized crop via `<picture>` / `srcset` if the subject is off-center. |
| **Performance** | `loading="eager"` and `fetchpriority="high"` are set because this is above-the-fold. Ensure the file is compressed (target **< 250 KB** via WebP if the stack supports it). |
| **Accessibility** | Overlay text contrast meets **WCAG AA (4.5:1)**. The gradient + `text-shadow` combination on white text over a dark gradient satisfies this, but verify against the actual photo. |
| **Existing layout** | Confirm the new `<section>` does not conflict with any existing `<h1>` on the page — there should be only one `<h1>` per page. |