---
name: PolicyScope
colors:
  surface: '#f8f9ff'
  surface-dim: '#c9dcf7'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eef4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dbe9ff'
  surface-container-highest: '#d1e4ff'
  on-surface: '#081d30'
  on-surface-variant: '#434655'
  inverse-surface: '#1f3246'
  inverse-on-surface: '#eaf1ff'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#006a63'
  on-secondary: '#ffffff'
  secondary-container: '#99efe5'
  on-secondary-container: '#006f67'
  tertiary: '#3e3fcc'
  on-tertiary: '#ffffff'
  tertiary-container: '#585be6'
  on-tertiary-container: '#f1eeff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#9cf2e8'
  secondary-fixed-dim: '#80d5cb'
  on-secondary-fixed: '#00201d'
  on-secondary-fixed-variant: '#00504a'
  tertiary-fixed: '#e1e0ff'
  tertiary-fixed-dim: '#c0c1ff'
  on-tertiary-fixed: '#07006c'
  on-tertiary-fixed-variant: '#2f2ebe'
  background: '#f8f9ff'
  on-background: '#081d30'
  surface-variant: '#d1e4ff'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  display-md:
    fontFamily: Inter
    fontSize: 26px
    fontWeight: '600'
    lineHeight: 32px
  headline-sm:
    fontFamily: Noto Sans
    fontSize: 20px
    fontWeight: '500'
    lineHeight: 28px
  body-lg:
    fontFamily: Noto Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Noto Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  metric-value:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 32px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  grid_columns: '12'
  gutter: 24px
  margin: 32px
  unit: 8px
  max_width: 1440px
---

## Brand & Style
The design system for this policy simulation workbench is built on a foundation of **Modern Institutionalism**. It avoids the visual cliches of "big data" dashboards (glows, dark-mode neon, glassmorphism) in favor of a high-density, rational, and authoritative workspace.

The brand personality is that of a "Strategic Command Center"—calculated, precise, and forensic. The aesthetic utilizes a clean, light-mode interface with a structured 1:1 information-to-ink ratio, ensuring that complex manufacturing policy data is legible and actionable. It prioritizes clarity and institutional trust through a neutral color profile and a rigorous alignment system.

## Colors
The palette is functional and semantic, designed to segment information by its "source of truth":
- **Deep Navy (#0B1F33):** Used for structural headers and high-level navigation to establish authority.
- **Steady Blue (#2563EB):** Reserved for primary interactive elements and systemic actions.
- **Teal (#0F766E):** Represents "Ground Truth"—verified manufacturing data and historical environmental benchmarks.
- **Indigo (#6366F1):** Identifies AI-generated insights, predictive simulations, and pending content.
- **Amber & Restrained Red:** Used strictly for fiscal pressure indicators and severe manufacturing risks.

Surface colors utilize a layered gray scale to differentiate the workbench's zones without relying on heavy borders.

## Typography
The system employs a dual-font strategy. **Inter** is used for all quantitative data, English labels, and core metrics to provide a technical, clean look. **Noto Sans SC** (Source Han Sans) handles all Chinese prose and descriptive text, ensuring high legibility for policy documents.

Hierarchy is strictly enforced. Large display styles are reserved for aggregate totals and system titles. Body text is kept at a compact 14px to support the high data density required for a workbench environment, while "Label-caps" are used for metadata like agent types (CENTRAL, PROVINCIAL).

## Layout & Spacing
The layout follows a strict 12-column fluid grid, optimized for a 1440px width. The workbench is divided into three functional zones:
1.  **Global Navigation/Timeline (Top):** Fixed height, containing the stage timeline and global search.
2.  **Context Sidebar (Left):** 3-column span for simulation parameters and agent settings.
3.  **Analysis Canvas (Center/Right):** 9-column span for core metric cards, maps, and flow cards.

Spacing is based on an 8px modular unit. Gutters are fixed at 24px to ensure distinct separation between data-heavy containers. Use white space to group related policy clusters rather than physical separators where possible.

## Elevation & Depth
Elevation is used sparingly to maintain the "workbench" feel. The system utilizes **Tonal Layers** and subtle shadows:
- **Level 0 (Background):** #F4F6F8. The base for all components.
- **Level 1 (Cards):** White background with a 1px border (#E2E8F0) and a soft, low-blur shadow (Y: 2px, Blur: 4px, Opacity: 0.05).
- **Level 2 (Active/Hover):** Increased shadow depth to indicate interactivity.
- **Level 3 (Modals/Overlays):** Used for evidence citation panels and deep-dive diffs.

Avoid any "pop-out" neomorphic effects. All surfaces should appear flat and structurally sound.

## Shapes
The shape language is "Soft-Modern." A standard 8px radius (`rounded-md`) is applied to cards and input fields, while buttons and tags use a 12px (`rounded-lg`) radius to provide a more approachable, human-centric feel for interactive elements.

- **Primary Buttons:** 12px radius.
- **Data Cards:** 8px radius.
- **Metric Chips:** Pill-shaped (fully rounded).

## Components
- **Status Tags:** Use a combination of a small leading icon and text. Backgrounds should be low-saturation (10% opacity of the semantic color) with a high-contrast label.
- **Agent Labels:** (Central, Provincial, Enterprise) should be rendered as small, uppercase labels in Inter, color-coded by the secondary Teal palette.
- **Core Metric Cards:** Feature a top-aligned label, a centered 28px Inter font value, and a bottom-aligned "sparkline" or "diff" indicator (comparing AI prediction vs. verified data).
- **Policy Parameter Sliders:** Use a customized track in Indigo (to signify simulation) with a numeric tooltip showing real-time impact.
- **Structured Event Flow:** A vertical timeline component using 1px gray lines and small circular nodes. Each node expands into a card detailing a policy "ripple" event.
- **Evidence Citation Tags:** Small, underlined Teal text or book-icon buttons that open a side-drawer with source policy documents.
- **Icons:** 20px linear icons with a 1.5px stroke width. No filled versions except for active state indicators.