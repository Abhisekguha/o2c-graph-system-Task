import React from 'react';
import './Header.css';

const Header = ({ stats, viewMode, onViewModeChange }) => {
  return (
    <header className="app-header">
      <div className="header-left">
        <h1 className="app-title">
          <span className="title-icon">📊</span>
          SAP O2C Graph System
        </h1>
        {stats && (
          <div className="header-stats">
            <div className="stat-item">
              <span className="stat-value">{stats.total_nodes?.toLocaleString()}</span>
              <span className="stat-label">Nodes</span>
            </div>
            <div className="stat-divider"></div>
            <div className="stat-item">
              <span className="stat-value">{stats.total_edges?.toLocaleString()}</span>
              <span className="stat-label">Edges</span>
            </div>
          </div>
        )}
      </div>

      <div className="header-right">
        <div className="view-mode-selector">
          <button
            className={`view-mode-btn ${viewMode === 'split' ? 'active' : ''}`}
            onClick={() => onViewModeChange('split')}
            title="Split View"
          >
            ⚡ Split
          </button>
          <button
            className={`view-mode-btn ${viewMode === 'graph' ? 'active' : ''}`}
            onClick={() => onViewModeChange('graph')}
            title="Graph Only"
          >
            🕸️ Graph
          </button>
          <button
            className={`view-mode-btn ${viewMode === 'chat' ? 'active' : ''}`}
            onClick={() => onViewModeChange('chat')}
            title="Chat Only"
          >
            💬 Chat
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
