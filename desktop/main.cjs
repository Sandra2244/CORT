/* ===== CORT Desktop — ventana holográfica =====
   Dos modos:
   · CABINA (por defecto): ventana sin marco, fondo oscuro, siempre al
     frente. Funciona en CUALQUIER equipo, incluida Linux sin GPU.
   · VIDRIO (CORT_GLASS=1): transparente sobre el escritorio. Requiere
     compositor + aceleración (Windows, Linux con GPU). En equipos con
     GL por software la ventana transparente queda invisible.
   Atajos:  Esc = salir · Ctrl+Alt+T = alternar "siempre al frente"
            Ctrl+Alt+C = atravesar el clic (modo fantasma)
   Interfaz: CORT_UI=http://otro:puerto para cambiar el origen.
   Cerebro: si no hay backend en CORT_PORT (8000), Electron levanta uno propio
   con el Python del sistema; si tampoco hay Python, el holograma sigue
   funcionando en modo local (partículas, reloj, notas del navegador). */
const { app, BrowserWindow, globalShortcut, screen } = require('electron');
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const glass = process.env.CORT_GLASS === '1';
const PORT = +(process.env.CORT_PORT || 8000);

if (glass) app.commandLine.appendSwitch('enable-transparent-visuals');
if (process.env.CORT_GPU !== '1') app.disableHardwareAcceleration(); // 2 GB RAM

/* UI embebida: al estar empaquetado, servimos resources/ui con un mini-servidor
   http local (los módulos ES no cargan con file://). En desarrollo se sigue
   usando http://127.0.0.1:8000, que ya reparte UI + API desde el backend. */
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.json': 'application/json',
  '.woff': 'font/woff', '.woff2': 'font/woff2', '.ico': 'image/x-icon' };
function serveEmbeddedUi() {
  const root = path.join(process.resourcesPath, 'ui');
  return new Promise(resolve => {
    const srv = http.createServer((req, res) => {
      let f = decodeURIComponent(req.url.split('?')[0]);
      if (f === '/') f = '/index.html';
      const file = path.join(root, f);
      if (!file.startsWith(root) || !fs.existsSync(file)) { res.writeHead(404); return res.end(''); }
      res.writeHead(200, { 'content-type': MIME[path.extname(file)] || 'application/octet-stream' });
      fs.createReadStream(file).pipe(res);
    });
    srv.listen(0, '127.0.0.1', () => resolve(`http://127.0.0.1:${srv.address().port}`));
  });
}

/* ---------------------------- backend embebido ---------------------------- */
function probeBackend() {
  return new Promise(resolve => {
    const req = http.get({ host: '127.0.0.1', port: PORT, path: '/api/port', timeout: 1200 },
      res => { res.resume(); resolve(res.statusCode === 200); });
    req.on('error', () => resolve(false));
    req.on('timeout', () => { req.destroy(); resolve(false); });
  });
}

function backendDir() {
  const cands = app.isPackaged
    ? [path.join(process.resourcesPath, 'backend')]
    : [path.join(__dirname, '..', 'backend')];
  return cands.find(c => fs.existsSync(path.join(c, 'app', 'main.py')));
}

function pythons() {
  const env = process.env.CORT_PYTHON;
  const list = env ? [env] : [];
  list.push('python3', 'python', 'py');
  return [...new Set(list)];
}

async function ensureBackend() {
  if (await probeBackend()) return true;            // ya lo arrancaste con scripts/run
  const dir = backendDir();
  if (!dir) return false;
  const uvicorn = path.join(path.dirname(process.execPath), 'uvicorn');
  const bases = fs.existsSync(uvicorn)
    ? [[uvicorn, []]]
    : pythons().map(p => [p, ['-m', 'uvicorn']]);
  for (const [bin, pre] of bases) {
    try {
      const child = spawn(bin,
        [...pre, '--app-dir', path.join(dir), 'app.main:app', '--port', String(PORT)],
        { env: { ...process.env, CORT_SERVE_UI: '1' }, stdio: 'ignore', detached: false });
      child.on('error', () => { child.__fail = true; });
      for (let i = 0; i < 25; i++) {                 // hasta ~7 s: venv + imports
        await new Promise(r => setTimeout(r, 300));
        if (child.__fail) break;
        if (await probeBackend()) { backendProc = child; console.log('CORT backend listo en :', PORT); return true; }
      }
      try { child.kill(); } catch (e) { /* ya murió */ }
    } catch (e) { /* siguiente candidato */ }
  }
  console.log('sin backend: el holograma corre en modo local');
  return false;
}

let win, backendProc = null, alwaysOnTop = true, ghost = false;

async function createWindow() {
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
  const hasBackend = await ensureBackend();
  const url = hasBackend
    ? `http://127.0.0.1:${PORT}`                       // UI + API en el mismo puerto
    : (process.env.CORT_UI || (app.isPackaged ? await serveEmbeddedUi()
                                             : 'http://127.0.0.1:8080'));
  win.loadURL(url + (glass ? '/?glass=1' : '/'));
  win.on('closed', () => { win = null; app.quit(); });
}

function killBackend() {
  try { backendProc && backendProc.kill(); } catch (e) { /* ya se cerró */ }
  backendProc = null;
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

app.on('window-all-closed', () => { killBackend(); app.quit(); });
app.on('before-quit', killBackend);
