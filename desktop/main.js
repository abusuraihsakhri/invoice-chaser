const { app, BrowserWindow, Menu, Tray, Notification, shell, ipcMain } = require("electron");
const path = require("path");
const fs = require("fs");

let mainWindow = null;
let tray = null;

const isDev = process.env.NODE_ENV === "development";

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 850,
    minWidth: 950,
    minHeight: 650,
    title: "Invoice Chaser",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  // Load the static Next.js export
  const outIndexPath = path.join(__dirname, "..", "frontend", "out", "index.html");
  if (!isDev && fs.existsSync(outIndexPath)) {
    mainWindow.loadFile(outIndexPath);
  } else {
    mainWindow.loadURL("http://localhost:3000").catch(() => {
      if (fs.existsSync(outIndexPath)) {
        mainWindow.loadFile(outIndexPath);
      }
    });
  }

  // Open external links in user's default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  createApplicationMenu();
  createSystemTray();
}

function createApplicationMenu() {
  const isMac = process.platform === "darwin";
  const template = [
    ...(isMac
      ? [
          {
            label: app.name,
            submenu: [
              { role: "about" },
              { type: "separator" },
              { role: "services" },
              { type: "separator" },
              { role: "hide" },
              { role: "hideOthers" },
              { role: "unhide" },
              { type: "separator" },
              { role: "quit" },
            ],
          },
        ]
      : []),
    {
      label: "File",
      submenu: [
        {
          label: "Dashboard",
          accelerator: "CmdOrCtrl+1",
          click: () => loadRoute("/"),
        },
        {
          label: "Invoices",
          accelerator: "CmdOrCtrl+2",
          click: () => loadRoute("/invoices"),
        },
        {
          label: "Clients",
          accelerator: "CmdOrCtrl+3",
          click: () => loadRoute("/clients"),
        },
        {
          label: "Reminders",
          accelerator: "CmdOrCtrl+4",
          click: () => loadRoute("/reminders"),
        },
        {
          label: "Settings",
          accelerator: "CmdOrCtrl+,",
          click: () => loadRoute("/settings"),
        },
        { type: "separator" },
        isMac ? { role: "close" } : { role: "quit" },
      ],
    },
    {
      label: "Edit",
      submenu: [
        { role: "undo" },
        { role: "redo" },
        { type: "separator" },
        { role: "cut" },
        { role: "copy" },
        { role: "paste" },
        { role: "selectAll" },
      ],
    },
    {
      label: "View",
      submenu: [
        { role: "reload" },
        { role: "forceReload" },
        { role: "toggleDevTools" },
        { type: "separator" },
        { role: "resetZoom" },
        { role: "zoomIn" },
        { role: "zoomOut" },
        { type: "separator" },
        { role: "togglefullscreen" },
      ],
    },
    {
      label: "Help",
      submenu: [
        {
          label: "Documentation & GitHub",
          click: async () => {
            await shell.openExternal("https://github.com");
          },
        },
        {
          label: "About Invoice Chaser",
          click: () => {
            const { dialog } = require("electron");
            dialog.showMessageBox(mainWindow, {
              type: "info",
              title: "Invoice Chaser",
              message: "Invoice Chaser v1.0.0",
              detail: "Cross-platform accounts receivable automation engine with AI-powered tone escalation.",
            });
          },
        },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

function loadRoute(subpath) {
  if (!mainWindow) return;
  const outPath = path.join(__dirname, "..", "frontend", "out", subpath === "/" ? "index.html" : `${subpath.replace(/^\//, "")}/index.html`);
  if (fs.existsSync(outPath)) {
    mainWindow.loadFile(outPath);
  } else {
    mainWindow.loadURL(`http://localhost:3000${subpath}`);
  }
}

function createSystemTray() {
  // Gracefully skip tray icon if assets not found
  const iconPath = path.join(__dirname, "assets", process.platform === "win32" ? "icon.ico" : "icon.png");
  if (!fs.existsSync(iconPath)) return;

  try {
    tray = new Tray(iconPath);
    const contextMenu = Menu.buildFromTemplate([
      { label: "Show Invoice Chaser", click: () => mainWindow && mainWindow.show() },
      { label: "Dashboard", click: () => loadRoute("/") },
      { label: "Invoices", click: () => loadRoute("/invoices") },
      { type: "separator" },
      { label: "Quit", click: () => app.quit() },
    ]);
    tray.setToolTip("Invoice Chaser");
    tray.setContextMenu(contextMenu);
  } catch (err) {
    console.warn("Could not create system tray:", err);
  }
}

// IPC Handlers
ipcMain.on("app:notify", (_event, { title, body }) => {
  if (Notification.isSupported()) {
    new Notification({ title: title || "Invoice Chaser", body }).show();
  }
});

ipcMain.on("app:open-external", (_event, url) => {
  if (url && (url.startsWith("http://") || url.startsWith("https://"))) {
    shell.openExternal(url);
  }
});

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
