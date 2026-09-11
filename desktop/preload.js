const { contextBridge, ipcRenderer } = require("electron");

// Secure context bridge for Desktop OS interactions
contextBridge.exposeInMainWorld("desktopAPI", {
  platform: process.platform,
  version: "1.0.0",
  sendNotification: (title, body) => {
    ipcRenderer.send("app:notify", { title, body });
  },
  openExternal: (url) => {
    ipcRenderer.send("app:open-external", url);
  },
  onUpdateAvailable: (callback) => {
    ipcRenderer.on("update:available", (_event, value) => callback(value));
  },
});
