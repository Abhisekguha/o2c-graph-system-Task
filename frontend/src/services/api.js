import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class ApiService {
  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  async getHealth() {
    const response = await this.client.get('/api/health');
    return response.data;
  }

  async getGraphData() {
    const response = await this.client.get('/api/graph/data');
    return response.data;
  }

  async getStats() {
    const response = await this.client.get('/api/graph/stats');
    return response.data;
  }

  async getNodes(nodeType = null, limit = 100, offset = 0) {
    const params = { limit, offset };
    if (nodeType) params.node_type = nodeType;
    
    const response = await this.client.get('/api/graph/nodes', { params });
    return response.data;
  }

  async getNode(nodeId) {
    const response = await this.client.get(`/api/graph/node/${nodeId}`);
    return response.data;
  }

  async getEdges(edgeType = null, limit = 100, offset = 0) {
    const params = { limit, offset };
    if (edgeType) params.edge_type = edgeType;
    
    const response = await this.client.get('/api/graph/edges', { params });
    return response.data;
  }

  async query(queryText, conversationHistory = []) {
    const response = await this.client.post('/api/query', {
      query: queryText,
      conversation_history: conversationHistory,
    });
    return response.data;
  }

  async searchNodes(searchQuery, limit = 20) {
    const response = await this.client.get('/api/search/nodes', {
      params: { q: searchQuery, limit },
    });
    return response.data;
  }

  async analyzeBrokenFlows() {
    const response = await this.client.get('/api/analyze/broken-flows');
    return response.data;
  }

  async traceDocument(nodeId) {
    const response = await this.client.get(`/api/trace/${nodeId}`);
    return response.data;
  }
}

export const apiService = new ApiService();
