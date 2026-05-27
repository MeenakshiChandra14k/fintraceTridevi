import React, {
  useEffect,
  useMemo,
  useState,
  useRef,
  Suspense
} from "react";

import {
  Canvas,
  useFrame
} from "@react-three/fiber";

import {
  OrbitControls,
  Text,
  Line
} from "@react-three/drei";

import * as THREE from "three";

import {
  forceSimulation,
  forceManyBody,
  forceLink,
  forceCenter
} from "d3-force";

import "./App.css";


// ==============================
// NODE COMPONENT
// ==============================

function Node({
  position = [0, 0, 0],
  color,
  label,
  risk = 0,
  frozen,
  onClick
}) {

  const [hovered, setHovered] =
    useState(false);

  const meshRef = useRef();

  useFrame(({ clock }) => {

    if (!meshRef.current) return;

    if (risk > 80 || frozen) {

      const pulse =
        Math.sin(
          clock.getElapsedTime() * 2.5
        );

      meshRef.current.scale.setScalar(
        1 + pulse * 0.08
      );

    } else {

      meshRef.current.scale.setScalar(1);
    }
  });

  return (

    <group position={position}>

      {/* NODE */}
      <mesh
        ref={meshRef}
        onClick={onClick}
        onPointerOver={() =>
          setHovered(true)
        }
        onPointerOut={() =>
          setHovered(false)
        }
      >

        <sphereGeometry
          args={[1, 32, 32]}
        />

        <meshStandardMaterial
          color={
            frozen
              ? "#ff2b2b"
              : color
          }

          emissive={
            frozen
              ? "#ff0000"
              : color
          }

          emissiveIntensity={
            frozen
              ? 25
              : risk > 50
                ? 5
                : 1
          }
        />

      </mesh>

      {/* LABEL */}
      <Text
        position={[0, 1.6, 0]}
        fontSize={0.5}
        color="white"
        anchorX="center"
        anchorY="middle"
      >
        {String(label).slice(0, 10)}
      </Text>


      {frozen && (

        <Text
          position={[0, 2.4, 0]}
          fontSize={0.4}
          color="#ff2b2b"
          anchorX="center"
          anchorY="middle"
        >
          🔒 FROZEN
        </Text>

      )}

      {/* TOOLTIP */}
      {hovered && (

        <Text
          position={[0, -1.7, 0]}
          fontSize={0.38}
          color="#00ffff"
          anchorX="center"
          anchorY="middle"
        >
          {`Risk: ${risk}%`}
        </Text>

      )}

    </group>
  );
}


// ==============================
// FLOW PARTICLE
// ==============================

function FlowParticle({
  start,
  end
}) {

  const meshRef = useRef();

  const speed = useMemo(
    () => Math.random() * 1.2 + 0.5,
    []
  );

  const offset = useMemo(
    () => Math.random() * Math.PI * 2,
    []
  );

  const startVec = useMemo(
    () => new THREE.Vector3(...start),
    [start]
  );

  const endVec = useMemo(
    () => new THREE.Vector3(...end),
    [end]
  );

  useFrame(({ clock }) => {

    if (!meshRef.current) return;

    const time =
      clock.getElapsedTime();

    const t =
      (
        Math.sin(
          time * speed + offset
        ) + 1
      ) / 2;

    meshRef.current.position.lerpVectors(
      startVec,
      endVec,
      t
    );
  });

  return (

    <mesh ref={meshRef}>

      <sphereGeometry
        args={[0.18, 12, 12]}
      />

      <meshStandardMaterial
        color="#ffd000"
        emissive="#ff9900"
        emissiveIntensity={8}
      />

    </mesh>
  );
}


// ==============================
// MAIN APP
// ==============================

