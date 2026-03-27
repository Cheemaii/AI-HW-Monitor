const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const cors = require('cors');
const path = require('path');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

app.use(cors());
app.use(express.json({ limit: '2mb' }));
app.use(express.static(path.join(__dirname, '../frontend')));
app.get('/dashboard/:token', (req, res) =>
  res.sendFile(path.join(__dirname, '../frontend/index.html')));

// Store latest data per session token
const sessions = new Map();

// Broadcast to all WebSocket clients watching a specific token
function broadcast(token, data) {
  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN && client.token === token) {
      client.send(JSON.stringify(data));
    }
  });
}

// Python script POSTs sensor data here
app.post('/api/upload/:token', (req, res) => {
  const { token } = req.params;
  const payload = req.body;

  if (!payload || !payload.sensors) {
    return res.status(400).json({ error: 'Invalid payload' });
  }

  payload.timestamp = Date.now();
  sessions.set(token, payload);
  broadcast(token, payload);

  res.json({ ok: true, clients: [...wss.clients].filter(c => c.token === token).length });
});

// Get latest snapshot (for page load)
app.get('/api/snapshot/:token', (req, res) => {
  const data = sessions.get(req.params.token);
  if (!data) return res.status(404).json({ error: 'No data yet' });
  res.json(data);
});

// WebSocket: client sends token on connect
wss.on('connection', (ws) => {
  ws.on('message', (msg) => {
    try {
      const { token } = JSON.parse(msg);
      ws.token = token;
      // Send latest snapshot immediately
      const snap = sessions.get(token);
      if (snap) ws.send(JSON.stringify(snap));
    } catch {}
  });
  ws.on('error', () => {});
});

// Cleanup stale sessions older than 5 minutes
setInterval(() => {
  const cutoff = Date.now() - 5 * 60 * 1000;
  for (const [token, data] of sessions) {
    if (data.timestamp < cutoff) sessions.delete(token);
  }
}, 60000);

const PORT = process.env.PORT || 3001;
server.listen(PORT, () => console.log(`HWStream server running on port ${PORT}`));
