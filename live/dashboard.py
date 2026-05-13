"""
Real-time monitoring dashboard for trading activity.
Streams events to web UI via Server-Sent Events (SSE).
"""
import json
from datetime import datetime
from threading import Thread, Lock
from flask import Flask, render_template, jsonify, Response
from flask_cors import CORS
import logging

logger = logging.getLogger(__name__)


class DashboardServer:
    """
    Web-based dashboard for monitoring trades, signals, and P&L.
    Connects to EventBus and streams events to browser in real-time.
    """

    def __init__(self, event_bus, host: str = "127.0.0.1", port: int = 5000):
        self.event_bus = event_bus
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        CORS(self.app)
        self.event_queue = []
        self.queue_lock = Lock()
        self._setup_routes()
        self._subscribe_to_events()

    def _subscribe_to_events(self):
        """Subscribe to all major events."""
        from live.events import EventType

        for event_type in EventType:
            self.event_bus.subscribe(event_type, self._on_event)

    def _on_event(self, event):
        """Buffer event for SSE streaming."""
        with self.queue_lock:
            self.event_queue.append(event.to_dict())

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route("/")
        def index():
            return self._get_html()

        @self.app.route("/api/events")
        def events():
            """Server-Sent Events stream of all events."""
            def event_stream():
                last_sent = 0
                while True:
                    with self.queue_lock:
                        new_events = self.event_queue[last_sent:]
                        if new_events:
                            for event in new_events:
                                yield f"data: {json.dumps(event)}\n\n"
                            last_sent = len(self.event_queue)
                    import time
                    time.sleep(0.1)

            return Response(event_stream(), mimetype="text/event-stream")

        @self.app.route("/api/history")
        def history():
            """Get event history."""
            limit = 100
            history = self.event_bus.get_history(limit=limit)
            return jsonify([e.to_dict() for e in history])

        @self.app.route("/api/trades")
        def trades():
            """Get today's trades."""
            trades = self.event_bus.get_today_trades()
            return jsonify([t.to_dict() for t in trades])

    def _get_html(self) -> str:
        """Return HTML dashboard."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Stock Simulator - Trading Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #0f1419;
            color: #e0e0e0;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            color: #1db954;
            margin-bottom: 20px;
            font-size: 2em;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #333;
        }
        .status {
            display: flex;
            gap: 20px;
            font-size: 0.9em;
        }
        .status-item {
            padding: 10px 15px;
            background: #1a1f26;
            border-radius: 6px;
            border-left: 3px solid #1db954;
        }
        .status-item.warning {
            border-left-color: #ff9500;
        }
        .status-item.error {
            border-left-color: #ff3b30;
        }
        .status-label {
            color: #888;
            font-size: 0.8em;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        .status-value {
            font-size: 1.2em;
            font-weight: bold;
            color: #1db954;
        }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        .panel {
            background: #1a1f26;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 20px;
        }
        .panel h2 {
            color: #1db954;
            font-size: 1.2em;
            margin-bottom: 15px;
            border-bottom: 1px solid #333;
            padding-bottom: 10px;
        }
        .event-log {
            max-height: 400px;
            overflow-y: auto;
        }
        .event {
            padding: 12px;
            margin-bottom: 8px;
            background: #0f1419;
            border-left: 3px solid #1db954;
            border-radius: 4px;
            font-size: 0.9em;
            font-family: 'Monaco', 'Courier New', monospace;
        }
        .event.signal {
            border-left-color: #00bfff;
        }
        .event.trade {
            border-left-color: #ffd700;
        }
        .event.error {
            border-left-color: #ff3b30;
        }
        .event.stop {
            border-left-color: #ff6347;
        }
        .event-time {
            color: #888;
            font-size: 0.8em;
        }
        .event-type {
            color: #1db954;
            font-weight: bold;
            text-transform: uppercase;
            margin-right: 10px;
        }
        .event-data {
            color: #bbb;
            margin-top: 5px;
            padding-left: 10px;
        }
        .trades-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }
        .trades-table th {
            background: #0f1419;
            color: #1db954;
            padding: 10px;
            text-align: left;
            font-weight: bold;
            border-bottom: 2px solid #333;
        }
        .trades-table td {
            padding: 10px;
            border-bottom: 1px solid #333;
        }
        .trades-table tr:hover {
            background: #0f1419;
        }
        .profit {
            color: #00ff00;
            font-weight: bold;
        }
        .loss {
            color: #ff3b30;
            font-weight: bold;
        }
        .pnl-neutral {
            color: #888;
        }
        .connecting {
            color: #ff9500;
        }
        .connected {
            color: #1db954;
        }
        .full-width {
            grid-column: 1 / -1;
        }
        .spinner {
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid #333;
            border-top: 2px solid #1db954;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 8px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .empty {
            color: #888;
            text-align: center;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Stock Simulator</h1>
            <div class="status">
                <div class="status-item">
                    <div class="status-label">Stream Status</div>
                    <div class="status-value">
                        <span class="spinner" id="spinner"></span>
                        <span id="status" class="connecting">Connecting...</span>
                    </div>
                </div>
                <div class="status-item">
                    <div class="status-label">Events</div>
                    <div class="status-value" id="event-count">0</div>
                </div>
            </div>
        </div>

        <div class="grid">
            <div class="panel">
                <h2>🔴 Live Events</h2>
                <div class="event-log" id="event-log">
                    <div class="empty">Waiting for events...</div>
                </div>
            </div>

            <div class="panel">
                <h2>📈 Today's Trades</h2>
                <table class="trades-table" id="trades-table">
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Entry</th>
                            <th>Exit</th>
                            <th>P&L</th>
                            <th>Reason</th>
                        </tr>
                    </thead>
                    <tbody id="trades-tbody">
                        <tr><td colspan="5" class="empty">No trades yet</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let eventCount = 0;
        const eventLog = document.getElementById('event-log');
        const tradesTable = document.getElementById('trades-tbody');

        // Connect to SSE stream
        const eventSource = new EventSource('/api/events');

        eventSource.onopen = () => {
            document.getElementById('status').textContent = 'Connected';
            document.getElementById('status').className = 'connected';
        };

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            addEventToLog(data);
            updateTradesTable();
            eventCount++;
            document.getElementById('event-count').textContent = eventCount;
        };

        eventSource.onerror = () => {
            document.getElementById('status').textContent = 'Disconnected';
            document.getElementById('status').className = 'connecting';
        };

        function addEventToLog(event) {
            // Clear "waiting" message
            if (eventLog.textContent.includes('Waiting')) {
                eventLog.innerHTML = '';
            }

            const eventEl = document.createElement('div');
            const type = event.type.replace(/_/g, ' ').toUpperCase();
            const time = new Date(event.timestamp).toLocaleTimeString();

            // Color by event type
            let eventClass = 'event';
            if (type.includes('SIGNAL')) eventClass += ' signal';
            else if (type.includes('CLOSED') || type.includes('OPENED')) eventClass += ' trade';
            else if (type.includes('STOP')) eventClass += ' stop';
            else if (type.includes('ERROR')) eventClass += ' error';

            eventEl.className = eventClass;
            eventEl.innerHTML = `
                <div>
                    <span class="event-time">[${time}]</span>
                    <span class="event-type">${type}</span>
                </div>
                <div class="event-data">${JSON.stringify(event.data, null, 2)}</div>
            `;

            // Insert at top, keep last 50
            eventLog.insertBefore(eventEl, eventLog.firstChild);
            if (eventLog.children.length > 50) {
                eventLog.removeChild(eventLog.lastChild);
            }
        }

        function updateTradesTable() {
            fetch('/api/trades')
                .then(r => r.json())
                .then(trades => {
                    if (trades.length === 0) {
                        tradesTable.innerHTML = '<tr><td colspan="5" class="empty">No trades today</td></tr>';
                        return;
                    }

                    tradesTable.innerHTML = trades
                        .filter(t => t.type === 'position_closed')
                        .map(t => {
                            const pnl = t.data.pnl;
                            const pnlClass = pnl > 0 ? 'profit' : pnl < 0 ? 'loss' : 'pnl-neutral';
                            const pnlSign = pnl > 0 ? '+' : '';
                            return `
                                <tr>
                                    <td>${t.data.symbol}</td>
                                    <td>$${t.data.entry_price.toFixed(2)}</td>
                                    <td>$${t.data.exit_price.toFixed(2)}</td>
                                    <td class="${pnlClass}">${pnlSign}$${pnl.toFixed(2)} (${(t.data.pnl_pct * 100).toFixed(2)}%)</td>
                                    <td>${t.data.reason}</td>
                                </tr>
                            `;
                        })
                        .join('');
                });
        }

        // Initial load
        updateTradesTable();
    </script>
</body>
</html>
        """

    def run(self, debug: bool = False):
        """Start the dashboard server."""
        logger.info(f"Starting dashboard on {self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=debug)

    def run_async(self):
        """Start dashboard in a background thread."""
        thread = Thread(target=self.run, daemon=True)
        thread.start()
        logger.info(f"Dashboard running at http://{self.host}:{self.port}")
        return thread
