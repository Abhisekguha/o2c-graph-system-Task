import React, { useRef, useEffect, useState, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import './GraphVisualization.css';

const GraphVisualization = ({ graphData, highlightedNodes, onNodeClick, selectedNode }) => {
  const graphRef = useRef();
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  
  useEffect(() => {
    const updateDimensions = () => {
      const container = document.querySelector('.graph-container');
      if (container) {
        setDimensions({
          width: container.clientWidth,
          height: container.clientHeight,
        });
      }
    };
    
    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  useEffect(() => {
    if (graphRef.current && highlightedNodes.length > 0) {
      // Zoom to highlighted nodes
      const node = graphData?.nodes.find(n => n.id === highlightedNodes[0]);
      if (node) {
        graphRef.current.centerAt(node.x, node.y, 1000);
        graphRef.current.zoom(3, 1000);
      }
    }
  }, [highlightedNodes, graphData]);

  // Prepare graph data - memoized to prevent unnecessary recalculations
  const preparedData = useMemo(() => {
    if (!graphData) return { nodes: [], links: [] };
    
    return {
      nodes: graphData.nodes.map(node => ({
        ...node,
        val: getNodeSize(node.type),
        color: getNodeColor(node.type, highlightedNodes.includes(node.id), selectedNode?.id === node.id),
      })),
      links: graphData.edges.map(edge => ({
        source: edge.source,
        target: edge.target,
        label: edge.label || edge.type,
        color: highlightedNodes.includes(edge.source) || highlightedNodes.includes(edge.target) 
          ? '#ffeb3b' 
          : '#3949ab',
      })),
    };
  }, [graphData, highlightedNodes, selectedNode]);

  const handleNodeClick = (node) => {
    if (onNodeClick) {
      onNodeClick(node);
    }
  };

  if (!graphData) {
    return <div className="graph-loading">Loading graph...</div>;
  }

  return (
    <div className="graph-container">
      <div className="graph-controls">
        <button 
          className="control-btn"
          onClick={() => graphRef.current?.zoomToFit(400)}
        >
          Fit View
        </button>
        <button 
          className="control-btn"
          onClick={() => graphRef.current?.centerAt(0, 0, 1000)}
        >
          Center
        </button>
      </div>
      
      <ForceGraph2D
        ref={graphRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={preparedData}
        nodeLabel={node => `${node.label} (${node.type})`}
        nodeRelSize={8}
        nodeVal={node => node.val}
        nodeColor={node => node.color}
        linkLabel={link => link.label}
        linkColor={link => link.color}
        linkWidth={link => highlightedNodes.includes(link.source.id) || highlightedNodes.includes(link.target.id) ? 3 : 1}
        linkDirectionalArrowLength={3}
        linkDirectionalArrowRelPos={1}
        linkDirectionalParticles={link => highlightedNodes.includes(link.source.id) || highlightedNodes.includes(link.target.id) ? 4 : 0}
        linkDirectionalParticleWidth={2}
        onNodeClick={handleNodeClick}
        enableNodeDrag={true}
        enableZoomInteraction={true}
        enablePanInteraction={true}
        cooldownTime={1000}
        d3AlphaDecay={0.01}
        d3VelocityDecay={0.2}
        linkDistance={80}
        d3Force={{
          charge: { strength: -120 },
          link: { distance: 80 }
        }}
      />
      
      <div className="graph-legend">
        <div className="legend-title">Node Types</div>
        {Object.entries(NODE_TYPE_COLORS).map(([type, color]) => (
          <div key={type} className="legend-item">
            <div className="legend-color" style={{ background: color }}></div>
            <span>{type}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// Helper functions
const NODE_TYPE_COLORS = {
  Customer: '#e91e63',
  SalesOrder: '#2196f3',
  SalesOrderItem: '#64b5f6',
  Delivery: '#ff9800',
  DeliveryItem: '#ffb74d',
  Invoice: '#4caf50',
  InvoiceItem: '#81c784',
  JournalEntry: '#9c27b0',
  Payment: '#00bcd4',
  Product: '#ffeb3b',
  Plant: '#795548',
  Address: '#607d8b',
};

const getNodeColor = (type, isHighlighted, isSelected) => {
  if (isSelected) return '#ff1744';
  if (isHighlighted) return '#ffeb3b';
  return NODE_TYPE_COLORS[type] || '#9e9e9e';
};

const getNodeSize = (type) => {
  const sizes = {
    Customer: 15,
    SalesOrder: 12,
    SalesOrderItem: 6,
    Delivery: 10,
    DeliveryItem: 6,
    Invoice: 12,
    InvoiceItem: 6,
    JournalEntry: 10,
    Payment: 10,
    Product: 8,
    Plant: 8,
    Address: 6,
  };
  return sizes[type] || 8;
};

export default GraphVisualization;
