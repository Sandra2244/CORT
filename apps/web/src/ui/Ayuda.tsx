/**
 * La ventana «ayuda»: el manual que ya no está repartido por los botones.
 *
 * En la versión anterior cada mando traía su párrafo explicativo pegado dentro
 * del riel, y por eso la cara se llenaba de texto. Aquí el manual vive en UNA
 * ventana y se abre con su nombre o con `?` — el resto de la pantalla puede
 * respirar.
 */
import { ACCESOS } from '../cort/teclas'

export function Ayuda() {
  return (
    <div className="ayuda">
      <p>
        <b>las ventanas</b> — el muelle de abajo enciende y apaga cada una. Se
        arrastran desde su tubo superior con el dedo o con el ratón, se echan con{' '}
        <b>✕</b> o con <code>Esc</code> (cierra la última que tocaste), y el botón{' '}
        <b>⤾</b> la devuelve a su sitio. Se pueden tener varias abiertas a la vez:
        la que se toca queda delante.
      </p>
      <p>
        <b>gestos con la cámara</b> — desenfocar con los dedos delante del objetivo
        encoge el reactor; enfocar lo devuelve. Al pulsar el botón el navegador
        pregunta: <b>permitir</b>. Si dijo que no una vez, se corrige en el candado
        de la dirección → <b>Permisos → Cámara</b>. Por la red con <code>http://</code>{' '}
        el navegador no da la cámara: hace falta HTTPS.
      </p>
      <p>
        <b>voz</b> — <b>que me hable</b> lee en voz alta lo que CORT responde.{' '}
        <b>hablarle</b> abre el micrófono y conversa: pide permiso la primera vez y
        el reconocimiento necesita internet (Edge o Chrome). El micrófono{' '}
        <b>no se apaga al cerrar la ventana</b>: vive fuera de ella, así que puedes
        dejarlo escuchando y seguir mirando la cara.
      </p>
      <p>
        <b>«OK CORT»</b> — el tercer botón deja el micrófono vigilando: cuando dices{' '}
        <b>OK CORT</b> (también <b>oye CORT</b> o <b>hola CORT</b>) suena un pitido, el
        anillo se forma y hablas: puedes decir la orden aparte o de corrido («OK CORT,
        sube el volumen»). Al responder vuelve a esperar. <b>Ojo:</b> el navegador no
        tiene una palabra de activación local, así que mientras esté activo el audio se
        manda al servicio de reconocimiento de Edge o Chrome. Apágalo cuando no lo
        necesites.
      </p>
      <p>
        <b>reposo y escucha</b> — si nadie toca nada durante 30 segundos, el reactor se
        deshace en una nube de puntos; cualquier gesto o mensaje lo devuelve. Con el
        micrófono abierto (<b>hablarle</b>) la nube se junta en un anillo que gira y se
        agita con tu voz; mientras CORT piensa o habla vuelve el reactor. Para verlos sin
        esperar: añade <code>?demo=reposo</code> o <code>?demo=escucha</code> a la
        dirección, o <code>?reposo=10</code> para que el reposo llegue a los 10 segundos
        (<code>?reposo=0</code> lo desactiva).
      </p>
      <p>
        <b>cuerpo</b> — CORT proyecta los archivos de tu carpeta. Se declara con{' '}
        <code>CORT_AVATAR_DIR=/ruta/a/tus/atuendos</code> en el <code>.env</code> y
        reiniciando CORT. Los <code>.vrm</code> se montan como cuerpo 3D dentro del
        mismo canvas.
      </p>
      <p>
        <b>atajos</b> — <code>/</code> abre la charla con el cursor listo,{' '}
        <code>?</code> trae esta ayuda y <code>Esc</code> despide la ventana de
        enfrente (no todas de un golpe). Cada superficie tiene su número, y el
        número es el que se ve en el muelle:
      </p>
      {/*
       * La tabla se genera desde `cort/teclas.ts`, no se teclea a mano aquí. Es
       * el motivo de que exista esa lista compartida: escrita a mano, la ayuda
       * puede prometer una tecla que el teclado ya no escucha, y nadie se entera
       * hasta que pulsa.
       */}
      <ul className="ayuda-teclas">
        {ACCESOS.map(({ id, etiqueta, tecla }) => (
          <li key={id}>
            <code>{tecla}</code> <b>{etiqueta}</b>
          </li>
        ))}
      </ul>
      <p>
        El temporizador y las acciones se piden escribiendo: «pon un temporizador de
        5 minutos», «baja el volumen».
      </p>
    </div>
  )
}
