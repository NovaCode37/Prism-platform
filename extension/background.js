const DEFAULT_URL = "https://getprism.su";

function baseUrl(url) {
  let u = (url || DEFAULT_URL).trim().replace(/\/+$/, "");
  if (!/^https?:\/\//i.test(u)) u = "https://" + u;
  return u;
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "prism-scan",
    title: chrome.i18n.getMessage("contextMenuTitle"),
    contexts: ["selection"],
  });
});

chrome.contextMenus.onClicked.addListener(async (info) => {
  if (info.menuItemId !== "prism-scan") return;
  const target = (info.selectionText || "").trim();
  if (!target) return;
  await chrome.storage.local.set({ pendingTarget: target });
  try {
    if (chrome.action.openPopup) {
      await chrome.action.openPopup();
      return;
    }
  } catch (e) {}
  chrome.tabs.create({ url: chrome.runtime.getURL(`scan.html?target=${encodeURIComponent(target)}`) });
});
