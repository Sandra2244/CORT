import React, { useState } from 'react'

export default function AvatarPanel(){
  const [avatars, setAvatars] = useState<string[]>([])

  React.useEffect(()=>{
    fetch('/api/avatar/').then(r=>r.json()).then(d=>setAvatars(d.avatars || []))
  }, [])

  return (
    <div style={{marginBottom:12}}>
      <h3>Avatar</h3>
      <div style={{display:'flex', gap:8, flexDirection:'column'}}>
        {avatars.length===0 && <div style={{opacity:0.6}}>No hay avatares en /avatars. Sube un glTF/VRM en la carpeta avatars.</div>}
        {avatars.map(a=> (
          <div key={a} style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
            <span style={{fontSize:12}}>{a}</span>
            <button onClick={async ()=>{await fetch(`/api/avatar/${encodeURIComponent(a)}/set`,{method:'POST'})}} style={{padding:'4px 8px'}}>Usar</button>
          </div>
        ))}
      </div>
    </div>
  )
}
