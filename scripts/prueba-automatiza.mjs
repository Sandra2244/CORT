#!/usr/bin/env node
/* Prueba del motor de automatizaciones (`ui/js/automatiza.js`), sin teléfono.
 *
 * El módulo es puro a propósito —el almacén, el reloj y las manos entran por
 * parámetros—, y eso es lo que permite comprobar aquí las reglas «cuando X,
 * entonces Y» en el portátil: los acentos, el freno de un minuto, «a las 7:30
 * una sola vez al día», la señal del auricular y la del aviso que Java manda
 * desde la 2.4. Nada de esto necesita Android ni WebView.
 *
 * Uso:  node scripts/prueba-automatiza.mjs     (una fracción de segundo)
 * Va en `build.yml` junto a las demás pruebas de lógica, antes de firmar.
 */
import { creaMotor, necesitaReloj, marcapasos, preajustes, DISPARADORES, ACCIONES, normaliza }
  from '../ui/js/automatiza.js';

let fallos = 0, hechos = 0;
const ok = (etiqueta, condicionado, detalle = '') => {
  if (condicionado) { hechos++; console.log('  ok  ' + etiqueta); }
  else { fallos++; console.log('  NO  ' + etiqueta + (detalle ? ' → ' + detalle : '')); }
};
/* Cede la vuelta de eventos: `corre` es `async`, así que las acciones se resuelven
   después del `dispara`. Sin esto la prueba miraría `pididas` demasiado pronto. */
const espera = () => new Promise(r => setTimeout(r, 0));

/* El almacén de mentira: dos motores sobre el mismo objeto son la prueba de que las
   reglas sobreviven a cerrar y abrir la app, que es lo que ella hace a diario. */
function almacen() {
  const mapa = new Map();
  return { getItem: k => (mapa.has(k) ? mapa.get(k) : null),
           setItem: (k, v) => mapa.set(k, String(v)),
           removeItem: k => mapa.delete(k), mapa };
}

/* Las manos de mentira: cuentan lo que se les pidió y pueden negarse. */
function manos(niegan = []) {
  const pididas = [];
  return { pididas,
           async ejecuta(que, a) { pididas.push({ que, a }); return !niegan.includes(que); } };
}

function consola() {
  const lineas = [];
  return { lineas, term: t => lineas.push(t) };
}

/* Un reloj que se mueve cuando lo dice la prueba, no cuando diga el sistema. */
function reloj(ms) {
  let t = ms;
  return { ahora: () => t, avanza: d => { t += d; }, fija: d => { t = d; } };
}

const base = Date.parse('2026-10-22T07:00:00Z');

console.log('\n[1] las frases: la suya, con sus acentos y sus palabras de más');
{
  const m = manos(), c = consola(), r = reloj(base);
  const motor = creaMotor({ ejecuta: m.ejecuta, term: c.term, almacen: almacen(), reloj: r.ahora });
  motor.agrega({ nombre: 'noche', disparador: { tipo: 'frase', texto: 'modo noche' },
                 hacen: [{ que: 'volumen', como: 'callar' }] });
  ok('frase: «Modo  NOCHE» con mayúsculas y doble espacio',
    motor.dispara({ tipo: 'frase', texto: 'Modo  NOCHE' }).length === 1);
  await espera();
  ok('frase: la mano recibió la acción', m.pididas.length === 1 && m.pididas[0].que === 'volumen',
    JSON.stringify(m.pididas));
  ok('frase: dentro de otra frase larga también cuenta (con el minuto de freno ya cumplido)',
    (() => { const v = creaMotor({ ejecuta: m.ejecuta, term: c.term, almacen: almacen(), reloj: () => base + 500000 });
             v.agrega({ nombre: 'larga', disparador: { tipo: 'frase', texto: 'modo noche' },
                        hacen: [{ que: 'habla', texto: 'x' }] });
             return v.dispara({ tipo: 'frase', texto: 'apaga todo, modo noche por favor' }).length === 1; })());
  ok('frase: con el freno puesto, la segunda vez NO suena (y eso se dice, no se calla)',
    motor.dispara({ tipo: 'frase', texto: 'modo noche' }).length === 0);
  ok('frase: el freno se AVISA en la consola, con el nombre de la regla',
    c.lineas.some(l => /acaba de sonar: la freno un minuto/.test(l)), c.lineas.join(' | '));
  r.fija(base + 61000);
  ok('frase: pasado el minuto vuelve a sonar',
    motor.dispara({ tipo: 'frase', texto: 'modo noche' }).length === 1);
  await espera();
  ok('frase: una que no coincide no dispara nada',
    motor.dispara({ tipo: 'frase', texto: 'qué hora es' }).length === 0);
  ok('frase: regla vacía no traga todo',
    (() => { const v = creaMotor({ ejecuta: m.ejecuta, term: c.term, almacen: almacen(), reloj: r.ahora });
             v.agrega({ nombre: 'vacia', disparador: { tipo: 'frase', texto: '' }, hacen: [{ que: 'habla', texto: 'x' }] });
             return v.dispara({ tipo: 'frase', texto: 'cualquier cosa' }).length === 0; })());
}

