import { useEffect, useState, useRef } from "react";
import * as d3 from "d3";

function App() {
  const [metrics, setMetrics] = useState({ total_accounts: 0, frozen_accounts: 0, blocked_transactions: 0 });
  const [blockedFeed, setBlockedFeed] = useState([]);
  const [serverStatus, setServerStatus] = useState("Connecting...");
  const [selectedNode, setSelectedNode] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const svgRef = useRef(null);
  // Persistent simulation cache keeps react state renders from clobbering D3's memory scope
  const simRef = useRef(null);

  // --- POLLING LOGIC FOR SYSTEM COUNTERS & FRAUD LOGS ---
  useEffect(() => {
    const fetchSystemState = async () => {
      try {
        const metricsRes = await fetch("http://localhost:8001/api/metrics");
        const metricsData = await metricsRes.json();
        
        const feedRes = await fetch("http://localhost:8001/api/blocked-transactions");
        const feedData = await feedRes.json();

        const graphRes = await fetch("http://localhost:8001/api/graph");
        const graphData = await graphRes.json();

        setMetrics({
          total_accounts: graphData.nodes?.length || 0, 
          frozen_accounts: metricsData.frozen_accounts || 0,
          blocked_transactions: metricsData.blocked_transactions || 0
        });
        setBlockedFeed(feedData || []);
        setServerStatus("Online - Ingestion Stream Clear");
      } catch (err) {
        setServerStatus("Offline - Reconnecting...");
      }
    };

    fetchSystemState();
    const pollInterval = setInterval(fetchSystemState, 2000);
    return () => clearInterval(pollInterval);
  }, []);

  // --- D3 FORCE GRAPH DYNAMICS (RUNS ONCE ON MOUNT) ---
  useEffect(() => {
    let intervalId;

    const buildOrUpdateNetworkMatrix = async () => {
      try {
        const response = await fetch("http://localhost:8001/api/graph");
        const data = await response.json();

        if (!data || !data.nodes || data.nodes.length === 0) return;
        if (!svgRef.current) return;

        const width = svgRef.current.parentElement?.clientWidth || 800;
        const height = svgRef.current.parentElement?.clientHeight || 500;

        const svg = d3.select(svgRef.current)
          .attr("width", width)
          .attr("height", height);

        // Keep root container clean but avoid wiping out essential sublayers
        let gContainer = svg.select("g.main-engine");
        if (gContainer.empty()) {
          gContainer = svg.append("g").attr("class", "main-engine");
          svg.call(d3.zoom().on("zoom", (event) => {
            gContainer.attr("transform", event.transform);
          }));
        }

        // Deep-clone incoming arrays to stop React from freezing D3 data mutations
        const nodesData = data.nodes.map(d => ({ ...d }));
        const linksData = (data.links || []).map(d => ({ ...d }));

        // Maintain existing positions across updates to avoid jarring visual jumps
        if (simRef.current) {
          const oldNodes = simRef.current.nodes();
          const nodeMap = new Map(oldNodes.map(n => [n.id, n]));
          nodesData.forEach(node => {
            const match = nodeMap.get(node.id);
            if (match) {
              node.x = match.x;
              node.y = match.y;
              node.vx = match.vx;
              node.vy = match.vy;
            }
          });
        }

        // Halt any existing simulation cycles before starting a new one
        if (simRef.current) simRef.current.stop();

        const simulation = d3.forceSimulation(nodesData)
          .force("link", d3.forceLink(linksData).id((d) => d.id).distance(90))
          .force("charge", d3.forceManyBody().strength(-220))
          .force("center", d3.forceCenter(width / 2, height / 2))
          .force("collision", d3.forceCollide().radius(25));

        simRef.current = simulation;

        // Render target link variables
        const link = gContainer.selectAll("line.tx-link")
          .data(linksData, d => `${d.source.id || d.source}-${d.target.id || d.target}`);
        
        link.exit().remove();
        const linkEnter = link.enter().append("line")
          .attr("class", "tx-link")
          .attr("stroke", "#334155")
          .attr("stroke-width", 2)
          .attr("stroke-opacity", 0.6);
        const allLinks = linkEnter.merge(link);

        // Render live network node variables
        const node = gContainer.selectAll("circle.account-node")
          .data(nodesData, d => d.id);

        node.exit().remove();
        const nodeEnter = node.enter().append("circle")
          .attr("class", "account-node")
          .attr("r", 10)
          .attr("stroke", "#ffffff")
          .attr("stroke-width", 1.5)
          .style("cursor", "pointer")
          .on("click", (event, d) => {
            setSelectedNode(d);
            setIsDrawerOpen(true);
          });

        const allNodes = nodeEnter.merge(node)
          .attr("fill", d => d.status === "BLOCKED" ? "#ef4444" : "#22c55e");

        // Render descriptive text variables
        const label = gContainer.selectAll("text.node-label")
          .data(nodesData, d => d.id);

        label.exit().remove();
        const labelEnter = label.enter().append("text")
          .attr("class", "node-label")
          .attr("font-size", "9px")
          .attr("fill", "#64748b")
          .attr("dx", 14)
          .attr("dy", 3);
        const allLabels = labelEnter.merge(label)
          .text(d => d.id ? (d.id.substring(0, 7) + "..") : "");

        simulation.on("tick", () => {
          allLinks
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

          allNodes
            .attr("cx", d => d.x)
            .attr("cy", d => d.y);

          allLabels
            .attr("x", d => d.x)
            .attr("y", d => d.y);
        });

      } catch (err) {
        console.error("D3 engine update fault:", err);
      }
    };

    buildOrUpdateNetworkMatrix();
    intervalId = setInterval(buildOrUpdateNetworkMatrix, 3000);
    return () => {
      clearInterval(intervalId);
      if (simRef.current) simRef.current.stop();
    };
  }, []);

  return (
    <div style={{ display: "flex", backgroundColor: "#020617", minHeight: "100vh", width: "100vw", color: "#f3f4f6", fontFamily: "monospace", overflow: "hidden" }}>
      
      {/* SIDEBAR NAVIGATION CONTROLS */}
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

      {/* CORE WORKSPACE PIPELINE */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", position: "relative", overflow: "hidden" }}>
        
        {/* COUNTER CARDS REGION */}
        <div style={{ display: "flex", padding: "24px 32px", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid #1e293b", flexShrink: 0 }}>
          <div style={{ display: "flex", gap: "16px" }}>
            <div style={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px", padding: "12px 24px", minWidth: "140px" }}>
              <div style={{ fontSize: "0.7rem", color: "#94a3b8", textTransform: "uppercase" }}>Active Nodes</div>
              <div style={{ fontSize: "1.8rem", fontWeight: "bold", marginTop: "4px" }}>{metrics.total_accounts}</div>
            </div>
            <div style={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px", padding: "12px 24px", minWidth: "140px" }}>
              <div style={{ fontSize: "0.7rem", color: "#94a3b8", textTransform: "uppercase" }}>Frozen Nodes</div>
              <div style={{ fontSize: "1.8rem", fontWeight: "bold", marginTop: "4px" }}>{metrics.frozen_accounts}</div>
            </div>
            <div style={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px", padding: "12px 24px", minWidth: "140px", borderLeft: "3px solid #ef4444" }}>
              <div style={{ fontSize: "0.7rem", color: "#ef4444", textTransform: "uppercase" }}>DLQ Interceptions</div>
              <div style={{ fontSize: "1.8rem", fontWeight: "bold", marginTop: "4px", color: "#ef4444" }}>{metrics.blocked_transactions}</div>
            </div>
          </div>

          <div style={{ backgroundColor: "#0f172a", padding: "8px 16px", borderRadius: "20px", border: "1px solid #1e293b", fontSize: "0.8rem", color: serverStatus.includes("Online") ? "#22c55e" : "#ef4444" }}>
            ● {serverStatus}
          </div>
        </div>

        {/* CENTRAL TOPOLOGY CANVAS */}
        <div style={{ flex: 1, position: "relative", backgroundColor: "#010409", overflow: "hidden" }}>
          {metrics.total_accounts === 0 && (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", zIndex: 2, backgroundColor: "rgba(1,4,9,0.85)" }}>
              <p style={{ color: "#484f58" }}>⏳ Waiting for Kafka real-time fraud data stream vectors...</p>
            </div>
          )}
          <svg ref={svgRef} style={{ width: "100%", height: "100%", display: "block" }} />
        </div>

        {/* SLIDE-DOWN COMPLIANCE DRAWER PANEL */}
        <div style={{ 
          position: "absolute", bottom: 0, left: 0, right: 0,
          height: "240px", backgroundColor: "#0b0f19", borderTop: "2px solid #1e293b",
          transform: isDrawerOpen ? "translateY(0)" : "translateY(100%)",
          transition: "transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
          zIndex: 10, padding: "24px", display: "flex", flexDirection: "column", gap: "16px"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ margin: 0, fontSize: "1rem", color: "#ef4444" }}>🔽 SLIDE-DOWN COMPLIANCE ANALYTICS DRAWER</h3>
            <button onClick={() => setIsDrawerOpen(false)} style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: "1.2rem" }}>✕</button>
          </div>

          {selectedNode ? (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem", textAlign: "left" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #1e293b", color: "#94a3b8" }}>
                  <th style={{ padding: "8px" }}>ACCOUNT ID Target</th>
                  <th style={{ padding: "8px" }}>SYSTEM STATUS</th>
                  <th style={{ padding: "8px" }}>RISK INDEX</th>
                  <th style={{ padding: "8px" }}>VOLUME ASSESSED</th>
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
                  <td style={{ padding: "12px 8px", color: "#f43f5e", fontWeight: "bold" }}>{selectedNode.risk || 92}% Critical Threshold</td>
                  <td style={{ padding: "12px 8px", color: "#10b981" }}>${parseFloat(selectedNode.volume || 4500).toLocaleString()} USD</td>
                </tr>
              </tbody>
            </table>
          ) : (
            <p style={{ color: "#64748b", fontSize: "0.85rem" }}>Select any active network terminal node within the workspace viewport above to track its financial audit attributes.</p>
          )}
        </div>
      </div>

      {/* RIGHT AUDIT LOG STREAM PANELS */}
      {/* RIGHT AUDIT LOG STREAM PANELS */}
      <div style={{ 
        width: "380px", 
        backgroundColor: "#0b0f19", 
        borderLeft: "1px solid #1e293b", 
        padding: "24px", 
        display: "flex", 
        flexDirection: "column", 
        gap: "20px", 
        overflowY: "auto", 
        flexShrink: 0,
        height: "100vh" 
      }}>
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
    </div> // Closing main flex container
  ); // Closing return
} // Closing App function
export default App;