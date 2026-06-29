function readBoolean(value: string | undefined): boolean {
  return value?.toLowerCase() === 'true';
}

function readSeconds(
  value: string | undefined,
  fallbackSeconds: number,
): number {
  if (!value) {
    return fallbackSeconds;
  }

  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallbackSeconds;
  }

  return parsed;
}

export const mirrorModeConfig = {
  burnInShiftMs:
    readSeconds(import.meta.env.VITE_MIRROR_BURN_IN_SHIFT_SECONDS, 45) * 1000,
  dimTimeoutMs:
    readSeconds(import.meta.env.VITE_MIRROR_DIM_TIMEOUT_SECONDS, 60) * 1000,
  enabled: readBoolean(import.meta.env.VITE_MIRROR_MODE),
  sleepTimeoutMs:
    readSeconds(import.meta.env.VITE_MIRROR_SLEEP_TIMEOUT_SECONDS, 120) * 1000,
  startupMs: readSeconds(import.meta.env.VITE_MIRROR_STARTUP_SECONDS, 3) * 1000,
};

export const wakeWordConfig = {
  browserListenerEnabled: readBoolean(
    import.meta.env.VITE_EXPERIMENTAL_BROWSER_WAKE_WORD,
  ),
};