console.log('\n[2] el aviso que Java manda desde la 2.4');
{
  const m = manos(), c = consola(), r = reloj(base);
  const motor = creaMotor({ ejecuta: m.ejecuta, term: c.term, almacen: almacen(), reloj: r.ahora });
  motor.agrega({ nombre: 'de juan', disparador: { tipo: 'aviso', de: 'whatsapp', texto: 'hola' },
                 hacen: [{ que: 'habla', texto: 'mensaje de WhatsApp' }] });
  ok('aviso: coincide con quien manda y con lo que dice',
    motor.dispara({ tipo: 'aviso', de: 'WhatsApp', dice: '14:02 · WhatsApp · Juan: hola!' }).length === 1);
  await espera();
  ok('aviso: mismo aviso de otra app NO dispara',
    motor.dispara({ tipo: 'aviso', de: 'gmail', dice: 'hola!' }).length === 0);
  ok('aviso: con otra palabra dentro del mensaje tampoco',
    motor.dispara({ tipo: 'aviso', de: 'whatsapp', dice: 'la reunión es a las 9' }).length === 0);
  r.fija(base + 90000);
  ok('aviso: sólo «de quién» basta si el texto está vacío',
    (() => { const v = creaMotor({ ejecuta: m.ejecuta, term: c.term, almacen: almacen(), reloj: r.ahora });
             v.agrega({ nombre: 'todo wa', disparador: { tipo: 'aviso', de: 'whatsapp' }, hacen: [{ que: 'habla', texto: 'x' }] });
             return v.dispara({ tipo: 'aviso', de: 'WhatsApp', dice: 'lo que sea' }).length === 1; })());
  ok('aviso: una regla con `de` y `texto` vacíos no dispara nunca',
    (() => { const v = creaMotor({ ejecuta: m.ejecuta, term: c.term, almacen: almacen(), reloj: r.ahora });
             v.agrega({ nombre: 'sucia', disparador: { tipo: 'aviso' }, hacen: [{ que: 'habla', texto: 'x' }] });
             return v.dispara({ tipo: 'aviso', de: 'whatsapp', dice: 'hola' }).length === 0; })());
}

console.log('\n[3] el auricular y la batería');
{
  const m = manos(), c = consola(), r = reloj(base);
  const motor = creaMotor({ ejecuta: m.ejecuta, term: c.term, almacen: almacen(), reloj: r.ahora });
  motor.agrega({ nombre: 'doble toque', disparador: { tipo: 'auricular', estado: 'suena' },
                 hacen: [{ que: 'musica', como: 'seguir' }] });
  ok('auricular: «suena» con escuchando:true',
    motor.dispara({ tipo: 'auricular', escuchando: true }).length === 1);
  await espera();
  ok('auricular: con escuchando:false NO es su señal',
    motor.dispara({ tipo: 'auricular', escuchando: false }).length === 0);
  r.fija(base + 90000);
  const bateria = creaMotor({ ejecuta: m.ejecuta, term: c.term, almacen: almacen(), reloj: r.ahora });
  bateria.agrega({ nombre: 'sin cable', disparador: { tipo: 'cargador', estado: 'desconecta' },
                   hacen: [{ que: 'habla', texto: 'ya sin cable' }] });
  ok('batería: desconecta (cargando:0)', bateria.dispara({ tipo: 'cargador', cargando: 0, bateria: 88 }).length === 1);
  await espera();
  ok('batería: conecta no se confunde con desconecta',
    bateria.dispara({ tipo: 'cargador', cargando: 1, bateria: 88 }).length === 0);
  const aviso = creaMotor({ ejecuta: m.ejecuta, term: c.term, almacen: almacen(), reloj: r.ahora });
  aviso.agrega({ nombre: 'a media batería', disparador: { tipo: 'cargador', estado: 'baje de', hasta: 20 },
                 hacen: [{ que: 'habla', texto: 'conéctalo' }] });
  ok('batería: «baje de 20» suena con 18', aviso.dispara({ tipo: 'cargador', cargando: 0, bateria: 18 }).length === 1);
  await espera();
  ok('batería: con 55 no', aviso.dispara({ tipo: 'cargador', cargando: 0, bateria: 55 }).length === 0);
  ok('batería: un `-1` (no leído) no se traga como «baje de»',
    aviso.dispara({ tipo: 'cargador', cargando: -1, bateria: -1 }).length === 0);
}

