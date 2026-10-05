---
name: repo-readme
description: Create or standardize a repository README.md with a visual-first, concise and consistent GitHub presentation. Use when creating, rewriting, refreshing or improving a repository README. Inspect the repository first and derive all technical claims from evidence.
---

# Repository README

Create or update the root `README.md` as a polished GitHub landing page: visual, easy to scan, useful to developers and concise. Keep every factual claim evidence-based.

## Inspect before writing

Inspect the existing README, manifests and lockfiles, source tree, test and CI configuration, deployment files, environment examples, API specs, docs, assets, license and Git metadata when available. Preserve useful information unless evidence shows it is obsolete, duplicated or incorrect.

Never invent features, versions, deployments, CI or release status, commands, integrations, coverage, architecture or URLs. Verify commands against project configuration, badges against authoritative sources, technology icons against actual dependencies or configuration, and local image links against files in the repository. Do not claim tests pass without current evidence.

## Visual identity

Start with a strong, centered visual hero. Keep project identity assets distinct:

```text
docs/assets/
├── logo.svg
└── readme-hero.svg
```

`logo.svg` is the reusable project mark: recognizable at small sizes and suitable outside the README. Make it an identity symbol, not a technical diagram. `readme-hero.svg` is a separate wide README composition. If either asset already exists, inspect and reuse it when suitable; create only assets needed for the README and use the convention above.

The hero should have a strong composition, generous negative space, one dominant idea and a small, coherent palette. Prefer abstract, geometric or editorial symbols that remain recognizable at small sizes. Use deliberate typography; monospace is not the default. Avoid boxes with arrows, pipeline stages, terminals, database cylinders, robots, code brackets and generic AI branding. Keep architecture and implementation details out of the hero. Never use fake screenshots, unrelated stock art or random hotlinked images.

## README order

Use this order, omitting any section without repository evidence:

1. Hero
2. Project name
3. One-line description
4. Compact, verifiable badges
5. Technology icons
6. Optional visual preview
7. Quick Start
8. Architecture
9. Development
10. Testing
11. API / Interfaces
12. Deployment
13. Project Structure
14. Contributing
15. License

Keep introductory text to the one-line description. Place Quick Start near the top, directly after the visual header and optional preview. Use images, concise tables, GitHub-compatible Mermaid diagrams and executable commands instead of long paragraphs. Use representative screenshots only when available and meaningful. Keep detailed explanations in `docs/` and link to them for progressive disclosure.

## Header details

Place badges directly below the description. Use a compact, consistent row of values that can be verified from the repository or an authoritative provider. Badges communicate project status; keep stack icons in a separate row. Show only a few primary technologies confirmed by evidence, not a dependency inventory. Omit unavailable or unverified badges and icons.

Use a single concise sentence for the description, normally under 160 characters. Avoid generic marketing copy. Do not add an Overview or a table of contents by default; add navigation only when the README's length requires it.

## Sections

- **Quick Start:** Prefer the shortest complete, executable path to run the project. Use the repository's documented tooling and commands; do not substitute tools or guess missing steps.
- **Architecture:** Summarize only evidenced components and relationships. Use a small Mermaid diagram or table when clearer than prose. Keep all technical diagrams here, never in the logo or hero.
- **Development and Testing:** Use compact command tables or code blocks. Include only commands supported by project files or documentation, and distinguish available checks from verified results.
- **API / Interfaces:** Link to the canonical OpenAPI spec, interface docs, CLI help or package documentation rather than duplicating them.
- **Deployment:** Include only configuration-backed or authoritatively documented deployment instructions. Never infer a production target or expose secrets.
- **Project Structure:** List only key paths, with brief descriptions; do not dump the repository tree.
- **Contributing and License:** Include only when repository guidance or a license file provides evidence, and link to the source file.

Prefer short sentences, compact tables and links. Remove repeated explanations, empty sections, generic boilerplate, filler, decorative complexity, excessive HTML and emoji. Detailed technical documentation belongs in `docs/` or the repository's established documentation location.

## Validate

Before finishing, verify factual claims, commands, badges, technology icons and referenced paths against repository evidence. Remove unsupported claims and empty sections, then review the README diff as a GitHub landing page. A developer should understand the project and reach Quick Start without reading a wall of text.
