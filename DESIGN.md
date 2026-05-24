---
name: Voxpost
description: Local Gmail companion — calm editorial minimalism for an audio-first product.
colors:
  ink: "#121214"
  slate: "#45454F"
  muted: "#5E5E68"
  paper: "#FAFAF8"
  surface: "#FFFFFF"
  line: "#C4C4BC"
  line-subtle: "#E4E4DE"
  accent: "#121214"
  accent-hover: "#2A2A32"
  on-accent: "#FFFFFF"
  link: "#0A5C55"
  link-hover: "#083F3A"
  ink-dark: "#F2F2F0"
  slate-dark: "#C8C8D0"
  muted-dark: "#A0A0AA"
  paper-dark: "#0C0C0E"
  surface-dark: "#18181C"
  line-dark: "#52525C"
  line-subtle-dark: "#2E2E36"
  accent-dark: "#F2F2F0"
  accent-hover-dark: "#DCDCE4"
  on-accent-dark: "#0C0C0E"
  link-dark: "#5EEAD4"
  link-hover-dark: "#99F6E4"
typography:
  display:
    fontFamily: Newsreader
    fontSize: 3.5rem
    fontWeight: "500"
    lineHeight: 1.08
    letterSpacing: -0.03em
  headline:
    fontFamily: Newsreader
    fontSize: 1.35rem
    fontWeight: "500"
    lineHeight: 1.35
    letterSpacing: -0.01em
  body-lg:
    fontFamily: DM Sans
    fontSize: 1.125rem
    fontWeight: "400"
    lineHeight: 1.65
  body-md:
    fontFamily: DM Sans
    fontSize: 1rem
    fontWeight: "400"
    lineHeight: 1.6
  label-caps:
    fontFamily: DM Sans
    fontSize: 0.6875rem
    fontWeight: "600"
    lineHeight: 1.2
    letterSpacing: 0.12em
  label-md:
    fontFamily: DM Sans
    fontSize: 0.875rem
    fontWeight: "600"
    lineHeight: 1.25
rounded:
  sm: 4px
  md: 8px
  lg: 12px
spacing:
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  xxl: 64px
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: 12px 20px
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-ghost:
    backgroundColor: transparent
    textColor: "{colors.ink}"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: 12px 20px
  hero-section:
    backgroundColor: "{colors.paper}"
    typography: "{typography.display}"
---

## Overview

Quiet confidence for an audio-first tool. The UI should feel like a premium broadsheet or a well-edited product page — not a generic SaaS template. Typography carries the brand; color stays restrained. Buttons use ink-on-paper contrast; teal is for links and focus only.

## Colors

- **Ink (#121214):** Headlines, primary text, and primary button fill.
- **Slate (#45454F):** Lead copy, captions, metadata — WCAG AA on paper.
- **Paper (#FAFAF8):** Page background — warmer than white, softer than gray.
- **Line (#C4C4BC):** Visible borders for buttons, search, and dividers.
- **Accent (#121214):** Primary buttons — white label on ink (light) or ink label on paper (dark).
- **Link (#0A5C55 / #5EEAD4 dark):** Inline links and focus rings only.

Dark mode inverts surfaces; buttons flip to light fill with dark text for the same contrast ratio.

## Typography

- **Newsreader** for the hero and section titles — editorial gravitas, not startup bold.
- **DM Sans** for body, labels, and UI chrome — neutral, readable, modern.
- **JetBrains Mono** for commands and code only.

## Layout

Mobile-first, generous whitespace. Hero is left-aligned on desktop with a max readable measure (~36rem for lead). Value props use a simple three-column grid with hairline separators, not icon cards. Terminal screenshot sits in a thin bordered frame — no drop-shadow stacks.

## Do's and Don'ts

**Do:** Short lines, one idea per block, docs in the header nav, 8px button radius.

**Don't:** Purple gradients, pill badges, decorative unicode icons, floating card hover lifts, or marketing filler.
