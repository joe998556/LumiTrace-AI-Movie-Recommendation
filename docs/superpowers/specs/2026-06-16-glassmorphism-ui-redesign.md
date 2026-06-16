# Glassmorphism UI Redesign

Date: 2026-06-16

## Goal

Redesign LumiTrace UI from flat dark theme to Glassmorphism with starry sky background, blue-purple palette, and Apple-style animations.

## Design System

### Colors
- Ground: `#0a0a1a` (deep night blue)
- Glass bg: `rgba(255,255,255,0.05)`
- Glass border: `rgba(255,255,255,0.1)`
- Glass blur: `16px`
- Primary: `#a78bfa` (purple)
- Secondary: `#60a5fa` (blue)
- Gradient: `linear-gradient(135deg, #a78bfa, #60a5fa)`
- Text: `#f0f0ff` / `#a0a0c0` / `#606080`

### Typography
- Inter (Google Fonts), weights 400/500/600
- Headings: letter-spacing -0.02em

### Spacing
- 4 / 8 / 12 / 16 / 24 / 40 / 64px

### Radius
- Small: 8px, Medium: 12px, Large: 16px

## Starry Sky Background (Canvas)

- 150-200 random stars, size 0.5-2px
- Twinkle animation (opacity 0.3-1.0)
- Slow drift (micro-movement)
- Shooting stars every 5-8 seconds
- Parallax: background moves at 0.3x scroll speed

## Glassmorphism Cards

- `background: rgba(255,255,255,0.05)`
- `backdrop-filter: blur(16px)`
- `border: 1px solid rgba(255,255,255,0.1)`
- Hover: border brightens + translateY(-4px) + subtle glow

## Animations (Apple-style)

- Card entrance: IntersectionObserver, fade-in + translateY(20px), cubic-bezier(0.22, 1, 0.36, 1)
- Hover: 150ms ease-out
- Panel slide: 350ms cubic-bezier(0.22, 1, 0.36, 1)
- Scroll parallax: stars at 0.3x speed

## Files Modified

- `index.html` — main page
- `favorites.html` — favorites page
- `script.js` — card rendering, interactions
- `app.py` — no changes needed

## Implementation Approach

- Canvas for starry sky (shared JS module)
- CSS custom properties for design tokens
- IntersectionObserver for scroll animations
- No external dependencies beyond Inter font

## Testing

- Visual: verify glass effect visible on dark background
- Performance: Canvas should maintain 60fps
- Responsive: cards reflow on mobile
- Accessibility: sufficient contrast on glass surfaces
