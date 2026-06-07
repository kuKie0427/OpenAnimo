---
name: OpenAnimo
description: "AI 漫剧生成平台：故事创意 → 3 Agent 协作 → 可视化漫剧成片"
colors:
  projection-amber: "#F5A623"
  projection-amber-content: "#1A1A12"
  gate-red: "#CC3333"
  gate-red-content: "#ffffff"
  lamp-blue: "#4A90D9"
  lamp-blue-content: "#ffffff"
  projection-black: "#0D0D12"
  projection-black-content: "#D4D4E0"
  screen-surface: "#14141C"
  film-gate: "#1C1C28"
  screen-text: "#D4D4E0"
  screen-muted: "#8888A0"
  rushes-cream: "#F4F1E8"
  rushes-linen: "#EBE7DA"
  rushes-ecru: "#DED9C8"
  rushes-text: "#1E1E2A"
  dark-projection-amber: "#F7C04A"
  dark-gate-red: "#D94A4A"
  dark-lamp-blue: "#5CA8E9"
  semantic-success: "#4CAF7D"
  semantic-warning: "#E8943A"
  semantic-error: "#D94848"
  semantic-info: "#5CA8E9"
typography:
  display:
    fontFamily: "Playfair Display, Georgia, serif"
    fontSize: "clamp(2rem, 5vw, 4rem)"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.005em"
  title:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "1.125rem"
    fontWeight: 500
    lineHeight: 1.25
  body:
    fontFamily: "Source Sans 3, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: "JetBrains Mono, Menlo, monospace"
    fontSize: "0.6875rem"
    fontWeight: 500
    letterSpacing: "0.06em"
    textTransform: "uppercase"
rounded:
  none: "2px"
  sm: "3px"
  md: "4px"
  lg: "6px"
  xl: "8px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  2xl: "48px"
  3xl: "64px"
components:
  button-primary:
    backgroundColor: "{colors.projection-amber}"
    textColor: "{colors.projection-amber-content}"
    rounded: "{rounded.sm}"
    padding: "10px 24px"
    border: "1px solid oklch(from {colors.projection-amber} calc(l * 0.85) c h)"
  button-primary-hover:
    backgroundColor: "{colors.dark-projection-amber}"
    boxShadow: "0 0 24px oklch(from {colors.projection-amber} l c h / 0.3)"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.screen-text}"
    rounded: "{rounded.sm}"
    border: "1px solid oklch(from {colors.screen-text} l c h / 0.25)"
  button-accent:
    backgroundColor: "{colors.lamp-blue}"
    textColor: "{colors.lamp-blue-content}"
    rounded: "{rounded.sm}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.screen-muted}"
    rounded: "{rounded.sm}"
  card-screen:
    backgroundColor: "{colors.screen-surface}"
    rounded: "{rounded.lg}"
    border: "1px solid oklch(from {colors.screen-text} l c h / 0.06)"
  card-feature:
    backgroundColor: "{colors.film-gate}"
    rounded: "{rounded.xl}"
    border: "1px solid oklch(from {colors.projection-amber} l c h / 0.12)"
  input-field:
    backgroundColor: "{colors.film-gate}"
    rounded: "{rounded.sm}"
    border: "1px solid oklch(from {colors.screen-text} l c h / 0.12)"
---

# Design System: OpenAnimo · The Projection Room

## 1. Overview

**Creative North Star: "The Projection Room"**

A film projection booth at midnight. The room is dark. The only light comes from the projector beam cutting through the darkness, casting warm amber onto the screen. This is a space of focus, anticipation, and craft — not a tool dashboard, but a screening room where stories come to life.

The system speaks one language: **cinematic atmosphere**. Every design choice answers "does this feel like a darkened screening room where films are made and watched?" The interface is the projection booth, the content is the film. UI elements are equipment in the booth — visible when needed, receding into darkness when not.

