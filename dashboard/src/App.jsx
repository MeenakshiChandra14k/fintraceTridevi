import { useEffect, useState, useRef } from "react";
import ForceGraph2D from "react-force-graph-2d";
import "./App.css";

function App() {
  const graphRef = useRef();
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [blockedFeed, setBlockedFeed] = useState([]);
  const [searchInput, setSearchInput] = useState("");
  const [hoveredNode, setHoveredNode] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [activeNodes, setActiveNodes] = useState([]);
  const [showAnalytics, setShowAnalytics] = useState(false);

  // ----------------------------------------------------------------
  // 🔍 1. SEARCH ACCOUNT ROUTE
  // ----------------------------------------------------------------
  const searchAccount = async () => {
    if (!searchInput) return;
    try {
      const response = await fetch(`http://localhost:8001/api/search?account_id=${searchInput}`);
      const data = await response.json();

      setGraphData((prev) => {
        if (graphRef.current) graphRef.current.d3ReheatSimulation();
        
        const existingNodes = new Map(prev.nodes.map(n => [n.id, n]));
        data.nodes?.forEach(node => existingNodes.set(node.id, node));

        const existingLinks = new Map(prev.links.map(l => [`${l.source?.id || l.source}-${l.target?.id || l.target}`, l]));
        data.links?.forEach(link => existingLinks.set(`${link.source}-${link.target}`, link));

        return {
          nodes: Array.from(existingNodes.values()),
          links: Array.from(existingLinks.values())
        };
      });
    } catch (err) {
      console.error("Search error:", err);
    }
  };

  useEffect(() => {
    // ----------------------------------------------------------------
    // 🕸️ 2. LIVE NETWORK GRAPH INGESTION (FIXED LOOP)
    // ----------------------------------------------------------------
    const fetchGraph = async () => {
      try {
        const response = await fetch("http://localhost:8001/api/graph");
        const data = await response.json();

        setGraphData(prev => {
          if (graphRef.current) graphRef.current.d3ReheatSimulation();

          const existingNodes = new Map(prev.nodes.map(n => [n.id, n]));
          data.nodes?.forEach(node => existingNodes.set(node.id, node));

          // Create unique signatures for links to prevent duplication crashes
          const baseLinks = [...prev.links];
          const visibleLinkSignatures = new Set(baseLinks.map(l => 
            `${l.source?.id || l.source}-${l.target?.id || l.target}-${l.amount}`
          ));

          data.links?.forEach(link => {
            const signature = `${link.source}-${link.target}-${link.amount}`;
            if (!visibleLinkSignatures.has(signature)) {
              visibleLinkSignatures.add(signature);
              baseLinks.push(link);
            }
          });

          return {
            nodes: Array.from(existingNodes.values()),
            links: baseLinks
          };
        });
      } catch (err) {
        console.error("Graph synchronization failed:", err);
      }
    };

    // ----------------------------------------------------------------
    // 📊 3. SYSTEM STATE METRICS
    // ----------------------------------------------------------------
    const fetchMetrics = async () => {
      try {
        const response = await fetch("http://localhost:8001/api/metrics");
        const data = await response.json();
        setMetrics(data);
      } catch (err) {
        console.error("Metrics sync failed:", err);
      }
    };

    // ----------------------------------------------------------------
    // 🛑 4. COMPLIANCE DLQ BLOCKED TRANSACTION FEED
    // ----------------------------------------------------------------
    const fetchBlockedFeed = async () => {
      try {
        const response = await fetch("http://localhost:8001/api/blocked-transactions");
        const data = await response.json();
        setBlockedFeed(data);

        const newAlerts = data.map((tx, index) => ({
          id: index,
          message: `${tx.source} → ${tx.target} blocked`,
          reason: tx.reason
        }));
        setAlerts(newAlerts);

        const hotAccounts = [];
        data.forEach((tx) => {
          if (tx.source) hotAccounts.push(tx.source);
          if (tx.target) hotAccounts.push(tx.target);
        });
        setActiveNodes(hotAccounts);
      } catch (err) {
        console.error("Blocked feed layout dropped:", err);
      }
    };

    // Initial boot trigger
    fetchGraph();
    fetchMetrics();
    fetchBlockedFeed();

    // Constant 3-second background heartbeat loop
    const interval = setInterval(() => {
      fetchGraph();
      fetchMetrics();
      fetchBlockedFeed();
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-container">
      <div className="sidebar">
        <h1>🛡️ FinTrace SOC</h1>
        <p>Live Fraud Network Monitoring</p>
        <hr />
        <button className="analytics-btn" onClick={() => setShowAnalytics(!showAnalytics)}>
          {showAnalytics ? "🕸️ View Live Network Map" : "📊 Compliance Analytics"}
        </button>
        <p style={{ marginTop: "20px" }}>Total Nodes: {graphData.nodes.length}</p>
        <p>Total Links: {graphData.links.length}</p>
      </div>

      <div className="graph-panel">
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search Account ID..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          <button onClick={searchAccount}>Search</button>
        </div>

        {hoveredNode && (
          <div className="hover-card">
            <h3>🧠 Account Intelligence</h3>
            <p><strong>ID:</strong> {hoveredNode.id}</p>
            <p><strong>Status:</strong> {hoveredNode.status || "SAFE"}</p>
            <p><strong>Volume:</strong> ${hoveredNode.volume || 0}</p>
          </div>
        )}

        <div className="alert-stack">
          {alerts.slice(-3).map((alert) => (
            <div key={alert.id} className="alert-toast">
              <strong>🚨 INTERCEPTION ALERT</strong>
              <p>{alert.message}</p>
              <small>{alert.reason}</small>
            </div>
          ))}
        </div>

        {showAnalytics && (
          <div className="analytics-panel">
            <h2>📊 Compliance Intelligence Overview</h2>
            <div className="analytics-grid">
              <div className="analytics-card">
                <h3>Secured Pool Assets</h3>
                <p style={{ color: "#22c55e" }}>${metrics?.secured_funds_pool?.toLocaleString() || "0"}</p>
              </div>
              <div className="analytics-card">
                <h3>Lost Interdictions</h3>
                <p style={{ color: "#ef4444" }}>${metrics?.lost_funds_pool?.toLocaleString() || "0"}</p>
              </div>
              <div className="analytics-card">
                <h3>Locked-down Nodes</h3>
                <p>{metrics?.frozen_accounts || 0}</p>
              </div>
              <div className="analytics-card">
                <h3>Total Safe Accounts</h3>
                <p>{metrics?.okay_accounts || 0}</p>
              </div>
            </div>

            <h3 className="risk-title">🔥 Live High-Risk Network Vector</h3>
            <div className="risk-list">
              {graphData.nodes.filter(n => n.status === "FROZEN" || n.risk > 70).slice(0, 5).map((node, index) => (
                <div key={index} className="risk-item">
                  <span>👤 {node.id}</span>
                  <span style={{ color: "#ef4444" }}>{node.status || "HIGH RISK"}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <ForceGraph2D
          ref={graphRef}
          graphData={graphData}
          cooldownTicks={100}
          linkSource="source"
          linkTarget="target"
          nodeLabel={(node) => `Account: ${node.id} | Risk: ${node.risk || 0}%`}
          nodeColor={(node) => {
            if (node.status === "FROZEN") return "#6b7280";
            if (node.risk > 70) return "#ef4444";
            return "#22c55e";
          }}
          nodeVal={(node) => Math.max((node.volume || 2000) / 1000, 4)}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const size = Math.max(5, node.volume ? Math.log(node.volume) * 1.5 : 6);
            let color = "#22c55e";
            if (node.status === "FROZEN") color = "#6b7280";
            else if (node.risk > 70) color = "#ef4444";

            // Glow styling for intercepted accounts
            if (node.status === "FROZEN") {
              ctx.shadowColor = color;
              ctx.shadowBlur = 15;
            } else {
              ctx.shadowBlur = 0;
            }

            // Draw outer target ring for pulse animation
            const pulse = activeNodes.includes(node.id) ? Math.sin(Date.now() * 0.008) * 3 : 0;
            ctx.beginPath();
            ctx.arc(node.x, node.y, size + pulse, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();

            // Label text rendering
            const fontSize = 10 / globalScale;
            ctx.font = `${fontSize}px monospace`;
            ctx.fillStyle = "rgba(255, 255, 255, 0.8)";
            ctx.fillText(node.id, node.x + size + 3, node.y + 3);
          }}
          onNodeClick={async (node) => {
            try {
              const response = await fetch(`http://localhost:8001/api/account/${node.id}`);
              const data = await response.json();
              setSelectedAccount(data);
            } catch (err) {
              console.error(err);
            }
          }}
          onNodeHover={(node) => setHoveredNode(node || null)}
          linkDirectionalParticles={4}
          linkDirectionalParticleSpeed={0.005}
          backgroundColor="#020617"
        />

        <div className="metrics-bar">
          <div className="metric-card"><h3>Frozen Accounts</h3><p>{metrics?.frozen_accounts || 0}</p></div>
          <div className="metric-card"><h3>Active System Nodes</h3><p>{metrics?.total_accounts || 0}</p></div>
          <div className="metric-card"><h3>DLQ Interceptions</h3><p>{metrics?.blocked_transactions || 0}</p></div>
        </div>

        <div className="blocked-feed">
          <h2>🚨 Live Compliance DLQ Core Activity Feed</h2>
          {blockedFeed.length === 0 ? <p style={{color: '#94a3b8'}}>No transaction anomalies intercepted yet.</p> : 
            blockedFeed.map((tx, index) => (
              <div key={index} className="blocked-card">
                <p><strong>{tx.source || tx.nameOrig}</strong> → <strong>{tx.target || tx.nameDest}</strong></p>
                <p style={{color: '#ef4444', fontWeight: 'bold'}}>${tx.amount}</p>
                <small>{tx.reason}</small>
              </div>
            ))
          }
        </div>

        {selectedAccount && (
          <div className="side-panel">
            <button className="close-btn" onClick={() => setSelectedAccount(null)}>✖</button>
            <h2>🕵️ Account Ledger Deep-Dive</h2>
            <p><strong>Account ID:</strong> {selectedAccount.account}</p>
            <p><strong>Status Configuration:</strong> {selectedAccount.status || "ACTIVE"}</p>
            <p><strong>Risk Spectrum Factor:</strong> {selectedAccount.risk || 0}%</p>
            <p><strong>Security Lockdown Trigger:</strong> {selectedAccount.freeze_reason || "None"}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;