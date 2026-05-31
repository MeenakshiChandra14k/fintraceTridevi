import { useEffect, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import "./App.css";

function App() {

  const [graphData, setGraphData] = useState({
    nodes: [],
    links: []
  });

  const [selectedAccount, setSelectedAccount] = useState(null);

  const [metrics, setMetrics] = useState(null);

  const [blockedFeed, setBlockedFeed] = useState([]);

  const [searchInput, setSearchInput] = useState("");

  const [hoveredNode, setHoveredNode] = useState(null);

  const [alerts, setAlerts] = useState([]);

  const [activeNodes, setActiveNodes] = useState([]);

  const [showAnalytics, setShowAnalytics] = useState(false);

  const searchAccount = async () => {

    if (!searchInput) return;

    try {

      const response = await fetch(
        `http://localhost:8001/search?account_id=${searchInput}`
      );

      const data = await response.json();

      setGraphData((prev) => {

        const existingNodes = new Map(
          prev.nodes.map(n => [n.id, n])
        );

        data.nodes.forEach(node => {
          existingNodes.set(node.id, node);
        });

        const existingLinks = new Map(
          prev.links.map(
            l => [`${l.source}-${l.target}`, l]
          )
        );

        data.links.forEach(link => {
          existingLinks.set(
            `${link.source}-${link.target}`,
            link
          );
        });

        return {
          nodes: Array.from(existingNodes.values()),
          links: Array.from(existingLinks.values())
        };
      });
    } catch (err) {

      console.error(err);
    }
  };

  useEffect(() => {

    const fetchGraph = async () => {

      try {

        const response = await fetch(
          "http://localhost:8001/graph"
        );

        const data = await response.json();

        setGraphData(prev => {

          const existingNodes = new Map(
            prev.nodes.map(n => [n.id, n])
          );

          data.nodes.forEach(node => {
            existingNodes.set(node.id, node);
          });

          const existingLinks = [
            ...prev.links
          ];

          data.links.forEach(link => {

            const exists = existingLinks.some(
              l =>
                l.source === link.source &&
                l.target === link.target
            );

            if (!exists) {
              existingLinks.push(link);
            }
          });

          return {
            nodes: Array.from(existingNodes.values()),
            links: existingLinks
          };
        });
      } catch (err) {

        console.error(err);
      }
    };

    const fetchMetrics = async () => {

      try {

        const response = await fetch(
          "http://localhost:8001/metrics"
        );

        const data = await response.json();

        setMetrics(data);

      } catch (err) {

        console.error(err);
      }
    };

    const fetchBlockedFeed = async () => {

      try {

        const response = await fetch(
          "http://localhost:8001/blocked-transactions"
        );

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

          hotAccounts.push(tx.source);
          hotAccounts.push(tx.target);

        });

        setActiveNodes(hotAccounts);

      } catch (err) {

        console.error(err);
      }
    };

    fetchGraph();
    fetchMetrics();
    fetchBlockedFeed();

    const interval = setInterval(() => {

      fetchGraph();
      fetchMetrics();
      fetchBlockedFeed();

    }, 5000);

    return () => clearInterval(interval);

  }, []);

  return (

    <div className="app-container">

      <div className="sidebar">

        <h1>🛡️ FinTrace SOC</h1>

        <p>Live Fraud Network Monitoring</p>

        <hr />
        <button
          className="analytics-btn"
          onClick={() =>
            setShowAnalytics(!showAnalytics)
          }
        >
          📊 Compliance Analytics
        </button>

        <p>Total Nodes: {graphData.nodes.length}</p>

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

          <button onClick={searchAccount}>
            Search
          </button>

        </div>

        {hoveredNode && (

          <div className="hover-card">

            <h3>🧠 Account Intelligence</h3>

            <p>
              <strong>ID:</strong>
              {hoveredNode.id}
            </p>

            <p>
              <strong>Status:</strong>
              {hoveredNode.status || "SAFE"}
            </p>

            <p>
              <strong>Volume:</strong>
              {hoveredNode.volume || 0}
            </p>

          </div>
        )}

        <div className="alert-stack">

          {alerts.map((alert) => (

            <div
              key={alert.id}
              className="alert-toast"
            >

              <strong>🚨 ALERT</strong>

              <p>{alert.message}</p>

              <small>{alert.reason}</small>

            </div>

          ))}

        </div>
        {showAnalytics && (

          <div className="analytics-panel">

            <h2>📊 Compliance Intelligence</h2>

            <div className="analytics-grid">

              <div className="analytics-card">
                <h3>Suspicious Volume</h3>
                <p>$8.2M</p>
              </div>

              <div className="analytics-card">
                <h3>AML Flags</h3>
                <p>184</p>
              </div>

              <div className="analytics-card">
                <h3>Frozen Accounts</h3>
                <p>{metrics?.frozen_accounts || 0}</p>
              </div>

              <div className="analytics-card">
                <h3>Risk Clusters</h3>
                <p>12</p>
              </div>

            </div>

            <h3 className="risk-title">
              🔥 Top Risk Accounts
            </h3>

            <div className="risk-list">

              {graphData.nodes
                .slice(0, 5)
                .map((node, index) => (

                  <div
                    key={index}
                    className="risk-item"
                  >

                    <span>{node.id}</span>

                    <span>
                      {node.status || "SAFE"}
                    </span>

                  </div>

                ))}

            </div>

          </div>
        )}
        <ForceGraph2D
          graphData={graphData}

          nodeLabel={(node) => `
            Account: ${node.id}
            Risk Score: ${node.risk || 0}
            Status: ${node.status || "ACTIVE"}
            Volume: ${node.volume || 0}
          `}

          nodeColor={(node) => {

            if (node.status === "FROZEN")
              return "#6b7280";

            if (node.status === "HIGH_RISK")
              return "#ef4444";

            if (node.status === "DORMANT")
              return "#8b5cf6";

            return "#22c55e";
          }}

          nodeVal={(node) => {

            return Math.max(
              node.volume / 1000,
              2
            );
          }}

          nodeCanvasObject={(node, ctx, globalScale) => {

            const label = node.id;

            const fontSize = 12 / globalScale;

            ctx.font = `${fontSize}px Sans-Serif`;

            let color = "#22c55e";

            if (node.status === "FROZEN") {
              color = "#6b7280";
            }

            else if (node.risk > 70) {
              color = "#ef4444";
            }

            else if (node.risk > 30) {
              color = "#f59e0b";
            }

            const size = node.volume
              ? Math.max(6, Math.log(node.volume))
              : 8;

            if (
              node.status === "FROZEN" ||
              node.risk > 70
            ) {

              ctx.shadowColor = color;

              ctx.shadowBlur = 25;

            } else {

              ctx.shadowBlur = 0;
            }

            ctx.beginPath();

            ctx.arc(
              node.x,
              node.y,
              size,
              0,
              2 * Math.PI
            );
            const pulse =
              activeNodes.includes(node.id)
                ? Math.sin(Date.now() * 0.005) * 4
                : 0;

            ctx.beginPath();

            ctx.arc(
              node.x,
              node.y,
              size + pulse,
              0,
              2 * Math.PI
            );

            ctx.fillStyle = color;

            ctx.fill();

            ctx.fillStyle = "white";

            ctx.fillText(
              label,
              node.x + 12,
              node.y + 4
            );
          }}

          onNodeClick={async (node) => {

            try {

              const response = await fetch(
                `http://localhost:8001/account/${node.id}`
              );

              const data = await response.json();

              setSelectedAccount(data);

            } catch (err) {

              console.error(err);
            }
          }}

          onNodeHover={(node) => {
            setHoveredNode(node || null);
          }}

          linkDirectionalParticles={2}

          linkDirectionalParticleSpeed={0.005}

          backgroundColor="#020617"
        />

        <div className="metrics-bar">

          <div className="metric-card">
            <h3>Frozen</h3>
            <p>{metrics?.frozen_accounts || 0}</p>
          </div>

          <div className="metric-card">
            <h3>Dormant</h3>
            <p>{metrics?.dormant_accounts || 0}</p>
          </div>

          <div className="metric-card">
            <h3>Total</h3>
            <p>{metrics?.total_accounts || 0}</p>
          </div>

          <div className="metric-card">
            <h3>Blocked</h3>
            <p>{metrics?.blocked_transactions || 0}</p>
          </div>

        </div>

        <div className="blocked-feed">

          <h2>🚨 Blocked Transactions</h2>

          {blockedFeed.map((tx, index) => (

            <div
              key={index}
              className="blocked-card"
            >

              <p>
                <strong>{tx.source}</strong>
                {" → "}
                <strong>{tx.target}</strong>
              </p>

              <p>${tx.amount}</p>

              <small>{tx.reason}</small>

            </div>

          ))}

        </div>

        {selectedAccount && (

          <div className="side-panel">

            <button
              className="close-btn"
              onClick={() => setSelectedAccount(null)}
            >
              ✖
            </button>

            <h2>🕵 Account Intelligence</h2>

            <p>
              <strong>Account:</strong>
              {selectedAccount.account}
            </p>

            <p>
              <strong>Status:</strong>
              {selectedAccount.status || "ACTIVE"}
            </p>

            <p>
              <strong>Risk:</strong>
              {selectedAccount.risk || 0}
            </p>

            <p>
              <strong>Freeze Reason:</strong>
              {selectedAccount.freeze_reason || "None"}
            </p>

            <h3>Outgoing Transfers</h3>

            <ul>

              {selectedAccount.outgoing?.map((tx, index) => (

                <li key={index}>
                  → {tx.target} (${tx.amount})
                </li>

              ))}

            </ul>

          </div>
        )}

      </div>

    </div>
  );
}

export default App;