function App() {

  const [graph, setGraph] =
    useState({
      nodes: [],
      links: []
    });

  const [selectedNode,
    setSelectedNode] =
    useState(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState(null);


  const [searchTerm, setSearchTerm] =
    useState("");

  // ==============================
  // FETCH GRAPH
  // ==============================

  useEffect(() => {

    const fetchGraph = () => {

      fetch(
        "http://127.0.0.1:9000/graph"
      )

        .then((res) => {

          if (!res.ok) {

            throw new Error(
              "Failed to fetch graph"
            );
          }

          return res.json();
        })

        .then((data) => {

          console.log(
            "GRAPH LOADED:",
            data
          );

          setGraph(data);

          setLoading(false);
        })

        .catch((err) => {

          console.error(err);

          setError(
            "Backend connection failed"
          );

          setLoading(false);
        });
    };

    // Initial fetch
    fetchGraph();

    // Auto refresh every 5 seconds
    const interval =
      setInterval(fetchGraph, 5000);

    return () =>
      clearInterval(interval);

  }, []);


  // ==============================
  // FORCE LAYOUT
  // ==============================

  const nodePositions = useMemo(() => {

    const positions = {};

    if (!graph.nodes.length) {
      return positions;
    }

    const simNodes =
      graph.nodes.map((n) => ({
        ...n
      }));

    const simLinks =
      graph.links.map((l) => ({
        source: l.source,
        target: l.target
      }));


    const simulation =
      forceSimulation(simNodes)

        .force(
          "charge",

          forceManyBody()
            .strength(-100)
        )

        .force(
          "link",

          forceLink(simLinks)

            .id((d) => d.id)

            .distance(60)
        )

        .force(
          "center",

          forceCenter(0, 0)
        )

        .stop();


    // RUN SIMULATION
    for (let i = 0; i < 300; i++) {

      simulation.tick();
    }


    // FIND GRAPH CENTER
    const avgX =
      simNodes.reduce(
        (sum, node) =>
          sum + (node.x || 0),
        0
      ) / simNodes.length;

    const avgY =
      simNodes.reduce(
        (sum, node) =>
          sum + (node.y || 0),
        0
      ) / simNodes.length;


    // SAVE CENTERED POSITIONS
    simNodes.forEach((node) => {

      positions[node.id] = [

        ((node.x || 0) - avgX) * 0.08,

        ((node.y || 0) - avgY) * 0.08,

        0
      ];
    });

    return positions;

  }, [graph]);


  return (

    <div className="app">

      {/* HEADER */}
      <div className="hud-top">

        <div className="brand">

          🧠 FinTrace DeepBrain

        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "15px"
          }}
        >

          <div className="status">

            {
              loading
                ? "SYNCING GRAPH..."
                : "LIVE FRAUD MESH ACTIVE"
            }

          </div>

          <input
            type="text"
            placeholder="Search Account ID..."
            value={searchTerm}
            onChange={(e) =>
              setSearchTerm(e.target.value)
            }
            style={{
              padding: "10px",
              borderRadius: "8px",
              border: "1px solid #333",
              outline: "none",
              background: "#111827",
              color: "white",
              width: "220px"
            }}
          />

        </div>

      </div>


      {/* ERROR */}
      {error && (

        <div className="error-box">

          ❌ {error}

        </div>
      )}


      {/* LOADING */}
      {loading && (

        <div className="loading-overlay">

          <div className="loader-card">

            <div className="spinner" />

            <p>
              Analyzing transaction graph...
            </p>

          </div>

        </div>
      )}


      {/* DASHBOARD */}
      <div className="dashboard">

        <div className="card">
          <h3>Total Accounts</h3>
          <p>{graph.nodes.length}</p>
        </div>

        <div className="card">
          <h3>Total Transfers</h3>
          <p>{graph.links.length}</p>
        </div>

        <div className="card">
          <h3>High Risk</h3>
          <p>
            {
              graph.nodes.filter(
                n => (n.risk || 0) > 80
              ).length
            }
          </p>
        </div>

      </div>



      {/* CANVAS */}
      <Canvas

        camera={{
          position: [0, 0, 20],
          fov: 75
        }}

        style={{
          width: "100vw",
          height: "100vh",
          background: "#050816"
        }}
      >

        <Suspense fallback={null}>

          {/* LIGHTS */}
          <ambientLight intensity={2} />

          <pointLight
            position={[0, 0, 50]}
            intensity={120}
          />


          {/* CONTROLS */}
          <OrbitControls
            enablePan
            enableZoom
            enableRotate
          />


          {/* LINKS */}
          {graph.links.map((link, i) => {

            const source =
              nodePositions[link.source];

            const target =
              nodePositions[link.target];

            if (!source || !target)
              return null;

            return (

              <Line
                key={i}

                points={[
                  source,
                  target
                ]}

                color="#3ad7ff"

                lineWidth={1.5}
              />

            );
          })}


          {/* FLOW PARTICLES */}
          {graph.links
            .slice(0, 40)
            .map((link, i) => {

              const source =
                nodePositions[link.source];

              const target =
                nodePositions[link.target];

              if (!source || !target)
                return null;

              return (

                <FlowParticle
                  key={`flow-${i}`}
                  start={source}
                  end={target}
                />

              );
            })}


          {/* NODES */}
          {graph.nodes
            .filter((node) =>
              node.id
                .toLowerCase()
                .includes(
                  searchTerm.toLowerCase()
                )
            )
            .map((node) => {
              const pos =
                nodePositions[node.id];

              if (!pos) return null;

              const risk =
                node.risk || 0;

              return (

                <Node
                  key={node.id}

                  position={pos}

                  color={
                    risk >= 70
                      ? "#ff2b2b"
                      : risk >= 40
                        ? "#ffd000"
                        : "#00ff88"
                  }

                  label={node.id}

                  risk={risk}

                  frozen={risk > 80}

                  onClick={() =>
                    setSelectedNode(node)
                  }
                />

              );
            })}

        </Suspense>

      </Canvas>


      {/* SIDEBAR */}
      {selectedNode && (

        <div className="sidebar">

          <div className="sidebar-header">

            <h2>
              🕵 Investigation Panel
            </h2>

          </div>

          <div className="sidebar-body">

            <p>

              <b>Account</b>

              <br />

              {selectedNode.id}

            </p>

            <p>

              <b>Risk Score</b>

              <br />

              {selectedNode.risk || 0}%

            </p>

            <p>

              <b>Status</b>

              <br />

              {
                (selectedNode.risk || 0) > 80
                  ? "🔒 Frozen"
                  : "✅ Active"
              }

            </p>

            {(selectedNode.risk || 0) > 80 && (

              <p>

                <b>Freeze Reason</b>

                <br />

                Mule Account / Layering Activity

              </p>

            )}

          </div>

          <button
            className="close-btn"

            onClick={() =>
              setSelectedNode(null)
            }
          >
            Close Panel
          </button>

        </div>
      )}

    </div>
  );
}

export default App;