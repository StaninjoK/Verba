"use client";

import type { ReactNode } from "react";
import { I18nProvider } from "@/lib/i18n";
import { ToastProvider } from "./Toast";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <I18nProvider>
      <ToastProvider>{children}</ToastProvider>
    </I18nProvider>
  );
}