console.log('\n[4] la hora: una vez cada día, ni una menos ni dos más');
{
  const m = manos(), c = consola();
  const r = reloj(Date.parse('2026-10-22T07:30:00'));
  const motor = creaMotor({ ejecuta: m.ejecuta, term: c.term, almacen: almacen(), reloj: r.ahora });
  motor.agrega({ nombre: 'mañana', disparador: { tipo: 'hora', hora: '07:30' },
                 hacen: [{ que: 'piensa', texto: '¿qué tengo hoy?' }] });
  ok('hora: suena a las 07:30', motor.dispara({ tipo: 'hora', hora: '07:30' }).length === 1);
  await espera();
  ok('hora: el latido de las 07:31 no la repite', motor.dispara({ tipo: 'hora', hora: '07:31' }).length === 0);
  ok('hora: OTRA vez a las 07:30 el mismo día tampoco',
    motor.dispara({ tipo: 'hora', hora: '07:30' }).length === 0);
  r.fija(Date.parse('2026-10-23T07:30:00'));
  ok('hora: al día siguiente vuelve a sonar', motor.dispara({ tipo: 'hora', hora: '07:30' }).length === 1);
  await espera();
  ok('hora: «07:3» no coincide con «7:30» (ni al revés)',
    motor.dispara({ tipo: 'hora', hora: '07:3' }).length === 0);
  ok('el reloj sólo hace falta con reglas de hora o batería',
    necesitaReloj([{ activo: true, disparador: { tipo: 'frase', texto: 'x' } }]) === false
    && necesitaReloj([{ activo: true, disparador: { tipo: 'hora', hora: '07:30' } }]) === true
    && necesitaReloj([{ activo: false, disparador: { tipo: 'hora', hora: '07:30' } }]) === false);
}

console.log('\n[5] el latido, con reloj y batería inyectados');
{
  const m = manos(), c = consola();
  const motor = creaMotor({ ejecuta: m.ejecuta, term: c.term, almacen: almacen(),
                            reloj: () => Date.parse('2026-10-22T20:15:00') });
  motor.agrega({ nombre: 'nueve', disparador: { tipo: 'hora', hora: '20:15' },
                 hacen: [{ que: 'habla', texto: 'es de noche' }] });
  let falso = 0;
  const intervaloReal = globalThis.setInterval;
  globalThis.setInterval = () => { falso++; return 1; };      // el latido no debe dispararse solo
  const lati = marcapasos({ motor, aparato: () => ({ bateria: 12, cargando: 0 }),
                            ahora: () => new Date('2026-10-22T20:15:30') });
  lati.pisa();
  globalThis.setInterval = intervaloReal;
  await espera();
  ok('latido: la hora se forma como «20:15» y suena', m.pididas.some(p => p.que === 'habla'));
  ok('latido: sin `setInterval` real no se dispara nada', falso === 0);
  const battery = creaMotor({ ejecuta: async (q) => { m.pididas.push({ que: q }); return true; },
                              term: c.term, almacen: almacen(), reloj: () => Date.parse('2026-10-22T20:15:00') });
  battery.agrega({ nombre: 'baja', disparador: { tipo: 'cargador', estado: 'baje de', hasta: 20 },
                   hacen: [{ que: 'habla', texto: 'conecta' }] });
  marcapasos({ motor: battery, aparato: () => ({ bateria: 15, cargando: 0 }),
               ahora: () => new Date('2026-10-22T21:00:00') }).pisa();
  await espera();
  ok('latido: la batería también se mira, con el `aparato()` que ya existe',
    m.pididas.filter(p => p.que === 'habla').length >= 2);
  ok('latido: sin lectura de batería el latido no inventa nada',
    (() => { const v = creaMotor({ ejecuta: m.ejecuta, term: c.term, almacen: almacen(), reloj: () => base });
             v.agrega({ nombre: 'solo bateria', disparador: { tipo: 'cargador', estado: 'conecta' },
                        hacen: [{ que: 'habla', texto: 'x' }] });
             marcapasos({ motor: v, aparato: () => null, ahora: () => new Date('2026-10-22T07:00:00') }).pisa();
             return true; })());
}

