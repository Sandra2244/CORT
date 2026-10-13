/**
 * La ventana «ayuda»: el manual que ya no está repartido por los botones.
 *
 * En la versión anterior cada mando traía su párrafo explicativo pegado dentro
 * del riel, y por eso la cara se llenaba de texto. Aquí el manual vive en UNA
 * ventana y se abre con su nombre o con `?` — el resto de la pantalla puede
 * respirar.
 */
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
        el reconocimiento necesita internet (Edge o Chrome).
      </p>
      <p>
        <b>cuerpo</b> — CORT proyecta los archivos de tu carpeta. Se declara con{' '}
        <code>CORT_AVATAR_DIR=/ruta/a/tus/atuendos</code> en el <code>.env</code> y
        reiniciando CORT. Los <code>.vrm</code> se montan como cuerpo 3D dentro del
        mismo canvas.
      </p>
      <p>
        <b>atajos</b> — <code>/</code> abre la charla con el cursor listo;{' '}
        <code>1</code>–<code>6</code> saltan a las seis ventanas; <code>Esc</code>{' '}
        despide la de enfrente. El temporizador y las acciones se piden escribiendo:
        «pon un temporizador de 5 minutos», «baja el volumen».
      </p>
    </div>
  )
}
