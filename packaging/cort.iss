; cort.iss — Inno Setup 6: el instalador de Windows de CORT.
;
; Por qué está aquí y por qué NO está compilado: esta máquina es Linux con dos
; núcleos y 1,8 GiB (medido en docs/PLATFORM.md); Inno Setup no corre aquí. El
; .iss se escribe y se revisa en el repo, **se compila en un PC Windows** con
; Inno Setup 6, y el `cort-setup.exe` resultante se adjunta a la Release ya
; abierta. Nada de esto se afirma funcionando sin haberlo pasado por ISCC.
;
; Compilar (en Windows, desde la raíz del árbol exportado de la etiqueta):
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\cort.iss
; Salida: packaging\Output\cort-setup-<versión>.exe
;
; El instalador NO hace de portero con el LLM ni con los datos de la usuaria:
; sólo coloca el árbol y crea atajos. Los recuerdos (`data/`), el `.env` y las
; preferencias viven en la carpeta de la usuaria y esta receta no los toca:
; actualizar CORT es reponer el árbol, nunca borrar la memoria.

#define MyAppName      "CORT"
#define MyAppVersion  "0.11.0"
#define MyAppPublisher "Sandra"
#define MyAppURL      "https://github.com/Sandra2244/CORT"
; Raíz del árbol exportado (git archive / zip de la etiqueta), un nivel arriba
; de packaging/.
#define RootDir       ".."

[Setup]
AppId={{8F4C9E31-52D7-4C0A-9C5B-C07C1C0ADE00}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\CORT
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename=cort-setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
; CORT no necesita privilegios: se instala por usuaria, sin tocar el sistema.
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\cort.bat

[Languages]
Name: "español"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio (doble clic para encender CORT)"

[Files]
; El árbol del proyecto, menos lo que nunca debe viajar (regla 7: sin claves,
; sin modelos, sin basura de build). Los patrones /exclude son de ISPP: se
; filtran en el [Files] de abajo con cada Exists/HasAttrs.
Source: "{#RootDir}\services\**";     DestDir: "{app}\services";     Excludes: "__pycache__\*.*,*.pyc,.env,.env.*"
Source: "{#RootDir}\apps\web\dist\**"; DestDir: "{app}\apps\web\dist"
Source: "{#RootDir}\scripts\**";       DestDir: "{app}\scripts";     Excludes: "__pycache__\*.*"
Source: "{#RootDir}\docs\**";          DestDir: "{app}\docs"
Source: "{#RootDir}\cort.bat";             DestDir: "{app}"
Source: "{#RootDir}\CORT.desktop";         DestDir: "{app}"
Source: "{#RootDir}\Makefile";             DestDir: "{app}"
Source: "{#RootDir}\README.md";            DestDir: "{app}"
Source: "{#RootDir}\AGENTS.md";            DestDir: "{app}"
Source: "{#RootDir}\INSTALAR-WINDOWS.txt"; DestDir: "{app}"
Source: "{#RootDir}\LICENSE";              DestDir: "{app}"
Source: "{#RootDir}\.env.example";         DestDir: "{app}"

[Icons]
; El atajo es exactamente el doble clic que ya existe: cort.bat, que llama al
; mismo scripts/cort.py que `make launch` en Linux (función documentada en
; docs/ARCHITECTURE.md). No se inventa un lanzador nuevo para el instalador.
Name: "{group}\Encender CORT";       Filename: "{app}\cort.bat"; WorkingDir: "{app}"
Name: "{group}\Instalación (leeme)"; Filename: "{app}\INSTALAR-WINDOWS.txt"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\CORT"; Filename: "{app}\cort.bat"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
; Dos decisiones honestas, y ninguna en silencio:
; 1) Python y Node NO se empaquetan: INSTALAR-WINDOWS.txt pide los oficiales
;    (python.org, nodejs.org) y este instalador no suplanta a sus instaladores.
; 2) La primera vez hay que crear el entorno y compilar la cara una vez —lo
;    mismo que el paso 3 del txt—. Se ofrece como tarea marcada por defecto;
;    si falla, el instalador no miente: la ventana del cmd queda a la vista.
Filename: "{cmd}"; Parameters: "/K cd /d ""{app}"""; Description: "Abrir cmd en la carpeta de CORT (paso 3 de INSTALAR-WINDOWS.txt: venv + dependencias + npm run build)"; Flags: postinstall skipifsilent

[Code]
; Antes de desinstalar, avisar de lo único que no se puede deshacer en silencio:
; los recuerdos y el .env de la usuaria. No se borra nada por detrás —Inno sólo
; quita lo que él puso—, pero lo dicho a la cara es más profesional que un
; confirm genérico.
function InitializeUninstall(): Boolean;
begin
  Result := MsgBox(
    'Se va a quitar el programa CORT. Tus recuerdos, tu .env y tus modelos NO están en esta lista: ' + #13#10 +
    'viven en la carpeta del proyecto y no se borran al desinstalar.' + #13#10 + #13#10 +
    '¿Continuar?', mbConfirmation, MB_OKCANCEL) = IDOK;
end;
