/**
 * Pruebas de la interfaz web, sin dependencias nuevas.
 *
 * Node 20 no sabe leer TypeScript, y el `tsc` que ya está en `apps/web` tampoco:
 * sólo typechea. Así que este archivo hace de puente con lo que hay:
 *
 *   1. lee `src/cort/*.ts` y lo transpila con el paquete `typescript` que **ya**
 *      es `devDependency` del proyecto,
 *   2. lo deja en un directorio temporal junto con las pruebas (`.test.mjs`),
 *   3. corre `node --test` sobre ese directorio.
 *
 * Por qué no `vitest` o `jest`: esta máquina tiene 1,8 GiB de RAM y un navegador
 * simulado (jsdom) cuesta justo la memoria que el reactor necesita para sí. Lo
 * que se prueba aquí son funciones puras —el estado de los paneles y la tabla de
 * teclas—, y a las funciones puras no les hace falta un DOM.
 *
 * El script se puede lanzar desde la raíz o desde `apps/web` (así lo llama el
 * `Makefile`): todas las rutas salen de su propia ubicación, no del `cwd`.
 */

import { copyFileSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { spawnSync } from 'node:child_process'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const WEB = join(dirname(fileURLToPath(import.meta.url)), '..', 'apps', 'web')

// `typescript` está en `apps/web/node_modules`, y este script vive en `scripts/`:
// sin una ruta explícita, `import('typescript')` no lo encontraría.
const require = createRequire(join(WEB, 'package.json'))
let ts
try {
  ts = require('typescript')
} catch {
  console.error('FALTA apps/web/node_modules — ejecuta: make web-deps')
  process.exit(1)
}

/** Módulos puros de la interfaz que se prueban sin navegador. Amplía la lista así. */
const MODULOS = ['src/cort/paneles.ts']
const PRUEBAS = ['tests/paneles.test.mjs']

const TMP = join(dirname(fileURLToPath(import.meta.url)), '..', '.pruebas-web-tmp')
rmSync(TMP, { recursive: true, force: true })
mkdirSync(TMP, { recursive: true })

for (const archivo of MODULOS) {
  const codigo = ts.transpileModule(readFileSync(join(WEB, archivo), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText
  const destino = join(TMP, archivo.split('/').pop().replace(/\.ts$/, '.mjs'))
  writeFileSync(destino, codigo)
  console.log(`transpilado ${archivo} → ${destino.replace(/^\.\//, '')}`)
}

for (const archivo of PRUEBAS) {
  copyFileSync(join(WEB, archivo), join(TMP, archivo.split('/').pop()))
}

const salida = spawnSync(process.execPath, ['--test', TMP], { stdio: 'inherit' })
rmSync(TMP, { recursive: true, force: true })
process.exit(salida.status ?? 1)
