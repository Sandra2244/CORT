import { useEffect, useState, useSyncExternalStore } from 'react'
import { avatarUrl, getSnapshot, pedirAvatares, subscribe } from '../cort/connection'

/**
 * El cuerpo de CORT: un atuendo de disco convertido en proyección.
 *
 * Es 2D y es a propósito. El VRM de 18 MB con sus ocho atuendos (150 MB en total)
 * existe, está servido por el core y se puede elegir desde aquí abajo — pero
 * cargar una malla esqueletizada con texturas en una máquina de 2 núcleos y ~286
 * MiB libres, con el reactor ya pintando a 17 fps, es prometer algo que no he
 * medido. Lo que sí funciona en este hardware es la proyección translúcida de los
 * sprites que ella misma tiene en disco, y por eso el avatar arranca así. El
 * intentón 3D está anotado en `docs/STATUS.md` con la medida que falta.
 *
 * La transparencia la pone el fondo del propio PNG —sus archivos se llaman «sin
 * fondo» por eso—, y el tinte azul-morado va encima con `soft-light` para que el
 * color de la ropa se siga distinguiendo. Si el tinte fuera un filtro de color
 * total, los ocho atuendos serían del mismo cyan y cambiar de vestido no se
 * notaría.
 */
export function Avatar({ nombre, onFallo }: { nombre: string; onFallo: () => void }) {
  const [lista, setLista] = useState(false)
  // Se suscribe aquí y no recibe `thinking` por props: el latido le toca sólo a
  // esta figura, y App no tiene por qué repintarse con cada estado del core.
  const s = useSyncExternalStore(subscribe, getSnapshot)

  // Un atuendo nuevo vuelve a empezar: si no, la figura vieja se quedaría
  // brillando mientras carga la nueva, y parecería que el cambio no hizo nada.
  useEffect(() => setLista(false), [nombre])

  return (
    <div
      className={`avatar ${lista ? 'lista' : ''} ${s.thinking ? 'procesando' : ''}`}
      role="img"
      aria-label={`CORT con cuerpo holográfico, atuendo ${nombre}`}
    >
      <img
        src={avatarUrl(nombre)}
        alt=""
        draggable={false}
        onLoad={() => setLista(true)}
        onError={onFallo}
      />
      <span className="avatar-linea" aria-hidden="true" />
      <span className="avatar-nombre">{nombre}</span>
    </div>
  )
}

/**
 * El selector táctil de archivos de atuendo.
 *
 * Sólo se abre cuando la bandeja está abierta, y sólo entonces pide la lista al
 * core: mientras nadie la pida, CORT no lee la carpeta de avatares de nadie.
 *
 * Hay dos tipos de mosaico. Las **imágenes** se eligen con su miniatura; los
 * **VRM** se eligen con un recuandro de texto, porque una vista previa de una
 * malla costaría renderizarla, y aquí se carga el modelo entero para poder
 * proyectarlo. Un botón gris que no hace nada sería peor: es lo que eran antes,
 * y se acabó cuando el cargador 3D empezó a funcionar.
 */
export function Atuendos({ visible, elegido, onElegir }: {
  visible: boolean
  elegido: string | null
  onElegir: (nombre: string | null) => void
}) {
  const s = useSyncExternalStore(subscribe, getSnapshot)

  useEffect(() => {
    if (visible && s.avatars === null) pedirAvatares()
  }, [visible, s.avatars])

  const items = s.avatars ?? []
  const imagenes = items.filter((i) => i.mime.startsWith('image/'))
  const modelos = items.filter((i) => !i.mime.startsWith('image/'))

  return (
    <div className="atuendos">
      <div className="atuendos-cabecalzo">
        <span className="zoom-label">atuendo</span>
        {elegido && (
          <button type="button" className="atuendos-volver" onClick={() => onElegir(null)}>
            volver al reactor
          </button>
        )}
      </div>

      {s.avatars === null && <p className="atuendos-nota">leyendo tu carpeta de avatares…</p>}
      {s.avatars !== null && imagenes.length === 0 && (
        <p className="atuendos-nota">
          {/* Sin `CORT_AVATAR_DIR` no hay catálogo, y decir «no encuentro atuendos»
              sin explicar por qué mandaría a buscar archivos a una carpeta que
              todavía no existe. */}
          no hay atuendos que mostrar. Escribe en el <code>.env</code>{' '}
          <code>CORT_AVATAR_DIR=/ruta/a/tus/atuendos</code> y reinicia CORT.
        </p>
      )}

      {imagenes.length > 0 && (
        <div className="atuendos-mosaico" role="group" aria-label="atuendos disponibles">
          {imagenes.map((i) => (
            <button
              key={i.nombre}
              type="button"
              className={`atuendo ${elegido === i.nombre ? 'activo' : ''}`}
              onClick={() => onElegir(elegido === i.nombre ? null : i.nombre)}
              aria-pressed={elegido === i.nombre}
              title={`${i.nombre} · ${(i.bytes / 1024 / 1024).toFixed(1)} MB`}
            >
              <img src={avatarUrl(i.nombre)} alt="" loading="lazy" draggable={false} />
              <span>{i.nombre.replace(/\.[a-z]+$/i, '')}</span>
            </button>
          ))}
        </div>
      )}

      {modelos.length > 0 && (
        <div className="atuendos-mosaico" role="group" aria-label="cuerpos 3D disponibles">
          {modelos.map((i) => (
            <button
              key={i.nombre}
              type="button"
              className={`atuendo atuendo-3d ${elegido === i.nombre ? 'activo' : ''}`}
              onClick={() => onElegir(elegido === i.nombre ? null : i.nombre)}
              aria-pressed={elegido === i.nombre}
              title={`${i.nombre} · ${(i.bytes / 1024 / 1024).toFixed(1)} MB · cuerpo 3D`}
            >
              {/* Sin miniatura: la cara del botón dice lo que es, y el peso
                  también — son archivos de 16 a 21 MB, y elegirlos a ciegas no. */}
              <span className="atuendo-3d-marca">3D</span>
              <span>{i.nombre.replace(/\.[a-z]+$/i, '')}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
