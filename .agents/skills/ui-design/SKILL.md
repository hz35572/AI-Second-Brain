---
name: ui-design
description: UI design guidance for building polished, usable product interfaces in this repository, especially the AI Second Brain frontend. Use when designing or reviewing app screens, layouts, component states, interaction patterns, visual hierarchy, responsive behavior, empty/loading/error states, or when translating product requirements into frontend UI.
---

# UI Design

Use this skill when shaping product UI for this repo, especially the chat, file management, upload, preview, and citation experiences.

## Design Priorities

- Keep the experience task-first, calm, and scan-friendly.
- Favor dense but organized layouts over decorative composition.
- Make the primary workflow visible immediately; avoid marketing-style framing.
- Preserve the citation-first contract: every answer point should be traceable, and citation UI must support click-to-open and locate/highlight behavior.
- Treat responsive behavior, loading states, and empty states as first-class work.

## Before Designing

1. Read the relevant product, frontend, and API docs.
2. Identify the exact workflow, state model, and failure modes.
3. Confirm the screen’s place in the broader three-column app layout.
4. Check whether the change affects citation behavior, scope selection, upload progress, or preview positioning.

## Layout Rules

- Use clear structural hierarchy: navigation, work area, and contextual preview or details.
- Keep sections full-width bands or disciplined panels; do not stack unnecessary cards inside cards.
- Use stable sizing for toolbars, panes, lists, and message streams so content changes do not shift the layout.
- Ensure text stays within its container at common desktop and mobile widths.
- Prefer compact controls, visible states, and direct manipulation over explanatory copy.

## Component Guidance

- Use icons for utility actions when a strong standard icon exists.
- Use tabs, segmented controls, toggles, menus, sliders, and text inputs for control states that users expect.
- Keep cards and surfaces restrained; avoid oversized radius unless the existing design system already does that.
- Design loading, empty, partial, and error states alongside the default state.
- For citation interactions, make the click target obvious and keep the source preview behavior discoverable without adding extra prose.

## Review Checklist

1. Does the screen fit the repository’s chat-first, work-focused product direction?
2. Is the main task easy to locate and complete?
3. Do all critical states have a visual answer?
4. Does the layout remain stable when content grows, streams, or wraps?
5. Does the design preserve citation traceability and preview behavior?

