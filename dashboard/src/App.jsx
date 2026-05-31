import { useEffect, useState, useRef } from "react";
import GraphComponent from "./components/GraphComponent";

function App() {
  const [metrics, setMetrics] = useState({ total_accounts: 0, active_nodes: 0, frozen_accounts: 0, blocked_transactions: 0 });
  const [blockedFeed, setBlockedFeed] = useState([]);
  const [serverStatus, setServerStatus] = useState("Connecting...");
  const [selectedNode, setSelectedNode] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });

  useEffect(() => {
    const fetchSystemState = async () => {
      try {
        const [mRes, fRes, gRes] = await Promise.all([
          fetch("http://localhost:8001/api/metrics"),
          fetch("http://localhost:8001/api/blocked-transactions"),
          fetch("http://localhost:8001/api/graph")
        ]);

        const mData = await mRes.json();
        const fData = await fRes.json();
        const gData = await gRes.json();

        // Only update graph if new nodes have arrived
        setGraphData(prev => {
          const prevIds = new Set(prev.nodes.map(n => n.id));
          const hasNew = (gData.nodes || []).some(n => !prevIds.has(n.id));
          if (!hasNew) return prev;
          return { nodes: gData.nodes || [], links: gData.links || [] };
        });

        setMetrics({
          total_accounts: mData.total_accounts,
          active_nodes: mData.active_nodes,
          frozen_accounts: mData.frozen_accounts,
          blocked_transactions: mData.blocked_transactions
        });

        setBlockedFeed(prev => {
          const newItems = JSON.stringify(fData) !== JSON.stringify(prev);
          return newItems ? fData : prev;
        });

        setServerStatus("Online - Ingestion Stream Clear");
      } catch (err) {
        setServerStatus("Offline - Reconnecting...");
      }
    };

    fetchSystemState();
    const pollInterval = setInterval(fetchSystemState, 2000);
    return () => clearInterval(pollInterval);
  }, []);

  return (
    <div style={{ display: "flex", backgroundColor: "#020617", height: "100vh", width: "100vw", color: "#f3f4f6", fontFamily: "monospace", overflow: "hidden" }}>

      {/* SIDEBAR */}
      <div style={{ width: "260px", backgroundColor: "#0b0f19", borderRight: "1px solid #1e293b", padding: "24px", display: "flex", flexDirection: "column", gap: "24px", flexShrink: 0 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: "bold", fontSize: "1.1rem" }}>
            <span style={{ color: "#ef4444" }}>🛡️</span> FINTRACE SOC
          </div>
          <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "4px" }}>DeepBrain Analysis Node</div>
        </div>

        <button style={{ width: "100%", padding: "12px", backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "6px", color: "#f8fafc", fontWeight: "bold", textAlign: "left" }}>
          📊 Compliance Log
        </button>

        <div style={{ marginTop: "auto", padding: "16px", backgroundColor: "#0f172a", borderRadius: "8px", border: "1px solid #1e293b", fontSize: "0.8rem" }}>
          <div style={{ color: "#94a3b8", marginBottom: "8px", fontWeight: "bold" }}>Network Totals</div>
          <div style={{ display: "flex", justifyContent: "space-between", margin: "4px 0" }}>
            <span style={{ color: "#64748b" }}>Total Nodes:</span>
            <span>{metrics.total_accounts}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", margin: "4px 0" }}>
            <span style={{ color: "#64748b" }}>Total Links:</span>
            <span style={{ color: "#ef4444" }}>{blockedFeed.length}</span>
          </div>
        </div>
      </div>

      {/* CORE WORKSPACE */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", position: "relative", overflow: "hidden", height: "100vh" }}>

        {/* COUNTER CARDS */}
        <div style={{ display: "flex", padding: "24px 32px", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid #1e293b", flexShrink: 0 }}>
          <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
            <div style={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px", padding: "12px 24px", minWidth: "140px" }}>
              <div style={{ fontSize: "0.7rem", color: "#94a3b8", textTransform: "uppercase" }}>Active Nodes</div>
              <div style={{ fontSize: "1.8rem", fontWeight: "bold", marginTop: "4px" }}>{metrics.active_nodes}</div>
            </div>
            <div style={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px", padding: "12px 24px", minWidth: "140px" }}>
              <div style={{ fontSize: "0.7rem", color: "#94a3b8", textTransform: "uppercase" }}>Frozen Nodes</div>
              <div style={{ fontSize: "1.8rem", fontWeight: "bold", marginTop: "4px" }}>{metrics.frozen_accounts}</div>
            </div>
            <div style={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px", padding: "12px 24px", minWidth: "140px", borderLeft: "3px solid #ef4444" }}>
              <div style={{ fontSize: "0.7rem", color: "#ef4444", textTransform: "uppercase" }}>DLQ Interceptions</div>
              <div style={{ fontSize: "1.8rem", fontWeight: "bold", marginTop: "4px", color: "#ef4444" }}>{metrics.blocked_transactions}</div>
            </div>
            <div style={{ backgroundColor: "#0f172a", padding: "8px 16px", borderRadius: "20px", border: "1px solid #1e293b", fontSize: "0.8rem", color: serverStatus.includes("Online") ? "#22c55e" : "#ef4444" }}>
              ● {serverStatus}
            </div>
          </div>
        </div>

        {/* GRAPH CANVAS */}
        <div style={{ flex: 1, position: "relative", backgroundColor: "#010409", overflow: "hidden" }}>
          {metrics.total_accounts === 0 && (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", zIndex: 2, backgroundColor: "rgba(1,4,9,0.85)" }}>
              <p style={{ color: "#484f58" }}>⏳ Waiting for Kafka real-time fraud data stream vectors...</p>
            </div>
          )}
          <GraphComponent
            data={graphData}
            onNodeClick={(d) => {
              setSelectedNode(d);
              setIsDrawerOpen(true);
            }}
          />
        </div>

        {/* COMPLIANCE DRAWER */}
        <div style={{
          position: "absolute", bottom: 0, left: 0, right: 0,
          height: "240px", backgroundColor: "#0b0f19", borderTop: "2px solid #1e293b",
          transform: isDrawerOpen ? "translateY(0)" : "translateY(100%)",
          transition: "transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
          zIndex: 10, padding: "24px", display: "flex", flexDirection: "column", gap: "16px"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ margin: 0, fontSize: "1rem", color: "#ef4444" }}>🔽 COMPLIANCE ANALYTICS</h3>
            <button onClick={() => setIsDrawerOpen(false)} style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: "1.2rem" }}>✕</button>
          </div>

          {selectedNode ? (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem", textAlign: "left" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #1e293b", color: "#94a3b8" }}>
                  <th style={{ padding: "8px" }}>ACCOUNT ID</th>
                  <th style={{ padding: "8px" }}>STATUS</th>
                  <th style={{ padding: "8px" }}>RISK INDEX</th>
                  <th style={{ padding: "8px" }}>VOLUME</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style={{ padding: "12px 8px", fontWeight: "bold", color: "#f8fafc" }}>{selectedNode.id}</td>
                  <td style={{ padding: "12px 8px" }}>
                    <span style={{ padding: "2px 8px", backgroundColor: selectedNode.status === "BLOCKED" ? "#7f1d1d" : "#064e3b", color: selectedNode.status === "BLOCKED" ? "#fca5a5" : "#a7f3d0", borderRadius: "4px" }}>
                      {selectedNode.status}
                    </span>
                  </td>
                  <td style={{ padding: "12px 8px", color: "#f43f5e", fontWeight: "bold" }}>{selectedNode.risk || 92}% Critical</td>
                  <td style={{ padding: "12px 8px", color: "#10b981" }}>${parseFloat(selectedNode.volume || 4500).toLocaleString()} USD</td>
                </tr>
              </tbody>
            </table>
          ) : (
            <p style={{ color: "#64748b", fontSize: "0.85rem" }}>Select a node in the graph to inspect its compliance attributes.</p>
          )}
        </div>

      </div>{/* END CORE WORKSPACE */}

      {/* RIGHT AUDIT PANEL */}
      <div style={{ width: "380px", backgroundColor: "#0b0f19", borderLeft: "1px solid #1e293b", padding: "24px", display: "flex", flexDirection: "column", gap: "20px", overflowY: "auto", flexShrink: 0, height: "100vh" }}>
        <div>
          <h3 style={{ margin: 0, fontSize: "0.95rem" }}>⚠️ Live Compliance DLQ</h3>
          <p style={{ margin: "4px 0 0 0", fontSize: "0.75rem", color: "#64748b" }}>Real-Time Shield Dropped Records</p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {blockedFeed.length === 0 ? (
            <div style={{ border: "1px dashed #1e293b", padding: "40px 20px", borderRadius: "8px", textAlign: "center", color: "#484f58", fontSize: "0.8rem" }}>
              Scanning system vectors... Ingestion pipeline clear.
            </div>
          ) : (
            blockedFeed.map((tx, idx) => (
              <div
                key={idx}
                onClick={() => {
                  setSelectedNode({ id: tx.source, status: "BLOCKED", risk: tx.risk, volume: tx.amount });
                  setIsDrawerOpen(true);
                }}
                style={{ backgroundColor: "#180707", border: "1px solid #7f1d1d", padding: "14px", borderRadius: "8px", fontSize: "0.8rem", cursor: "pointer" }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", fontWeight: "bold", color: "#fca5a5" }}>
                  <span>🚨 SHIELD INTERCEPTION</span>
                  <span style={{ color: "#ef4444" }}>${parseFloat(tx.amount || 0).toLocaleString()}</span>
                </div>
                <div style={{ color: "#e2e8f0", margin: "6px 0", fontSize: "0.75rem" }}>
                  {tx.source} → {tx.target}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

    </div>
  );
}

export default App;