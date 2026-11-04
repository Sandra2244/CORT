/* S5: qué cuesta de verdad un ayudante de X11 en C, medido.
   Sólo LEE: pide _NET_CLIENT_LIST y el título de cada ventana. No mueve, no activa,
   no cierra nada —por eso puede correrse en la máquina real sin arena. */
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <X11/Xutil.h>
#include <stdio.h>

int main(void) {
  Display *d = XOpenDisplay(NULL);
  if (!d) { fprintf(stderr, "sin display\n"); return 2; }
  Window root = DefaultRootWindow(d);
  Atom lista = XInternAtom(d, "_NET_CLIENT_LIST", False);
  Atom tipo = None; int formato = 0;
  unsigned long n = 0, tras = 0;
  unsigned char *datos = NULL;
  if (XGetWindowProperty(d, root, lista, 0, 1024, False, XA_WINDOW, &tipo, &formato,
                         &n, &tras, &datos) != Success || !datos) {
    fprintf(stderr, "el gestor no expone _NET_CLIENT_LIST\n");
    XCloseDisplay(d);
    return 1;
  }
  Window *wins = (Window *)datos;
  printf("%lu ventanas\n", n);
  for (unsigned long i = 0; i < n; i++) {
    XTextProperty tp; char *s = NULL;
    if (XGetWMName(d, wins[i], &tp) && tp.value) s = (char *)tp.value;
    printf("  0x%08lx  %s\n", (unsigned long)wins[i], s ? s : "(sin titulo)");
    if (s) XFree(tp.value);
  }
  XFree(datos);
  XCloseDisplay(d);
  return 0;
}
