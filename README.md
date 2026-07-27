# PyBlocks Studio — local reconstruction

This repository is a local reconstruction of the intended PyBlocks Studio application.

## Why this is a reconstruction

The readable Lovable project commit `d5f2402b3b9c723fc182579a3d77a69c6d117365` contains the generic TanStack/Shadcn scaffold and a blank placeholder route. It does not contain the visual Python editor shown or described in the earlier request. Therefore, this repository preserves the inspected project metadata while implementing the missing application from the product specification.

## Immediately runnable standalone version

The `standalone/` directory has no npm dependencies.

```bash
cd pyblocks-studio-local
python3 -m http.server 8000
```

Then open:

```text
http://127.0.0.1:8000/standalone/
```

The standalone build includes:

- Procedurally generated SVG block geometry.
- Typed and inspectable connector metadata.
- Mouse and touch block movement.
- Canvas pan and zoom.
- A Python-oriented starter workspace.
- Live Python source, graph, connector, artifact, and runtime views.
- Deterministic package/module descriptor generation.
- Downloadable SVG and JSON package artifacts.
- LocalStorage persistence.
- Desktop three-panel layout.
- Mobile canvas-first layout with Blocks/Code tabs.
- A draggable block-library bottom sheet occupying roughly 28–82% of viewport height, initially 40%.
- Full-screen mobile secondary inspector views.

## React/TypeScript source

The root `src/` directory contains the modular React/TypeScript implementation. Its dependencies are declared in `package.json`.

```bash
npm install
npm run dev
```

Dependency installation could not be completed in the generation container because npm network operations timed out. The TypeScript source is retained, while the standalone build is the verified dependency-free execution path.

## Virtual generated package layout

Browser-generated artifacts use virtual paths of this form:

```text
blocks/<normalized-package-name>/
├── blocks.svg
└── block-specs.json
```

The files can be downloaded from the Artifacts view. A production local Python bridge can replace the browser descriptor adapter with real `inspect`, `importlib`, `typing`, and signature discovery.
