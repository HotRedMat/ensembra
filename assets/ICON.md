# Icon and screenshot requirements

This folder holds brand assets for marketplace submission. **Images are not yet created** — this file is a spec for what to produce before submitting to the official marketplace.

## Target files

```
assets/
├── icon-128.png        # 128x128 square, transparent background
├── icon-256.png        # 256x256 square, transparent background
├── icon-svg.svg        # vector source
├── social-preview.png  # 1280x640 for GitHub social card
├── screenshot-run.png       # /ensembra:run output
├── screenshot-config.png    # /ensembra:config interactive picker
└── screenshot-transfer.png  # /ensembra:transfer result
```

## Icon design brief

**Concept**: an ensemble — multiple instruments performing in concert, unified by a conductor.

**Visual metaphors to consider** (pick one or blend):
1. **Baton + concentric rings** — a conductor's baton at the center, with rings representing the 5 phases radiating outward
2. **Six notes on a staff** — six musical notes (one per performer) arranged on a staff, with a seventh note slightly offset (scribe)
3. **Abstract geometric** — six dots forming a hexagon around a central dot (conductor), connected by thin lines showing deliberation

**Palette suggestions**:
- Primary: deep indigo (`#3730a3`) — suggests focus and orchestration
- Accent: warm amber (`#f59e0b`) — suggests harmony and the "spark" of agreement
- Background: transparent, or very pale cream (`#fef3c7`) if a background is needed

**Style**:
- Flat / minimal (matches Claude Code's aesthetic)
- High contrast, works at 16x16 favicon size as well as 256x256
- No small text (unreadable at thumbnail sizes)

## Screenshot brief

All screenshots should be **clean terminal captures** with syntax highlighting:
- Font: a monospace with good Korean glyph coverage (D2Coding, JetBrains Mono KR, Sarasa Mono K)
- Theme: light or dark, consistent across screenshots
- No personal paths — use placeholders like `~/project` instead of `/Users/…`

**`screenshot-run.png`**: the final summary block from `/ensembra:run feature`, showing the "Ensembra Run — feature" heading, consensus %, changed files, reuse evaluation section. ~30 lines.

**`screenshot-config.png`**: the Reuse-First Policy submenu showing the Quick Select menu and Custom checkboxes, with an active cascade message. ~25 lines.

**`screenshot-transfer.png`**: the table of contents from a generated `docs/transfer/*.md` file, showing sections 0–10 and the devils-advocate "주의할 함정" header expanded with 2–3 bullet points. ~30 lines.

## Social preview brief

**`social-preview.png`** (1280x640) for GitHub "Social preview":
- Background: subtle gradient from indigo to black
- Left side: Ensembra icon (the larger version)
- Right side: title `Ensembra` in large white serif or sans-serif, subtitle `Multi-agent orchestrator for Claude Code` in smaller muted white
- Bottom right: small `v0.1.0` version badge

## How to produce these

Ensembra doesn't ship binary assets. Contributors are welcome to design them and open a PR. When you do:

1. Export PNG at the listed resolutions
2. Optimize with `pngquant` or `oxipng` for small file sizes
3. Place in `assets/` following the filenames above
4. Update this file to change status from "not yet created" to "current"
5. Update `README.md` header badges to reference the new icon (if applicable)

## Licensing

Any icon or screenshot committed to this repo must be either:
- Original work by the contributor, licensed MIT (matching the project)
- Derived from MIT / CC0 / public domain assets with attribution in this file

No proprietary fonts, stock photos with restrictive licenses, or AI-generated images from services with unclear terms.

## Status

**Not yet created.** Marketplace submission will wait for at least `icon-128.png`, `icon-256.png`, and one screenshot.
