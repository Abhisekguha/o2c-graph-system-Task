import React, { useState } from 'react';
import './StatsPanel.css';

const StatsPanel = ({ stats, selectedNode }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!stats) return null;

  return (
    <div className={`stats-panel ${isExpanded ? 'expanded' : ''}`}>
      <button 
        className="stats-toggle"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? '▼' : '▲'} {isExpanded ? 'Hide' : 'Stats'}
      </button>

      {isExpanded && (
        <div className="stats-content">
          {selectedNode ? (
            <div className="selected-node-info">
              <h3 className="section-title">Selected Node</h3>
              <div className="node-info-grid">
                <div className="info-row">
                  <span className="info-label">ID:</span>
                  <span className="info-value">{selectedNode.id}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Type:</span>
                  <span className="info-value type-badge">{selectedNode.type}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Label:</span>
                  <span className="info-value">{selectedNode.label}</span>
                </div>
                
                {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
                  <div className="properties-section">
                    <h4 className="properties-title">Properties</h4>
                    <div className="properties-list">
                      {Object.entries(selectedNode.properties)
                        .filter(([key, value]) => value !== null && value !== '')
                        .slice(0, 10)
                        .map(([key, value]) => (
                          <div key={key} className="property-row">
                            <span className="property-key">{key}:</span>
                            <span className="property-value">
                              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                            </span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="graph-stats">
              <h3 className="section-title">Graph Statistics</h3>
              
              <div className="stats-grid">
                <div className="stats-card">
                  <div className="stats-card-value">{stats.total_nodes?.toLocaleString()}</div>
                  <div className="stats-card-label">Total Nodes</div>
                </div>
                
                <div className="stats-card">
                  <div className="stats-card-value">{stats.total_edges?.toLocaleString()}</div>
                  <div className="stats-card-label">Total Edges</div>
                </div>
              </div>

              {stats.node_types && (
                <div className="type-breakdown">
                  <h4 className="breakdown-title">Node Types</h4>
                  <div className="type-list">
                    {Object.entries(stats.node_types)
                      .sort((a, b) => b[1] - a[1])
                      .map(([type, count]) => (
                        <div key={type} className="type-item">
                          <span className="type-name">{type}</span>
                          <span className="type-count">{count.toLocaleString()}</span>
                        </div>
                      ))}
                  </div>
                </div>
              )}

              {stats.edge_types && (
                <div className="type-breakdown">
                  <h4 className="breakdown-title">Edge Types</h4>
                  <div className="type-list">
                    {Object.entries(stats.edge_types)
                      .sort((a, b) => b[1] - a[1])
                      .map(([type, count]) => (
                        <div key={type} className="type-item">
                          <span className="type-name">{type}</span>
                          <span className="type-count">{count.toLocaleString()}</span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default StatsPanel;
