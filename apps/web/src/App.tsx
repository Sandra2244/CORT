import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import './App.css'

interface Message {
  type: string
  content?: string
  message?: string
  author?: string
  emotion?: string
  timestamp?: string
}

interface ChatMessage {
  role: string
  text: string
  emotion?: string
}

function App() {
  const wsRef = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isListening, setIsListening] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [currentEmotion, setCurrentEmotion] = useState('neutral')
  const [personality, setPersonality] = useState('friendly')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [clientCount, setClientCount] = useState(0)

  // Connect to WebSocket bridge
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.hostname}:8787`
    
    console.log(`🔌 Connecting to ${wsUrl}`)
    wsRef.current = new WebSocket(wsUrl)

    wsRef.current.onopen = () => {
      console.log('✅ Connected to CORT Bridge')
      setIsConnected(true)
    }

    wsRef.current.onmessage = (event) => {
      const data: Message = JSON.parse(event.data)
      console.log('📨 Message received:', data)

      if (data.type === 'connected') {
        setMessages([{ role: 'system', text: '✨ CORT Ready to assist' }])
        // Extract client count if available
        if (data.clientCount) {
          setClientCount(data.clientCount)
        }
      } else if (data.type === 'response') {
        setIsLoading(false)
        setMessages(prev => [...prev, { 
          role: 'cort', 
          text: data.content || data.message || '',
          emotion: data.emotion
        }])
        if (data.emotion) {
          setCurrentEmotion(data.emotion)
        }
      } else if (data.type === 'error') {
        setIsLoading(false)
        setMessages(prev => [...prev, { 
          role: 'error', 
          text: data.message || 'An error occurred' 
        }])
      }
    }

    wsRef.current.onerror = (error) => {
      console.error('❌ WebSocket error:', error)
      setIsConnected(false)
    }

    wsRef.current.onclose = () => {
      console.log('Connection closed')
      setIsConnected(false)
    }

    return () => {
      wsRef.current?.close()
    }
  }, [])

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = () => {
    if (!inputValue.trim() || !isConnected) return

    const userMessage = inputValue
    setMessages(prev => [...prev, { role: 'user', text: userMessage }])
    setInputValue('')
    setIsLoading(true)

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'message',
        content: userMessage
      }))
    }
  }

  const changePersonality = (newPersonality: string) => {
    setPersonality(newPersonality)
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'personality',
        preset: newPersonality
      }))
    }
  }

  const emotionColors: Record<string, string> = {
    'happy': 'from-yellow-400 to-orange-500',
    'neutral': 'from-blue-400 to-cyan-500',
    'thinking': 'from-purple-400 to-pink-500',
    'sad': 'from-blue-600 to-indigo-700',
    'excited': 'from-red-400 to-yellow-500',
    'thoughtful': 'from-indigo-400 to-purple-500'
  }

  const getEmotionColor = () => emotionColors[currentEmotion] || emotionColors['neutral']

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-900 to-slate-950 text-white overflow-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 right-0 w-96 h-96 bg-purple-600/20 rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-blue-600/20 rounded-full blur-3xl"></div>
      </div>

      <div className="relative z-10">
        {/* Header */}
        <header className="border-b border-purple-500/20 backdrop-blur-md bg-slate-900/30 sticky top-0">
          <div className="max-w-6xl mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <motion.div
                  className={`w-10 h-10 rounded-full bg-gradient-to-br ${getEmotionColor()} flex items-center justify-center shadow-lg`}
                  animate={{ 
                    scale: isConnected ? [1, 1.1, 1] : 1,
                    boxShadow: isConnected 
                      ? ['0 0 20px rgba(59, 130, 246, 0.5)', '0 0 40px rgba(59, 130, 246, 0.8)', '0 0 20px rgba(59, 130, 246, 0.5)']
                      : '0 0 0px rgba(59, 130, 246, 0)'
                  }}
                  transition={{ repeat: isConnected ? Infinity : 0, duration: 2 }}
                >
                  <span className="text-lg">⚡</span>
                </motion.div>
                <div>
                  <h1 className="text-3xl font-bold tracking-wider bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">CORT</h1>
                  <p className="text-xs text-purple-300">v0.1.0-alpha • {isConnected ? '🟢 Online' : '🔴 Offline'}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-300">Personality: <span className="text-cyan-400 font-semibold">{personality}</span></p>
                <p className="text-xs text-gray-400">Active clients: {clientCount}</p>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-6xl mx-auto px-4 py-8 min-h-[calc(100vh-200px)] flex flex-col gap-8">
          {/* Avatar Section */}
          <div className="flex flex-col items-center justify-center py-8">
            <motion.div
              className="relative w-64 h-64"
              animate={{ y: [0, -15, 0] }}
              transition={{ repeat: Infinity, duration: 4 }}
            >
              {/* Holographic Avatar */}
              <motion.div
                className={`absolute inset-0 rounded-full bg-gradient-to-br ${getEmotionColor()} shadow-2xl`}
                animate={{ opacity: [0.6, 0.8, 0.6] }}
                transition={{ repeat: Infinity, duration: 3 }}
              >
                <div className="flex items-center justify-center h-full">
                  <motion.span 
                    className="text-8xl"
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 8, linear: true }}
                  >
                    🔵
                  </motion.span>
                </div>
              </motion.div>

              {/* Outer Ring */}
              <motion.div
                className="absolute inset-0 rounded-full border-2 border-transparent border-t-cyan-400 border-r-cyan-400 shadow-lg"
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 3, linear: true }}
              ></motion.div>

              {/* Inner Pulsing Ring */}
              <motion.div
                className="absolute inset-8 rounded-full border border-purple-400/50"
                animate={{ scale: [1, 1.1, 1] }}
                transition={{ repeat: Infinity, duration: 2 }}
              ></motion.div>
            </motion.div>

            {/* Status Text */}
            <motion.h2 
              className="text-2xl font-semibold mt-6 text-center"
              animate={{ opacity: [0.8, 1, 0.8] }}
              transition={{ repeat: Infinity, duration: 2 }}
            >
              {isLoading ? '🧠 Thinking...' : isListening ? '🎤 Listening...' : '✨ Ready to assist'}
            </motion.h2>
          </div>

          {/* Personality Selector */}
          <div className="flex justify-center gap-2 flex-wrap">
            {['friendly', 'professional', 'technical', 'creative'].map(p => (
              <motion.button
                key={p}
                onClick={() => changePersonality(p)}
                className={`px-4 py-2 rounded-full font-semibold transition-all ${
                  personality === p
                    ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg'
                    : 'bg-slate-700/50 text-gray-300 hover:bg-slate-600'
                }`}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </motion.button>
            ))}
          </div>

          {/* Messages Area */}
          <motion.div 
            className="flex-1 space-y-4 bg-slate-900/40 rounded-2xl p-6 border border-purple-500/20 overflow-y-auto max-h-96 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <AnimatePresence>
              {messages.length === 0 ? (
                <div className="text-center text-gray-400 py-8">
                  <p className="text-lg">👋 Welcome to CORT</p>
                  <p className="text-sm mt-2">Start a conversation to get started</p>
                </div>
              ) : (
                messages.map((msg, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-xs px-4 py-2 rounded-lg ${
                        msg.role === 'user'
                          ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white'
                          : msg.role === 'system'
                          ? 'bg-amber-900/40 text-amber-200 border border-amber-500/30'
                          : msg.role === 'error'
                          ? 'bg-red-900/40 text-red-200 border border-red-500/30'
                          : 'bg-cyan-600/30 text-cyan-100 border border-cyan-400/30'
                      }`}
                    >
                      {msg.text}
                    </div>
                  </motion.div>
                ))
              )}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </motion.div>
        </main>

        {/* Input Section */}
        <footer className="border-t border-purple-500/20 backdrop-blur-md bg-slate-900/30 sticky bottom-0">
          <div className="max-w-6xl mx-auto px-4 py-4">
            <div className="space-y-3">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                  placeholder={isConnected ? "Type your message..." : "Connecting..."}
                  disabled={!isConnected || isLoading}
                  className="flex-1 bg-slate-800/50 border border-purple-500/30 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/30 disabled:opacity-50 transition"
                />
                <motion.button
                  onClick={sendMessage}
                  disabled={!isConnected || isLoading}
                  className="bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50 px-6 py-3 rounded-lg font-semibold transition shadow-lg"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {isLoading ? '⏳' : '📤'}
                </motion.button>
                <motion.button
                  onClick={() => setIsListening(!isListening)}
                  className={`px-4 py-3 rounded-lg font-semibold transition shadow-lg ${
                    isListening
                      ? 'bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-500 hover:to-orange-500'
                      : 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500'
                  } disabled:opacity-50`}
                  disabled={!isConnected}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {isListening ? '🎤' : '🔊'}
                </motion.button>
              </div>
              <p className="text-xs text-gray-400 text-center">💡 Tip: Say "Hey CORT" to activate voice mode, or just type your message</p>
            </div>
          </div>
        </footer>
      </div>
    </div>
  )
}

export default App
