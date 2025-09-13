README.md
# Urban Vitals

A basic, static website built with the **React** framework using **Vite**.  
Language: **JavaScript**.

## Tech Stack
- React (JavaScript)
- Vite (dev server & build)
- Static site output in `dist/`

## Getting Started

```bash
# Install deps (inside the project)
npm install
```

# Start dev server
```bash
npm run dev
```

Open your browser to the URL Vite prints (usually http://localhost:5173/).

Build (Static)

## Build for Production

Build a production, static bundle:

```bash
npm run build
```

The output goes to `dist/` — you can host that folder on any static host (e.g., GitHub Pages, Netlify, Vercel, S3).

Optionally preview the production build locally:

```bash
npm run preview
```

Project Structure
.
├─ index.html
├─ src/
│  ├─ App.jsx
│  ├─ main.jsx
│  └─ index.css
├─ package.json
└─ vite.config.js

Notes

This is a plain JavaScript React app (no TypeScript).

There is no backend; it’s a static single-page app (SPA).

Customize styles in src/index.css and content in src/App.jsx.


---

## How to use this now
1. Replace your current `src/App.jsx` and `src/index.css` with the ones above.
2. Update `index.html` title/meta if you like.
3. In the project root, run:
   ```bash
   npm run dev


When you’re ready to deploy a static site:

npm run build
npm run preview  # optional, to test the built files