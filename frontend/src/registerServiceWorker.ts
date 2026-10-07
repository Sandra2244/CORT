// Registra un service worker básico si el navegador lo soporta
export function registerServiceWorker(){
  if('serviceWorker' in navigator){
    window.addEventListener('load', ()=>{
      navigator.serviceWorker.register('/sw.js').then(reg=>{
        console.log('ServiceWorker registrado', reg)
      }).catch(err=>{
        console.warn('ServiceWorker error', err)
      })
    })
  }
}
