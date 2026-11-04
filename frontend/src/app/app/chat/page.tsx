import { Suspense } from "react";
import { ChatWorkspace } from "./ChatWorkspace";
import "../../app.css";

// Chat id comes from the query string (/app/chat?id=…) so the app can be exported as static files.
export default function ChatPage() {
  return (
    <Suspense fallback={null}>
      <ChatWorkspace />
    </Suspense>
  );
}
