import { useEffect, useRef, useState } from "react";
import { Maximize2, Minimize2, List, Network } from "lucide-react";
import * as d3 from "d3";

const NODE_COLORS = {
  Paper: "#6c5ce7",
  Gene: "#00d2a0",
  Drug: "#4da6ff",
  Disease: "#ff6b6b",
  Protein: "#ffa94d",
  Pathway: "#ffd43b",
  Author: "#a0a0c0",
  Conclusion: "#a855f7",
};

export default function GraphViewer({ graphData, fullscreen = false, onClose }) {
  const [isFullscreen, setIsFullscreen] = useState(fullscreen);
  const [viewMode, setViewMode] = useState("visual"); // "visual" or "list"

  useEffect(() => {
    setIsFullscreen(fullscreen);
  }, [fullscreen]);

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
    if (onClose && isFullscreen) {
      onClose();
    }
  };

  if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
    return (
      <div className={`graph-container ${isFullscreen ? "fullscreen" : ""}`}>
        <div className="graph-header">
          <span className="graph-title">Knowledge Graph</span>
          <button className="graph-expand-btn" onClick={toggleFullscreen}>
            {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
        </div>
        <div className="graph-empty">No graph data — ingest papers first</div>
      </div>
    );
  }

  return (
    <div className={`graph-container ${isFullscreen ? "fullscreen" : ""}`}>
      <div className="graph-header">
        <span className="graph-title">
          Knowledge Graph ({graphData.total_nodes} nodes, {graphData.total_edges} edges)
        </span>
        <div className="graph-controls">
          <button 
            className={`graph-view-btn ${viewMode === "visual" ? "active" : ""}`}
            onClick={() => setViewMode("visual")}
            title="Visual View"
          >
            <Network size={16} />
          </button>
          <button 
            className={`graph-view-btn ${viewMode === "list" ? "active" : ""}`}
            onClick={() => setViewMode("list")}
            title="List View"
          >
            <List size={16} />
          </button>
          <button className="graph-expand-btn" onClick={toggleFullscreen}>
            {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
        </div>
      </div>
      
      {viewMode === "visual" ? (
        <GraphVisualization graphData={graphData} />
      ) : (
        <GraphListView graphData={graphData} />
      )}
    </div>
  );
}

function GraphVisualization({ graphData }) {
  const svgRef = useRef(null);

  useEffect(() => {
    if (!graphData || !graphData.nodes || graphData.nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = svgRef.current.clientWidth || 600;
    const height = svgRef.current.clientHeight || 400;

    const g = svg.append("g");

    /* Zoom */
    svg.call(
      d3.zoom().scaleExtent([0.3, 4]).on("zoom", (e) => {
        g.attr("transform", e.transform);
      })
    );

    /* Build D3 data */
    const nodeMap = new Map();
    const nodes = [];
    graphData.nodes.forEach((n, i) => {
      const id = n.properties.id || n.properties.name || n.properties.symbol || `n${i}`;
      if (!nodeMap.has(id)) {
        const label = (n.labels && n.labels[0]) || "Unknown";
        const displayName = n.properties.name || n.properties.title || n.properties.symbol || id;
        nodeMap.set(id, { id, label, displayName, ...n.properties });
        nodes.push(nodeMap.get(id));
      }
    });

    const links = graphData.edges
      .map((e) => ({
        source: e.source,
        target: e.target,
        rel: e.rel_type,
      }))
      .filter((l) => nodeMap.has(l.source) && nodeMap.has(l.target));

    /* Simulation */
    const sim = d3
      .forceSimulation(nodes)
      .force("link", d3.forceLink(links).id((d) => d.id).distance(80))
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide(24));

    /* Edges */
    const link = g
      .append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", "var(--border-bright)")
      .attr("stroke-width", 1)
      .attr("stroke-opacity", 0.5);

    /* Edge labels */
    const linkLabel = g
      .append("g")
      .selectAll("text")
      .data(links)
      .join("text")
      .text((d) => d.rel)
      .attr("font-size", 8)
      .attr("fill", "var(--text-muted)")
      .attr("text-anchor", "middle")
      .attr("font-family", "var(--mono)");

    /* Nodes */
    const node = g
      .append("g")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", (d) => (d.label === "Paper" ? 8 : 6))
      .attr("fill", (d) => NODE_COLORS[d.label] || "#6a6a8a")
      .attr("stroke", "var(--bg-primary)")
      .attr("stroke-width", 2)
      .style("cursor", "pointer")
      .call(drag(sim));

    /* Labels */
    const label = g
      .append("g")
      .selectAll("text")
      .data(nodes)
      .join("text")
      .text((d) => truncate(d.displayName, 20))
      .attr("font-size", 10)
      .attr("fill", "var(--text-secondary)")
      .attr("dx", 12)
      .attr("dy", 4)
      .attr("font-family", "var(--font)");

    /* Tooltip on hover */
    node.append("title").text((d) => `${d.label}: ${d.displayName}`);

    sim.on("tick", () => {
      link
        .attr("x1", (d) => d.source.x)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x)
        .attr("y2", (d) => d.target.y);

      linkLabel
        .attr("x", (d) => (d.source.x + d.target.x) / 2)
        .attr("y", (d) => (d.source.y + d.target.y) / 2);

      node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);

      label.attr("x", (d) => d.x).attr("y", (d) => d.y);
    });

    return () => sim.stop();
  }, [graphData]);

  return <svg ref={svgRef} style={{ width: "100%", height: "100%" }} />;
}

