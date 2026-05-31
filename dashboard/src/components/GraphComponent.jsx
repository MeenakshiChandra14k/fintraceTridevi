import { useEffect, useRef } from "react";
import * as d3 from "d3";

const GraphComponent = ({ data, onNodeClick }) => {
  const svgRef = useRef(null);
  const simRef = useRef(null);
  const onNodeClickRef = useRef(onNodeClick);

  useEffect(() => {
    onNodeClickRef.current = onNodeClick;
  }, [onNodeClick]);

  useEffect(() => {
    if (!data.nodes?.length || !svgRef.current) return;

    const container = svgRef.current.parentElement;
    const width = container?.clientWidth || 800;
    const height = container?.clientHeight || 500;

    const svg = d3.select(svgRef.current)
      .attr("viewBox", `0 0 ${width} ${height}`)
      .attr("width", "100%")
      .attr("height", "100%");

    if (simRef.current) {
      simRef.current.nodes(data.nodes);
      simRef.current.force("link").links(data.links);
      simRef.current.alpha(0.1).restart();

      svg.select("g.links").selectAll("line")
        .data(data.links)
        .join("line")
        .attr("stroke", "#475569")
        .attr("stroke-width", 2);

      svg.select("g.nodes").selectAll("g")
        .data(data.nodes, d => d.id)
        .join(enter => {
          const g = enter.append("g")
            .on("click", (e, d) => onNodeClickRef.current(d));
          g.append("circle").attr("r", 8);
          g.append("text")
            .attr("x", 10).attr("y", 3)
            .attr("fill", "#fff").attr("font-size", "10px");
          return g;
        })
        .select("circle")
        .attr("fill", d => d.status === "BLOCKED" ? "#ef4444" : "#22c55e");

      svg.select("g.nodes").selectAll("g").select("text")
        .text(d => d.id);

      return;
    }

    // First mount
    svg.selectAll("*").remove();

    // Zoom container
    const zoomG = svg.append("g").attr("class", "zoom-container");

    svg.call(
      d3.zoom()
        .scaleExtent([0.2, 4])  // min 20% zoom, max 400%
        .on("zoom", (event) => {
          zoomG.attr("transform", event.transform);
        })
    );

    simRef.current = d3.forceSimulation(data.nodes)
      .force("link", d3.forceLink(data.links).id(d => d.id).distance(60))
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .alphaDecay(0.05)
      .alphaMin(0.05);  // ← stops simulation once settled

    const linkG = zoomG.append("g").attr("class", "links");
    const nodeG = zoomG.append("g").attr("class", "nodes");

    linkG.selectAll("line")
      .data(data.links).enter().append("line")
      .attr("stroke", "#475569").attr("stroke-width", 2);

    const node = nodeG.selectAll("g")
      .data(data.nodes, d => d.id).enter().append("g")
      .on("click", (e, d) => onNodeClickRef.current(d));

    node.append("circle").attr("r", 8)
      .attr("fill", d => d.status === "BLOCKED" ? "#ef4444" : "#22c55e");

    node.append("text").text(d => d.id)
      .attr("x", 10).attr("y", 3)
      .attr("fill", "#fff").attr("font-size", "10px");

    simRef.current.on("tick", () => {
      // Clamp nodes within bounds so they can't fly off screen
      // data.nodes.forEach(d => {
      //   d.x = Math.max(20, Math.min(width - 20, d.x));
      //   d.y = Math.max(20, Math.min(height - 20, d.y));
      // });

      linkG.selectAll("line")
        .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
      nodeG.selectAll("g")
        .attr("transform", d => `translate(${d.x},${d.y})`);
    });

    return () => {
      simRef.current?.stop();
      simRef.current = null;
    };
  }, [data]);

  return <svg ref={svgRef} style={{ width: "100%", height: "100%" }} />;
};

export default GraphComponent;