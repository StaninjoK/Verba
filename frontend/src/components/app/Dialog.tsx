"use client";

import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from "react";
import { useI18n } from "@/lib/i18n";

function useDialogKeys(onClose: () => void, ref: React.RefObject<HTMLDivElement | null>) {
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab" && ref.current) {
        // keep focus inside the dialog
        const focusable = ref.current.querySelectorAll<HTMLElement>("button, input, select, textarea, a[href]");
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previous?.focus?.();
    };
  }, [onClose, ref]);
}

function DialogShell({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();
  useDialogKeys(onClose, ref);
  return (
    <div className="dialog-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby={titleId} ref={ref}>
        <h2 id={titleId}>{title}</h2>
        {children}
      </div>
    </div>
  );
}

export function ConfirmDialog(props: {
  title: string;
  body: string;
  confirmLabel: string;
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const cancelRef = useRef<HTMLButtonElement>(null);
  useEffect(() => cancelRef.current?.focus(), []);
  return (
    <DialogShell title={props.title} onClose={props.onClose}>
      <p className="muted">{props.body}</p>
      <div className="dialog-actions">
        <button ref={cancelRef} type="button" className="btn" onClick={props.onClose}>{t("lib.cancel")}</button>
        <button type="button" className={`btn ${props.danger ? "btn-danger-solid" : "btn-primary"}`} onClick={props.onConfirm}
          disabled={props.busy}>
          {props.busy && <span className="spinner" aria-hidden="true" />}
          {props.confirmLabel}
        </button>
      </div>
    </DialogShell>
  );
}

export function RenameDialog(props: { initial: string; onSave: (title: string) => Promise<void> | void; onClose: () => void }) {
  const { t } = useI18n();
  const [value, setValue] = useState(props.initial);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => inputRef.current?.select(), []);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!value.trim()) return;
    setBusy(true);
    try {
      await props.onSave(value.trim());
    } finally {
      setBusy(false);
    }
  };
  return (
    <DialogShell title={t("ws.rename")} onClose={props.onClose}>
      <form onSubmit={submit}>
        <label className="sr-only" htmlFor="rename-input">{t("ws.rename")}</label>
        <input id="rename-input" ref={inputRef} className="input" value={value} maxLength={200}
          onChange={(e) => setValue(e.target.value)} />
        <div className="dialog-actions">
          <button type="button" className="btn" onClick={props.onClose}>{t("lib.cancel")}</button>
          <button type="submit" className="btn btn-primary" disabled={busy || !value.trim()}>{t("lib.save")}</button>
        </div>
      </form>
    </DialogShell>
  );
}
