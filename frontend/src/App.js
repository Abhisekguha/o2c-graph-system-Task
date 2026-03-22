import React, { useState, useEffect } from 'react';
import GraphVisualization from './components/GraphVisualization';
import ChatInterface from './components/ChatInterface';
import StatsPanel from './components/StatsPanel';
import Header from './components/Header';
import { apiService } from './services/api';
import './App.css';

function App() {
  const [graphData, setGraphData] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [highlightedNodes, setHighlightedNodes] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [viewMode, setViewMode] = useState('split'); // 'split', 'graph', 'chat'

  useEffect(() => {
    loadGraphData();
  }, []);

  const loadGraphData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [graphResponse, statsResponse] = await Promise.all([
        apiService.getGraphData(),
        apiService.getStats()
      ]);
      
      setGraphData(graphResponse);
      setStats(statsResponse);
      setLoading(false);
    } catch (err) {
      console.error('Failed to load graph data:', err);
      setError('Failed to load graph data. Please make sure the backend server is running.');
      setLoading(false);
    }
  };

  const handleNodeClick = async (node) => {
    setSelectedNode(node);
    try {
      const nodeDetails = await apiService.getNode(node.id);
      setSelectedNode(nodeDetails.node);
    } catch (err) {
      console.error('Failed to load node details:', err);
    }
  };

  const handleQueryResponse = (response) => {
    if (response.highlighted_nodes && response.highlighted_nodes.length > 0) {
      setHighlightedNodes(response.highlighted_nodes);
    }
  };

  if (loading) {
    return (
      <div className="app-loading">
        <div className="loader"></div>
        <p>Loading SAP O2C Graph System...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app-error">
        <div className="error-content">
          <h2>⚠️ Error</h2>
          <p>{error}</p>
          <button onClick={loadGraphData} className="retry-button">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <Header 
        stats={stats} 
        viewMode={viewMode}
        onViewModeChange={setViewMode}
      />
      
      <div className="app-content">
        <div className={`content-layout ${viewMode}`}>
          {(viewMode === 'split' || viewMode === 'graph') && (
            <div className="graph-section">
              <GraphVisualization
                graphData={graphData}
                highlightedNodes={highlightedNodes}
                onNodeClick={handleNodeClick}
                selectedNode={selectedNode}
              />
              {stats && (
                <StatsPanel stats={stats} selectedNode={selectedNode} />
              )}
            </div>
          )}
          
          {(viewMode === 'split' || viewMode === 'chat') && (
            <div className="chat-section">
              <ChatInterface
                onQueryResponse={handleQueryResponse}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
