"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type SystemInfo } from "./api";

export type SystemState = { kind: "loading" } | { kind: "offline" } | { kind: "ready"; info: SystemInfo };

export function useSystem(pollMs = 15000) {
  const [state, setState] = useState<SystemState>({ kind: "loading" });

  const refresh = useCallback(async () => {
    try {
      const info = await api.system();
      setState({ kind: "ready", info });
    } catch {
      setState({ kind: "offline" });
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial fetch of external state
    void refresh();
    const id = window.setInterval(refresh, pollMs);
    return () => window.clearInterval(id);
  }, [refresh, pollMs]);

  return { state, refresh };
}

export function languageName(code: string, locale: string): string {
  try {
    const name = new Intl.DisplayNames([locale], { type: "language" }).of(code);
    return name ? name.charAt(0).toLocaleUpperCase(locale) + name.slice(1) : code;
  } catch {
    return code;
  }
}
