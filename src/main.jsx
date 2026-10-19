import React, { lazy, Suspense } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/dm-sans";
import "@fontsource-variable/manrope";
const legacy =
  window.location.pathname === "/v1" ||
  window.location.pathname.startsWith("/v1/");
const App = legacy
  ? lazy(() => import("./App.jsx"))
  : lazy(() => import("./DelayLab.jsx"));
if (legacy) document.title = "Swiss Rail Network Explorer — V1 synthetic demo";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Suspense
      fallback={
        <p style={{ padding: "40px", fontFamily: "Arial, sans-serif" }}>
          Loading study…
        </p>
      }
    >
      <App />
    </Suspense>
  </React.StrictMode>,
);
