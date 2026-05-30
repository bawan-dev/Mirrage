# Mirrage Frontend

React + TypeScript + Tailwind CSS dashboard for the mirror interface, built with Vite.

## Commands

```powershell
npm install      # install dependencies
npm run dev      # start the dev server on http://127.0.0.1:5173
npm run build    # type-check then build for production
npm run type-check  # type-check only
npm run preview  # preview the production build
```

## Structure

- `src/main.tsx` — app entry point
- `src/App.tsx` — dashboard layout and backend status wiring
- `src/api.ts` — typed backend API client
- `src/types.ts` — response shapes matching the backend schemas
- `src/styles.css` — Tailwind entry plus Mirrage design tokens

The backend URL is read from `VITE_API_BASE_URL` (see `.env.example`) and defaults
to `http://127.0.0.1:8000`.
