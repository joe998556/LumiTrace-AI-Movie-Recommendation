/* Public deployment configuration. API URLs are not secrets. */
(function () {
  "use strict";
  // A static host may set window.LUMITRACE_API_BASE before this script loads.
  // A one-container deployment needs no override and stays same-origin.
  const DEPLOYED_API_BASE = "";
  const configured = String(window.LUMITRACE_API_BASE || DEPLOYED_API_BASE).trim().replace(/\/$/, "");
  const sameOrigin = window.location.protocol === "file:"
    ? "http://localhost:8080/api"
    : `${window.location.origin}/api`;
  window.LumiTraceConfig = Object.freeze({ apiBase: configured || sameOrigin });
})();
