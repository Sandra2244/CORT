package dev.sandra.cort;

/**
 * Los literales de la marca, en un solo sitio. Son los mismos de
 * `scripts/marca.py`, que a su vez son los de `apps/web/src/cort/palette.ts`:
 * la cara del teléfono, el anillo del `Canvas` y la PWA tienen que desentonar
 * por construcción y no por descuido.
 *
 * Está aquí y no dentro de `MainActivity` porque desde `v0.15.0` hay **dos**
 * caras que lo usan: la del WebView (el portátil encendido) y la nativa
 * (el teléfono solo). Copiar los seis enteros en cada una es la forma clásica
 * de que una se quede antigua.
 */
public final class Paleta {
    public static final int FONDO = 0xFF02040C;      // --bg
    public static final int CIAN = 0xFF5CE1FF;       // --tint
    public static final int VIOLETA = 0xFF8F5CFF;    // night.core
    public static final int CLARO = 0xFFDFFBFF;      // work.hot
    public static final int SUAVE = 0x8ADFFBFF;      // el mismo blanco al 54 %
    public static final int AVISO = 0xFFFFC46B;      // el ámbar del subtítulo
    public static final int CAMPO = 0xFF0A1620;      // el vidrio de las ventanas
    public static final int BORDE = 0xFF143040;      // el hilo que separa el registro

    private Paleta() {
    }
}
