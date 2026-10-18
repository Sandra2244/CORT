/* ===== CORT Desktop — ventana holográfica =====
   Dos modos:
   · CABINA (por defecto): ventana sin marco, fondo oscuro, siempre al
     frente. Funciona en CUALQUIER equipo, incluida Linux sin GPU.
   · VIDRIO (CORT_GLASS=1): transparente sobre el escritorio. Requiere
     compositor + aceleración (Windows, Linux con GPU). En equipos con
     GL por software la ventana transparente queda invisible.
   Atajos:  Esc = salir · Ctrl+Alt+T = alternar "siempre al frente"
            Ctrl+Alt+C = atravesar el clic (modo fantasma)
   Interfaz: CORT_UI=http://otro:puerto para cambiar el origen. */
const { app, BrowserWindow, globalShortcut, screen } = require('electron');

const glass = process.env.CORT_GLASS === '1';

if (glass) app.commandLine.appendSwitch('enable-transparent-visuals');
if (process.env.CORT_GPU !== '1') app.disableHardwareAcceleration(); // 2 GB RAM

let win, alwaysOnTop = true, ghost = false;

function createWindow() {
  const { width, height } = screen.getPrimaryDisplay().bounds;
  const opts = glass
    ? { width, height, x: 0, y: 0, transparent: true, backgroundColor: '#00000000' }
    : { width: Math.round(width * 0.86), height: Math.round(height * 0.86),
        x: Math.round(width * 0.07), y: Math.round(height * 0.07),
        transparent: false, backgroundColor: '#02040a' };
  win = new BrowserWindow({
    ...opts,
    frame: false,
    hasShadow: false,
    alwaysOnTop: true,
    fullscreenable: true,
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });
  win.setMenuBarVisibility(false);
  win.setAlwaysOnTop(true, 'screen-saver');
  const url = process.env.CORT_UI || 'http://127.0.0.1:8080';
  win.loadURL(url + (glass ? '/?glass=1' : '/'));
  win.on('closed', () => { win = null; app.quit(); });
}

app.whenReady().then(() => {
  createWindow();
  globalShortcut.register('Escape', () => app.quit());
  globalShortcut.register('CommandOrControl+Alt+T', () => {
    alwaysOnTop = !alwaysOnTop;
    win && win.setAlwaysOnTop(alwaysOnTop, 'screen-saver');
  });
  globalShortcut.register('CommandOrControl+Alt+C', () => {
    ghost = !ghost;
    win && win.setIgnoreMouseEvents(ghost, { forward: true });
  });
});

app.on('window-all-closed', () => app.quit());
