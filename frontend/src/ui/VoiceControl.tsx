import React, { useState } from 'react'

export default function VoiceControl({ onTranscribed }:{ onTranscribed?: (t:string)=>void }){
  const [lastText, setLastText] = useState('')
  const doSTT = async ()=>{
    // placeholder: llamamos al endpoint y mostramos resultado
    const res = await fetch('/api/voice/stt', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ audio_b64: null }) })
    const j = await res.json()
    setLastText(j.text)
    onTranscribed?.(j.text)
  }
  const doTTS = async ()=>{
    const text = prompt('Texto para TTS:')
    if(!text) return
    const res = await fetch('/api/voice/tts', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ text }) })
    const j = await res.json()
    alert('TTS generado (placeholder): '+JSON.stringify(j))
  }
  return (
    <div style={{marginBottom:12}}>
      <h3>Voz</h3>
      <div style={{display:'flex', gap:8}}>
        <button onClick={doSTT} style={{padding:'6px 10px'}}>STT</button>
        <button onClick={doTTS} style={{padding:'6px 10px'}}>TTS</button>
      </div>
      <div style={{marginTop:8, opacity:0.8, fontSize:13}}>Transcripción: {lastText}</div>
    </div>
  )
}
