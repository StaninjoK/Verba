"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { chatApi, isChatActive, type ChatSummary } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { MockBadge, StatusBadge } from "./StatusBadge";

/** Imported WhatsApp chats. Hidden while there are none. */
export function ChatList({ refreshKey }: { refreshKey: number }) {
  const { t, locale } = useI18n();
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    chatApi.list().then((list) => !cancelled && setChats(list)).catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [refreshKey, tick]);

  const anyActive = chats.some((c) => isChatActive(c.status));
  useEffect(() => {
    if (!anyActive) return;
    const id = window.setInterval(() => setTick((n) => n + 1), 2500);
    return () => window.clearInterval(id);
  }, [anyActive]);

  if (!chats.length) return null;
  return (
    <section className="library" aria-labelledby="chat-list-title">
      <div className="library-head">
        <h2 id="chat-list-title">{t("chat.listTitle")}</h2>
      </div>
      <ul className="project-list" data-testid="chat-list">
        {chats.map((c) => (
          <li key={c.id} className="project-row" data-testid="chat-row">
            <Link href={`/app/chat?id=${c.id}`} className="project-link">
              <span className="file-icon chat-row-icon" aria-hidden="true">💬</span>
              <span className="project-main">
                <span className="project-title">{c.title}</span>
                <span className="project-meta hint">
                  {c.total_items > 0 && (
                    <span className="tabular">{t("chat.progress", { done: c.done_items, total: c.total_items })}</span>
                  )}
                  <span aria-hidden="true">·</span>
                  <span>{new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(c.created_at))}</span>
                </span>
              </span>
              <span className="project-badges">
                {c.is_mock && <MockBadge />}
                <StatusBadge status={c.status} />
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
