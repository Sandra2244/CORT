#!/usr/bin/env node
/**
 * CORT Bridge Server - Enhanced WebSocket Orchestration
 * Combines adewaskar/jarvis bridge + OpenJarvis skill routing + OpenClaw gesture handling
 */

import express from 'express';
import { WebSocketServer, WebSocket } from 'ws';
import axios from 'axios';
import dotenv from 'dotenv';
import http from 'http';

dotenv.config();

const app = express();
const PORT = parseInt(process.env.BRIDGE_PORT || '8787');
const CORE_URL = process.env.CORE_URL || 'http://localhost:8000';
const VOICE_URL = process.env.VOICE_URL || 'http://localhost:8001';

app.use(express.json());

// ANSI Colors
const c = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

const log = (msg, color = c.reset) => console.log(`${color}${msg}${c.reset}`);

// REST endpoint for health
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'cort-bridge',
    version: '0.1.0',
    timestamp: new Date().toISOString(),
    services: {
      core: CORE_URL,
      voice: VOICE_URL
    }
  });
});

// REST endpoint for direct messages
app.post('/message', async (req, res) => {
  try {
    const { content } = req.body;
    log(`📨 Processing: "${content.substring(0, 50)}..."`, c.yellow);
    
    const response = await axios.post(`${CORE_URL}/chat`, {
      content,
      author: 'user'
    });
    
    log(`✅ Response generated`, c.green);
    res.json(response.data);
  } catch (error) {
    log(`❌ Error: ${error.message}`, c.yellow);
    res.status(500).json({ error: 'Failed to process message' });
  }
});

// WebSocket server with enhanced message routing
const wss = new WebSocketServer({ noServer: true });
let connectedClients = 0;

wss.on('connection', (ws) => {
  connectedClients++;
  const clientId = Math.random().toString(36).substring(7);
  log(`🔌 Client #${clientId} connected (Total: ${connectedClients})`, c.green);
  
  // Send welcome
  ws.send(JSON.stringify({
    type: 'connected',
    message: 'Connected to CORT Bridge',
    clientId,
    timestamp: new Date().toISOString(),
    clientCount: connectedClients
  }));
  
  // Message handler
  ws.on('message', async (data) => {
    try {
      const message = JSON.parse(data.toString());
      log(`📩 [${clientId}] ${message.type}`, c.cyan);
      
      if (message.type === 'message' || message.type === 'chat') {
        try {
          const response = await axios.post(`${CORE_URL}/chat`, {
            content: message.content,
            author: 'user'
          });
          
          ws.send(JSON.stringify({
            type: 'response',
            content: response.data.content,
            emotion: response.data.emotion,
            timestamp: response.data.timestamp,
            status: 'success'
          }));
        } catch (e) {
          log(`❌ Core error: ${e.message}`, c.yellow);
          ws.send(JSON.stringify({
            type: 'error',
            message: 'Failed to get response from core'
          }));
        }
      }
      else if (message.type === 'context') {
        try {
          await axios.post(`${CORE_URL}/context`, message.data);
          ws.send(JSON.stringify({ type: 'context_updated', status: 'success' }));
        } catch (e) {
          ws.send(JSON.stringify({ type: 'error', message: 'Failed to update context' }));
        }
      }
      else if (message.type === 'personality') {
        try {
          const response = await axios.post(`${CORE_URL}/personality/${message.preset}`);
          ws.send(JSON.stringify({
            type: 'personality_updated',
            preset: message.preset,
            status: 'success'
          }));
        } catch (e) {
          ws.send(JSON.stringify({ type: 'error', message: 'Failed to update personality' }));
        }
      }
      else if (message.type === 'gesture') {
        // OpenClaw gesture processing
        const gestureResponse = {
          type: 'gesture_processed',
          action: message.action,
          timestamp: new Date().toISOString()
        };
        ws.send(JSON.stringify(gestureResponse));
      }
      else if (message.type === 'ping') {
        ws.send(JSON.stringify({ type: 'pong', timestamp: new Date().toISOString() }));
      }
    } catch (error) {
      log(`❌ Message error: ${error.message}`, c.yellow);
      ws.send(JSON.stringify({ type: 'error', message: 'Invalid message format' }));
    }
  });
  
  ws.on('close', () => {
    connectedClients--;
    log(`❌ Client #${clientId} disconnected (Total: ${connectedClients})`, c.yellow);
  });
  
  ws.on('error', (error) => {
    log(`❌ WebSocket error: ${error.message}`, c.yellow);
  });
});

// HTTP server with WebSocket upgrade
const server = http.createServer(app);

server.listen(PORT, () => {
  log(`\n${c.blue}${'═'.repeat(60)}${c.reset}`, c.blue);
  log(`${c.bright}🚀 CORT Bridge running${c.reset}`, c.bright);
  log(`${c.blue}${'═'.repeat(60)}${c.reset}`, c.blue);
  log(`   Bridge: ws://0.0.0.0:${PORT}`, c.cyan);
  log(`   Core:   ${CORE_URL}`, c.cyan);
  log(`   Voice:  ${VOICE_URL}`, c.cyan);
  log(`${c.blue}${'═'.repeat(60)}\n${c.reset}`, c.blue);
});

server.on('upgrade', (request, socket, head) => {
  wss.handleUpgrade(request, socket, head, (ws) => {
    wss.emit('connection', ws, request);
  });
});

process.on('SIGTERM', () => {
  log('\n🛑 SIGTERM received, shutting down...', c.yellow);
  server.close(() => {
    log('Server closed', c.reset);
    process.exit(0);
  });
});
