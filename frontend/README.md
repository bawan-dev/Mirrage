# Mirrage Frontend

React + TypeScript + Tailwind CSS mirror interface, built with Vite.

## Commands

```powershell
npm install
npm run dev
npm run build
npm run type-check
npm run preview
```

## Structure

- `src/main.tsx` - app entry point
- `src/App.tsx` - mirror UI, focus views, and backend status wiring
- `src/api.ts` - typed backend API client
- `src/types.ts` - response shapes matching the backend schemas
- `src/demoData.ts` - explicit fake data used only by demo mode
- `src/styles.css` - Tailwind entry plus Mirrage design tokens

The backend URL is read from `VITE_API_BASE_URL` and defaults to
`http://127.0.0.1:8000`.

The normal development interface includes an owner-only Identity view. A
trusted-device token entered there is kept in module memory for the current page
session; it is not written to `localStorage` or bundled into a `VITE_`
variable. Mirror Mode shows only the current display name and does not expose
identity administration.

For portfolio screenshots:

```powershell
$env:VITE_MIRROR_MODE="true"
$env:VITE_MIRRAGE_DEMO_MODE="true"
npm run dev
```
