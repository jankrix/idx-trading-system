// Intercept every request to exodus.stockbit.com and capture the Bearer token.
// Stores it in chrome.storage.local so the popup can read it.

chrome.webRequest.onBeforeSendHeaders.addListener(
  (details) => {
    const authHeader = details.requestHeaders?.find(
      (h) => h.name.toLowerCase() === "authorization"
    );
    if (authHeader?.value?.startsWith("Bearer ")) {
      const token = authHeader.value.replace("Bearer ", "").trim();
      chrome.storage.local.set({
        token,
        captured_at: new Date().toISOString(),
        synced: false,
      });
    }
  },
  { urls: ["https://exodus.stockbit.com/*"] },
  ["requestHeaders"]
);
