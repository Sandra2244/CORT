import React, { useState } from 'react'
import HologramScene from './ui/HologramScene'
import { generate } from './services/api'
import AvatarPanel from './ui/AvatarPanel'
import VoiceControl from './ui/VoiceControl'

export default function App(){
  const [messages, setMessages] = useState<any[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)

  const send = async () => {
    if(!input) return
    const userMsg = { role: 'user', content: input }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setInput("")
    setLoading(true)
    try{
      const resp = await generate({ model: 'llama2', messages: newMessages })
      const assistant = resp || { reply: 'Sin respuesta (scaffold)'}
      setMessages([...newMessages, { role: 'assistant', content: JSON.stringify(assistant) }])
    }catch(e){
      setMessages([...newMessages, { role: 'assistant', content: 'Error: '+String(e) }])
    }finally{ setLoading(false) }
  }

  return (
    <div style={{display:'grid', gridTemplateColumns:'1fr 420px', height:'100vh'}}>
      <div style={{padding:24}}>
        <HologramScene />
      </div>
      <div style={{background:'rgba(255,255,255,0.03)', padding:16, color:'#cfe9ff'}}>
        <h2>CORT — Chat (scaffold)</h2>
        <AvatarPanel />
        <VoiceControl onTranscribed={(t)=>{ setInput(prev => prev ? prev + '\n' + t : t) }} />
        <div style={{height: '45%', overflow:'auto', background:'rgba(0,0,0,0.2)', padding:8}}>
          {messages.map((m, i)=> (
            <div key={i} style={{margin:6, padding:8, borderRadius:8, background: m.role==='user' ? 'rgba(0,150,255,0.12)' : 'rgba(255,255,255,0.03)'}}>
              <b>{m.role}:</b> <span style={{whiteSpace:'pre-wrap'}}>{m.content}</span>
            </div>
          ))}
        </div>
        <div style={{marginTop:8}}>
          <input value={input} onChange={e=>setInput(e.target.value)} style={{width:'100%', padding:8, borderRadius:6, border:'none', background:'rgba(255,255,255,0.02)', color:'#cfe9ff'}} placeholder='Escribe algo...' />
          <button onClick={send} disabled={loading} style={{marginTop:8, width:'100%', padding:10, borderRadius:6, background:'linear-gradient(90deg,#00b4ff,#6a00ff)', color:'white', border:'none'}}>Enviar</button>
        </div>
      </div>
    </div>
  )
}
