import { Suspense } from "react";
import { Workspace } from "./Workspace";
import "../../app.css";

// Project id comes from the query string (/app/project?id=…) so the app can be exported as static files.
export default function ProjectPage() {
  return (
    <Suspense fallback={null}>
      <Workspace />
    </Suspense>
  );
}
