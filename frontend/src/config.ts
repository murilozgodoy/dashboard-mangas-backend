export const API_BASE =
  typeof window !== "undefined" && (window.location.port === "5173" || window.location.port === "3000")
    ? "http://localhost:8002"
    : "";
