#!/usr/bin/env node
/**
 * CORT Bridge Server
 * WebSocket orchestration layer between frontend and backend services
 * Handles real-time communication, message routing, and service coordination
 */

import express from 'express';
import { WebSocketServer, WebSocket } from 'ws';
import axios from 'axios';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
const PORT = parseInt(process.env.BRIDGE_PORT || '8787');
const CORE_URL = process.env.CORE_URL || 'http://localhost:8000';
const VOICE_URL = process.env.VOICE_URL || 'http://localhost:8001';

app.use(express.json());

// Colors for console
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

const log = (msg: string, color: string = colors.reset) => {
  console.log(`${color}${msg}${colors.reset}`);
};

// Health check
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

// REST endpoint for direct message processing
app.post('/message', async (req, res) => {
  try {
    const { content } = req.body;
    
    log(`📨 Processing message: "${content}"`, colors.yellow);
    
    // Forward to core service
    const response = await axios.post(`${CORE_URL}/chat`, {
      content,
      author: 'user'
    });
    
    log(`✅ Response generated`, colors.green);
    res.json(response.data);
  } catch (error) {
    log(`❌ Error processing message: ${error}`, colors.yellow);
    res.status(500).json({ error: 'Failed to process message' });
  }
});

// WebSocket server configuration
const wss = new WebSocketServer({ noServer: true });

let connectedClients = 0;

wss.on('connection', (ws: WebSocket) => {
  connectedClients++;
  log(`🔌 Client connected (Total: ${connectedClients})`, colors.green);
  
  // Send welcome message
  ws.send(JSON.stringify({
    type: 'connected',
    message: 'Connected to CORT Bridge',
    timestamp: new Date().toISOString(),
    clientCount: connectedClients
  }));
  
  // Handle incoming messages
  ws.on('message', async (data) => {
    try {
      const message = JSON.parse(data.toString());
      log(`📨 [${connectedClients}] Received: ${message.type}`, colors.cyan);
      
      // Route based on message type
      if (message.type === 'message' || message.type === 'chat') {
        try {
          // Forward to core service
          const response = await axios.post(`${CORE_URL}/chat`, {
            content: message.content,
            author: 'user'
          });
          
          log(`✅ Response from core`, colors.green);
          
          // Send back to client
          ws.send(JSON.stringify({
            type: 'response',
            content: response.data.content,
            emotion: response.data.emotion,
            timestamp: response.data.timestamp,
            status: 'success'
          }));
        } catch (coreError) {
          log(`❌ Core service error`, colors.yellow);
          ws.send(JSON.stringify({
            type: 'error',
            message: 'Failed to get response from core',
            timestamp: new Date().toISOString()
          }));
        }
      } 
      else if (message.type === 'context') {
        // Update context in core
        try {
          await axios.post(`${CORE_URL}/context`, message.data);
          ws.send(JSON.stringify({
            type: 'context_updated',
            status: 'success'
          }));
        } catch (error) {
          ws.send(JSON.stringify({
            type: 'error',
            message: 'Failed to update context'
          }));
        }
      }
      else if (message.type === 'personality') {
        // Change personality
        try {
          const response = await axios.post(
            `${CORE_URL}/personality/${message.preset}`
          );
          ws.send(JSON.stringify({
            type: 'personality_updated',
            preset: message.preset,
            status: 'success'
          }));
        } catch (error) {
          ws.send(JSON.stringify({
            type: 'error',
            message: 'Failed to update personality'
          }));
        }
      }
      else if (message.type === 'ping') {
        ws.send(JSON.stringify({
          type: 'pong',
          timestamp: new Date().toISOString()
        }));
      }
    } catch (error) {
      log(`❌ Error processing message: ${error}`, colors.yellow);
      ws.send(JSON.stringify({
        type: 'error',
        message: 'Invalid message format'
      }));
    }
  });
  
  // Handle client disconnect
  ws.on('close', () => {
    connectedClients--;
    log(`❌ Client disconnected (Total: ${connectedClients})`, colors.yellow);
  });
  
  // Handle errors
  ws.on('error', (error) => {
    log(`❌ WebSocket error: ${error}`, colors.yellow);
  });
});

// HTTP upgrade for WebSocket
const server = app.listen(PORT, () => {
  log(`\n${'═'.repeat(50)}`, colors.blue);
  log(`🚀 CORT Bridge running`, colors.bright);
  log(`${'═'.repeat(50)}`, colors.blue);
  log(`   Bridge: ws://0.0.0.0:${PORT}`, colors.cyan);
  log(`   Core:   ${CORE_URL}`, colors.cyan);
  log(`   Voice:  ${VOICE_URL}`, colors.cyan);
  log(`   Health: http://0.0.0.0:${PORT}/health`, colors.cyan);
  log(`${'═'.repeat(50)}\n`, colors.blue);
});

// Handle HTTP upgrade for WebSocket
server.on('upgrade', (request, socket, head) => {
  wss.handleUpgrade(request, socket, head, (ws) => {
    wss.emit('connection', ws, request);
  });
});

// Graceful shutdown
process.on('SIGTERM', () => {
  log('\n🛑 SIGTERM received, shutting down...', colors.yellow);
  server.close(() => {
    log('Server closed', colors.reset);
    process.exit(0);
  });
});