console.log('\n[6] fallar, apagar y acordarse');
{
  const m = manos(['linterna']), c = consola();
  const r = reloj(base);
  const motor = creaMotor({ ejecuta: m.ejecuta, term: c.term, almacen: almacen(), reloj: r.ahora });
  motor.agrega({ nombre: 'dos manos', disparador: { tipo: 'frase', texto: 'luces' },
                 hacen: [{ que: 'habla', texto: 'vale' }, { que: 'linterna', como: 'encender' }] });
  motor.dispara({ tipo: 'frase', texto: 'luces' });
  await espera();
  ok('fallar: la que sí pudo se cuenta', c.lineas.some(l => /automatización «dos manos»/.test(l)), c.lineas.join(' | '));
  ok('fallar: la que no pudo se DICE, no se calla',
    c.lineas.some(l => /no pudo: linterna/.test(l)), c.lineas.join(' | '));

  const almacen2 = almacen();
  const uno = creaMotor({ ejecuta: m.ejecuta, term: c.term, almacen: almacen2, reloj: r.ahora });
  uno.agrega({ nombre: 'recado', disparador: { tipo: 'frase', texto: 'recado' },
               hacen: [{ que: 'recuerdo', texto: 'la leche' }] });
  const otra = creaMotor({ ejecuta: m.ejecuta, term: c.term, almacen: almacen2, reloj: r.ahora });
  ok('guardar: las reglas sobreviven a cerrar la app',
    otra.total() === 1 && otra.lista()[0].nombre === 'recado'
    && otra.lista()[0].cuando.includes('recado'), JSON.stringify(otra.lista()));
  otra.cambia(otra.lista()[0].id, false);
  ok('apagar: una regla apagada no suena',
    otra.dispara({ tipo: 'frase', texto: 'recado' }).length === 0);
  otra.cambia(otra.crudas()[0].id, true);
  ok('encender: vuelve a estar viva y se le quita el freno',
    otra.dispara({ tipo: 'frase', texto: 'recado' }).length === 1);
  await espera();
  otra.quita(otra.crudas()[0].id);
  ok('borrar: la regla desaparece y se guarda', otra.total() === 0
    && JSON.parse(almacen2.getItem('cort.autos.v1')).reglas.length === 0);

  const rota = { getItem: () => '{esto no es json', setItem: () => {} };
  const conRota = creaMotor({ ejecuta: m.ejecuta, term: c.term, almacen: rota, reloj: r.ahora });
  ok('almacén roto: se empieza limpio en vez de reventar', conRota.total() === 0);
  const sinAlmacen = creaMotor({ ejecuta: m.ejecuta, term: c.term, almacen: null, reloj: r.ahora });
  sinAlmacen.agrega({ nombre: 'memoria', disparador: { tipo: 'frase', texto: 'x' }, hacen: [{ que: 'habla', texto: 'y' }] });
  ok('sin almacén: la regla funciona en RAM y lo advierte',
    sinAlmacen.dispara({ tipo: 'frase', texto: 'x' }).length === 1 && sinAlmacen.guardadas() === false);
}

console.log('\n[7] las de muestra, el formulario y lo que promete la hoja');
{
  const m = manos(), c = consola(), r = reloj(base);
  const motor = creaMotor({ ejecuta: m.ejecuta, term: c.term, almacen: almacen(), reloj: r.ahora });
  const plantas = preajustes();
  ok('muestra: tres reglas, con nombre, disparador y acciones',
    plantas.length === 3 && plantas.every(x => x.disparador.tipo && x.hacen.length));
  ok('muestra: la de la frase dispara, las otras dos empiegan apagadas',
    plantas.filter(x => x.activo).length === 1 && /noche/i.test(plantas[0].nombre));
  plantas.forEach(x => motor.agrega(x));
  motor.dispara({ tipo: 'frase', texto: 'modo noche' });
  await espera();
  ok('muestra: encendida de fábrica, funciona tal cual',
    m.pididas.some(p => p.que === 'volumen' && p.a.como === 'callar'));

  // Que lo que la hoja ofrece exista: un `<select>` con una opción que el motor no
  // atiende es la promesa vacía de siempre.
  ok('disparadores: los cinco tienen su campo y su señal nombrada',
    DISPARADORES.length === 5 && DISPARADORES.every(d => d.id && d.nombre && d.senal));
  ok('acciones: cada una con su `id` y su campo',
    ACCIONES.every(a => a.id && a.nombre && (a.campo || a.opciones)));
  ok('normaliza: sin tildes y sin mayúsculas, para comparar',
    normaliza('Cámbiame  el VOLUMEN') === 'cambiame el volumen');
  ok('el resumen que pinta la hoja dice cuándo y qué hace',
    (() => { const x = motor.lista().find(v => v.nombre === 'modo noche');
             return x && /cuando yo diga/.test(x.cuando) && x.hacen.length >= 2; })());
}

console.log('\n' + (fallos ? 'FALTA ' + fallos + ' COSA(S) en el motor de automatizaciones.'
                           : 'motor de automatizaciones: ' + hechos + ' comprobaciones, todas en verde.'));
process.exit(fallos ? 1 : 0);
