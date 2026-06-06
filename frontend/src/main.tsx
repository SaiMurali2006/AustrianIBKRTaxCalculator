import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ThemeProvider } from "./theme/ThemeProvider";
import "./theme/tokens.css";
import "./components/components.css";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </StrictMode>,
);