**Key Characteristics:**
- Dark-first: the room is always dimmed, content is the light source
- Projection amber as the sole warm anchor — the projector bulb glowing in the dark
- Diffuse atmospheric glows replace hard shadows — light scattering through a lens, not ink on paper
- Thin, precise borders (1px) replace bold comic outlines — the fine edge of a film gate, not a marker stroke
- Opacity-based hover states — a dimmer switch, not a physical press
- Film grain textures as surface identity — the celluloid medium, not the printed page
- Sharp, refined corners (2–8px) — precision equipment, not rounded craft tools

This system explicitly rejects three aesthetics: the warm comic workshop (the old OpenAnimo), the grey SaaS panel (Notion/Jira coldness), and the generic AI generator (white card grids + purple gradients). If it looks like a comic book, it's stuck in the old direction. If it looks like a Jira ticket, the atmosphere is missing. If it looks like a Midjourney landing page, the personality is missing.

---

## 2. Colors

The palette is a projection booth at night: deep charcoal blacks serve as the darkened room, projection amber is the sole warm light source punching through, and cool blue-grey tints provide the structural depth of equipment in low light. No CMYK plates, no warm paper tones — this is light in darkness, not ink on paper.

### Primary
- **Projection Amber** (#F5A623): The projector bulb. Primary action buttons, active states, progress markers, the warm pulse in the dark. The only warm color in the system. Dark mode shifts to #F7C04A with increased luminance to maintain punch against the dark room.

### Secondary
- **Gate Red** (#CC3333): The recording indicator, the darkroom safe light. Secondary emphasis, destructive actions, error states, attention markers. A narrow, specific red — like the LED on a camera, not a broad accent. Dark mode shifts to #D94A4A.

### Tertiary
- **Lamp Blue** (#4A90D9): Equipment indicator lights, structural accents, info states. A cool, precise blue like the glow of a mixing board LED. Used sparingly — never competes with projection amber. Dark mode shifts to #5CA8E9.

### Neutral
- **Projection Black** (#0D0D12): Base-100 surface. The darkened room itself. Deep charcoal with a subtle blue undertone — not pure black, not warm black. The foundation everything sits on.
- **Screen Surface** (#14141C): Base-200 surface. Sidebar backgrounds, panel surfaces. One step above the room darkness, like the faint glow of equipment racks.
- **Film Gate** (#1C1C28): Base-300 surface. Elevated surfaces, input backgrounds, card containers. The brightest dark — like a film gate illuminated from within.
- **Screen Text** (#D4D4E0): Primary text. Cool white with a hint of blue — like projected subtitles, never warm paper.
- **Screen Muted** (#8888A0): Secondary text, placeholders, metadata. Dimmed, like equipment labels in low light.

### Light Variant: "Rushes Room"
For daylight use or preference, a light variant exists — the screening room with the house lights partially up for reviewing dailies:
- **Rushes Cream** (#F4F1E8): Base-100 light surface. Warm off-white with zero yellow tint — morning light through frosted glass, not aged paper.
- **Rushes Linen** (#EBE7DA): Base-200 light surface. Panel and sidebar backgrounds.
- **Rushes Ecru** (#DED9C8): Base-300 light surface. Input backgrounds, elevated cards.
- **Rushes Text** (#1E1E2A): Primary text in light mode. Deep charcoal, not pure black.

### Named Rules

**The One Warm Light Rule.** Projection Amber is the only warm color in the entire system. No warm tints on neutrals, no warm accent variants, no warm hover states on non-primary elements. The projector bulb is singular. If something else glows warm, it competes with the primary action and dilutes the atmosphere. The system is built on cool darkness; the warmth is a signal, not a mood.

**The Cool Neutral Rule.** Every neutral is tinted toward the blue axis (hue ~240–260 in OKLCH). Pure grey, warm grey, or yellow-tinted neutrals are prohibited. The room is lit by equipment — blue-white LEDs, not incandescent bulbs. If a neutral could feel "cozy" or "warm," it needs more blue.

**The Registration Rule.** The three accent colors follow a fixed hierarchy: Amber for primary action (the projector), Red for attention/destruction (the recording light), Blue for structure/info (the equipment). No role-swapping. No "use blue because it looks nice here." The projection booth has a fixed panel of indicator lights — they don't change meaning.

---

## 3. Typography

**Display Font:** Playfair Display (Georgia fallback)
**Heading Font:** Cormorant Garamond (Georgia fallback)
**Body Font:** Source Sans 3 (system-ui fallback)
**Label/Mono Font:** JetBrains Mono (Menlo fallback)

**Character:** The pairing is a film credit sequence: Playfair Display carries the title card with editorial gravitas, Cormorant Garamond handles the cast and crew with refined precision, Source Sans 3 does the body work with clean readability, and JetBrains Mono marks the technical data — timecodes, frame numbers, equipment labels. No comic fonts, no handwriting, no rounded terminals. This is a projection booth, not a sketchbook.

### Hierarchy
- **Display** (700, clamp(2rem, 5vw, 4rem), line-height 1.05): Film title cards. Hero section headlines. Splash text. The only place Playfair Display is used. Letter-spacing -0.01em for optical tightness at large sizes. Appears at most once per screen.
- **Headline** (600, 1.5rem, line-height 1.15): Section titles, modal headers, sidebar project names. Cormorant Garamond at its most structured. Letter-spacing -0.005em.
- **Title** (500, 1.125rem, line-height 1.25): Card titles, button labels (non-primary), toast headings. Cormorant Garamond at medium weight.
- **Body** (400, 0.9375rem, line-height 1.65): All running text. Paragraphs, descriptions, chat messages. Max line length 60–70ch. Source Sans 3 for maximum readability at length.
- **Label** (500, 0.6875rem, letter-spacing 0.06em, uppercase): Status indicators, metadata, timestamps, technical identifiers. JetBrains Mono exclusively. Uppercase for timecode precision.

### Named Rules

**The One Display Rule.** Playfair Display appears at most once per screen. If a second element needs display weight, use Cormorant Garamond 600 at headline size. Display type that appears twice is display type that has lost its title-card impact.

**The Mono-for-Data Rule.** JetBrains Mono is reserved for status labels, timestamps, technical identifiers, and code. Never use it for button labels, headings, or body text. If it could appear on a film slate, it belongs in Mono. If it reads like a sentence, it does not.

**The No Handwriting Rule.** Decorative script, cursive, and handwriting fonts are prohibited. The projection booth is precision equipment. Margin notes are typed, not hand-lettered. Personality comes from atmosphere, not simulated handwriting.

---

## 4. Elevation & Atmosphere

The Projection Room uses light, not shadow, to communicate elevation. Elements don't cast shadows — they emit or catch light. The model is a darkened room where surfaces are visible only by the projector beam or equipment glow.

### Glow Vocabulary
- **Aperture** (`0 0 1px oklch(from var(--bc) l c h / 0.08), 0 0 8px oklch(from var(--bc) l c h / 0.04)`): Default card elevation. Subtle inner glow like a surface catching stray light. Used on card-screen.
- **Gate Glow** (`0 0 0 1px oklch(from var(--p) l c h / 0.12), 0 0 20px oklch(from var(--p) l c h / 0.08)`): Feature card elevation. A thin amber border-glow, like the edge of a film gate illuminated. Used on card-feature.
- **Projection** (`0 0 40px oklch(from var(--p) l c h / 0.15), 0 0 80px oklch(from var(--p) l c h / 0.06)`): Hover state glow. The projector brightens — light expands outward without moving the element.
- **Beam** (`0 0 2px oklch(from var(--a) l c h / 0.15), 0 0 12px oklch(from var(--a) l c h / 0.06)`): Accent glow in lamp blue. Equipment indicator illumination.
- **Signal** (`0 0 2px oklch(from var(--s) l c h / 0.2), 0 0 6px oklch(from var(--s) l c h / 0.08)`): Gate red glow for attention states. The recording light pulses.

### Tonal Layering
- **Dark mode** (default): Three depths of the projection room — Projection Black (#0D0D12) for the deepest background, Screen Surface (#14141C) for panels, Film Gate (#1C1C28) for elevated surfaces. No shadows between layers — the tonal shift alone creates depth, like different distances from the projector.
- **Light mode** (Rushes Room): Three cream surfaces — Rushes Cream (#F4F1E8), Rushes Linen (#EBE7DA), Rushes Ecru (#DED9C8). Glow effects reduce to subtle border highlights; the atmosphere shifts from "dark room" to "morning screening."

### Texture
- **Film Grain**: A subtle SVG noise filter (`feTurbulence` with `feColorMatrix`) applied at 3–5% opacity over the base background. Higher opacity (6–8%) on hero sections. Simulates the celluloid surface — the medium itself.
- **Vignette**: A radial gradient from transparent to `projection-black` at 15% opacity, applied to the outermost 20% of the viewport. Darkens the periphery, focuses attention on center content. Disabled in light mode.
- **Scanline** (optional, decorative): A 2px repeating linear gradient at 1–2% opacity on feature cards. A subtle nod to projection equipment without going retro. Disabled in light mode.

### Named Rules

**The Light-Is-Elevation Rule.** Glow intensity communicates hierarchy, not decoration. A card-feature with Gate Glow has higher visual weight than a card-screen with Aperture. Removing a glow changes the element's hierarchy, not just its decoration. Never remove a glow for aesthetics alone.

**The Still-At-Rest Rule.** Elements do not translate on hover. No lift, no press, no physical displacement. The projection booth has fixed equipment — it doesn't move. Interaction is signaled by glow expansion and opacity shifts only: hover brightens (glow radius increases, background lightens 2–4%), active dims (glow collapses, background darkens 2–4%). The model is a dimmer switch, not a button press.

**The No-Shadow Rule.** Box-shadow with offset (X or Y > 0) is prohibited. Shadows that simulate light falling on objects belong in the physical world. The Projection Room is a space of emitted and scattered light — all glows are centered (0 offset), diffuse, and atmospheric. If a shadow has direction, it breaks the projection booth illusion.

---

## 5. Components

### Buttons
- **Shape:** Sharp (3px radius), thin 1px border, no uppercase (labels use Cormorant Garamond 500)
- **Primary (Projection Amber):** `btn-projection` with `bg-primary text-primary-content`. 1px border in darkened amber. Aperture glow at rest. Padding: 10px 24px.
- **Secondary (Ghost):** Transparent background, 1px border in `screen-text/25`, `screen-text` color. No glow at rest. Hover adds `bg-screen-surface` and subtle Aperture glow.
- **Accent (Lamp Blue):** `bg-accent text-accent-content`. Beam glow at rest. Used for informational actions, settings, links.
- **Destructive (Gate Red):** `bg-secondary text-secondary-content`. Signal glow at rest.
- **Hover:** Glow expands — Aperture → Projection scale for primary, background fills in for ghost. No translate. Transition: 200ms ease-out.
- **Active:** Glow collapses to none. Background darkens 4%. No translate. The dimmer dips.
- **Disabled:** 40% opacity, cursor-not-allowed. No hover or active transitions.
- **Loading:** A 2px amber ring spinner (border animation) replaces content. All interaction blocked.

### Cards / Containers
- **card-screen:** Rounded-lg (6px), 1px border in `screen-text/6`, Aperture glow. Background: Screen Surface. Hover: glow expands to 12px radius, border brightens to `screen-text/12`. The default card for content sections. Padding: 24px standard, 16px compact.
- **card-feature:** Rounded-xl (8px), 1px border in `projection-amber/12`, Gate Glow (amber tinted). Background: Film Gate. Hover: gate glow expands to Projection scale. The identity card for hero content, featured sections, canvas. Padding: 32px.

### Inputs / Fields
- **input-field:** 1px border in `screen-text/12`, rounded-sm (3px), Film Gate background. Placeholder text in `screen-muted`. Focus: border shifts to Projection Amber, adds Aperture glow. No ring, no outline — just a decisive border-color and glow transition.
- **Error state:** Border shifts to Gate Red (#CC3333). Error message in Gate Red below, font-label.
- **Label:** Cormorant Garamond 500, `screen-text` color, sitting above the input with 8px gap. Optional: a faint amber dot to the left when the field is focused.

### Chips / Tags
- **Style:** Rounded-sm (3px), 1px border, Screen Surface background. No glow at rest.
- **State:** Unselected: Screen Surface bg, `screen-muted` text, `screen-text/10` border. Selected: `projection-amber/10` bg, Projection Amber text, Projection Amber border. Hover (unselected): border brightens to `screen-text/20`.
- **Removable:** An × icon in `screen-muted`, hover turns Gate Red. No background fill on hover.

### Navigation
- **Sidebar:** 240px fixed panel, Screen Surface background. 1px right border in `screen-text/6`. Active project: no left border accent — instead, the project name glows in Projection Amber (text color shift + subtle text-shadow). Project names in Cormorant Garamond 600. Delete button (Gate Red) revealed on hover only, opacity transition 150ms. The entire sidebar has a subtle right-edge vignette.
- **TopBar:** 44px height, 1px bottom border in `screen-text/8`. Stage indicators: small amber dots (6px) connected by 1px `screen-text/15` lines. Active stage: dot becomes Projection Amber with Aperture glow, label shifts to `screen-text`. Inactive: `screen-muted` dot and label. Labels in JetBrains Mono Label size.
- **Project Switcher:** Horizontal row of project titles above the canvas. Active project underlined with a 1px Projection Amber line that extends on hover (width transition 200ms).

### Chat Messages
- **message-ai:** Rounded-lg (6px), Film Gate background, 1px border in `screen-text/6`. Left-aligned. A subtle 1px amber left edge (not a stripe — a 1px inset border-left) as the "incoming" indicator. Body in Source Sans 3, timestamp in JetBrains Mono Label.
- **message-user:** Rounded-lg (6px), `projection-amber/8` background, 1px border in `projection-amber/15`. Right-aligned. No directional arrow — alignment alone distinguishes sender. The amber tint is the ownership signal.
- **System message:** Centered, no background, no border, `screen-muted` color, JetBrains Mono Label. For "Agent started," "Phase complete" status lines — like a timecode burn-in.

### Film Grain Backgrounds
- **grain-subtle:** SVG noise at 3% opacity over any surface. Default atmospheric texture for the entire application.
- **grain-hero:** SVG noise at 6% opacity + vignette overlay. Hero sections and feature cards. The grain is denser, the vignette draws focus to center.
- **grain-dense:** SVG noise at 8% opacity + scanline overlay at 1.5%. Canvas background and focused work areas. Creates a distinct "this is the work surface" identity.
- **Light mode:** All grain opacities reduce by 50% (3%→1.5%, 6%→3%, 8%→4%). Scanlines disabled entirely. The rushes room is cleaner.

### Progress & Status
- **Progress Bar:** 2px height, Film Gate background track. Fill in Projection Amber with a subtle animated gradient shimmer (the "projector warming up" effect). No rounded caps — sharp ends.
- **Stage Indicator (TopBar):** See Navigation → TopBar.
- **Status Badge:** JetBrains Mono Label, uppercase. "RECORDING" in Gate Red with Signal glow. "STANDBY" in `screen-muted`. "RENDERING" in Lamp Blue with Beam glow. Like equipment status LEDs.
- **Spinner:** 2px border ring in `screen-text/15`, with one quadrant in Projection Amber. Smooth rotation. No daisyUI dependency — pure CSS.

---

## 6. Do's and Don'ts

### Do:
- **Do** use Projection Amber as the singular warm light in the interface. Everything else is cool dark — the amber is the signal.
- **Do** use glow expansion (increased blur radius) to signal hover, and glow collapse to signal active. The dimmer switch model.
- **Do** tint all neutrals cool (toward the blue axis, hue ~240–260). Warm neutrals belong in living rooms, not projection booths.
- **Do** use film grain textures as atmospheric depth, especially on hero sections and canvas — the celluloid surface is the identity.
- **Do** keep Playfair Display to one appearance per screen. The title card loses impact with repetition.
- **Do** align chat messages by sender (AI left, user right) without speech bubbles or directional arrows. The alignment IS the direction.
- **Do** increase glow radius and grain opacity in dark mode for atmosphere; reduce both in light mode for clarity.
- **Do** use JetBrains Mono only for status labels, timestamps, timecodes, and technical identifiers.
- **Do** use thin 1px borders as the only structural line weight. No 3px comic outlines.
- **Do** let content be the brightest thing on screen. UI recedes; the film is the light source.

### Don't:
- **Don't** use directional box-shadows (any X/Y offset). The projection booth has no sun, no overhead light, no cast shadows. Only centered atmospheric glows.
- **Don't** create grey SaaS panels. If a sidebar looks like it belongs in Jira, it needs more atmosphere — grain, vignette, or depth.
- **Don't** use generic AI tool aesthetics: white card grids with purple gradients are the antithesis of a darkened screening room.
- **Don't** use decorative script, cursive, or handwriting fonts. No Caveat, no comic fonts. This is precision equipment.
- **Don't** use border-left or border-right accent stripes thicker than 1px. Use glow, background tint, or text color to signal active state.
- **Don't** use gradient text (`background-clip: text`). Solid colors only. The projector doesn't tint the subtitles.
- **Don't** use glassmorphism (backdrop-blur, translucent panels) as default surface treatment. The projection booth has solid equipment, not ghost panels.
- **Don't** translate elements on hover or active. The booth is fixed equipment. Glow and opacity are the only interaction signals.
- **Don't** use display fonts (Playfair Display) in UI labels, buttons, or data. Display is for the title card, not for the control panel.
- **Don't** use bold borders (2px+). The film gate is a fine edge. Thick borders are comic book outlines — the old system.
- **Don't** tint neutrals warm. No cream, no ecru, no yellow-tinged greys. The room is lit by equipment — blue-white, not incandescent.
- **Don't** use rounded corners above 8px. Sharp edges are precision instruments. Large radii are soft toys.
- **Don't** use more than one warm color. Projection Amber is singular. If a second warm appears, it dilutes the projector's signal.
- **Don't** use uppercase on button labels or headings. Uppercase is reserved for JetBrains Mono status labels — timecode precision, not emphasis.
- **Don't** reinvent standard affordances (custom scrollbars, weird form controls, non-standard modals). The projection booth has standard equipment — the magic is in the film, not the furniture.

---

## 7. Motion

### Principles
- **Fade, Don't Move.** The projection booth has fixed equipment. Transitions use opacity, not translation. A new scene fades in; it doesn't slide in.
- **200ms Default.** All interactive transitions (hover, focus, active) use 200ms ease-out. Page transitions use 300ms ease-out.
- **Staggered Reveal.** On page load, content reveals top-to-bottom with 50ms stagger delays and 300ms fade-in. Simulates the projector warming up — first the room, then the title, then the content.
- **No Bounce, No Spring.** Easing curves are `ease-out` (decelerating) or `ease-in-out` for larger transitions. No overshoot, no bounce physics. The projection booth is precise, not playful.

### Specific Transitions
- **Page Enter:** Opacity 0→1 over 300ms ease-out. Content children stagger with 50ms delays.
- **Page Exit:** Opacity 1→0 over 150ms ease-in. No stagger — the projector cuts, not fades.
- **Modal Open:** Backdrop fades in (200ms), modal content fades in with 100ms delay (200ms).
- **Modal Close:** Both fade out simultaneously (150ms).
- **Hover:** Glow expansion 200ms ease-out, background/color shift 150ms ease-out.
- **Active:** Glow collapse 100ms ease-in.

### Loading State
A centered amber ring (2px, 24px diameter) with one quadrant in full Projection Amber, rotating smoothly (`linear`, 800ms). Below: "Warming up…" in JetBrains Mono Label, `screen-muted`, fading in/out in a 2s cycle. The projector starting sequence.
