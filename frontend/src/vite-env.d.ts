/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_MIRRAGE_DEMO_MODE?: string;
  readonly VITE_MIRROR_BURN_IN_SHIFT_SECONDS?: string;
  readonly VITE_MIRROR_DIM_TIMEOUT_SECONDS?: string;
  readonly VITE_MIRROR_MODE?: string;
  readonly VITE_MIRROR_SLEEP_TIMEOUT_SECONDS?: string;
  readonly VITE_MIRROR_STARTUP_SECONDS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