function GraphListView({ graphData }) {
  const nodesByLabel = {};
  const edgesByType = {};

  // Group nodes by label
  graphData.nodes.forEach((n) => {
    const label = (n.labels && n.labels[0]) || "Unknown";
    if (!nodesByLabel[label]) {
      nodesByLabel[label] = [];
    }
    const displayName = n.properties.name || n.properties.title || n.properties.symbol || n.properties.id || "Unknown";
    nodesByLabel[label].push({ ...n.properties, displayName });
  });

  // Group edges by type
  graphData.edges.forEach((e) => {
    if (!edgesByType[e.rel_type]) {
      edgesByType[e.rel_type] = [];
    }
    edgesByType[e.rel_type].push(e);
  });

  return (
    <div className="graph-list-view">
      <div className="graph-list-section">
        <h4>Nodes by Type</h4>
        {Object.entries(nodesByLabel).map(([label, items]) => (
          <div key={label} className="graph-list-group">
            <div 
              className="graph-list-group-header"
              style={{ borderLeftColor: NODE_COLORS[label] || "#6a6a8a" }}
            >
              <span 
                className="node-badge"
                style={{ backgroundColor: NODE_COLORS[label] || "#6a6a8a" }}
              >
                {label}
              </span>
              <span className="node-count">{items.length}</span>
            </div>
            <ul className="graph-list-items">
              {items.slice(0, 10).map((item, i) => (
                <li key={i} className="graph-list-item">
                  {item.displayName}
                  {item.year && <span className="item-year">({item.year})</span>}
                </li>
              ))}
              {items.length > 10 && (
                <li className="graph-list-more">+{items.length - 10} more</li>
              )}
            </ul>
          </div>
        ))}
      </div>

      <div className="graph-list-section">
        <h4>Relationships</h4>
        {Object.entries(edgesByType).map(([relType, edges]) => (
          <div key={relType} className="graph-list-group">
            <div className="graph-list-group-header">
              <span className="rel-badge">{relType}</span>
              <span className="node-count">{edges.length}</span>
            </div>
            <ul className="graph-list-items">
              {edges.slice(0, 5).map((edge, i) => (
                <li key={i} className="graph-list-item edge-item">
                  {edge.source} → {edge.target}
                </li>
              ))}
              {edges.length > 5 && (
                <li className="graph-list-more">+{edges.length - 5} more</li>
              )}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

/* Drag behavior */
function drag(simulation) {
  return d3
    .drag()
    .on("start", (e, d) => {
      if (!e.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    })
    .on("drag", (e, d) => {
      d.fx = e.x;
      d.fy = e.y;
    })
    .on("end", (e, d) => {
      if (!e.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    });
}

function truncate(s, n) {
  return s && s.length > n ? s.slice(0, n) + "…" : s;
}
