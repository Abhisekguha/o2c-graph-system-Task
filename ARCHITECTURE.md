# Architecture Document

## System Overview

The SAP O2C Graph System is a full-stack application that transforms fragmented business data into an interconnected graph and provides a natural language interface for exploration.

```
┌─────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                       │
│                      (React Frontend)                       │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────────┐  │
│  │ Graph Viz      │  │ Chat Interface  │  │ Stats Panel  │  │
│  │ (Force Graph)  │  │ (Conversation)  │  │ (Metrics)    │  │
│  └────────────────┘  └─────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/REST API
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       API LAYER                             │
│                     (FastAPI Backend)                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Endpoints:                                            │ │
│  │  • /api/graph/* - Graph operations                     │ │
│  │  • /api/query - NL query processing                    │ │
│  │  • /api/analyze/* - Business analytics                 │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│    Query Engine          │  │    Graph Builder         │
│  (LLM Integration)       │  │  (NetworkX)              │
│                          │  │                          │
│  • Guardrails            │  │  • Node creation         │
│  • Prompt engineering    │  │  • Edge creation         │
│  • Response parsing      │  │  • Relationship mapping  │
│  • Context management    │  │  • Graph algorithms      │
└──────────────────────────┘  └──────────────────────────┘
           │                              │
           │                              │
           ▼                              ▼
┌──────────────────────┐      ┌──────────────────────┐
│   Gemini Pro API     │      │   In-Memory Graph    │
│  (Google AI)         │      │   (NetworkX)         │
└──────────────────────┘      └──────────────────────┘
                                         │
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │   Data Loader        │
                              │   (JSONL Parser)     │
                              └──────────────────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │   JSONL Files        │
                              │   (Dataset)          │
                              └──────────────────────┘
```

---

## Component Breakdown

### 1. Frontend (React)

**Technologies:**
- React 18.2
- react-force-graph (2D visualization)
- Axios (HTTP client)
- Material-UI components

**Components:**

```
src/
├── App.js                    # Main application container
├── components/
│   ├── GraphVisualization.js # Force-directed graph display
│   ├── ChatInterface.js      # Conversational query UI
│   ├── Header.js             # Top navigation bar
│   └── StatsPanel.js         # Statistical information display
└── services/
    └── api.js                # API client (axios wrapper)
```

**State Management:**
- React hooks (useState, useEffect)
- Component-level state
- Props for data flow

**Key Features:**
- Real-time graph rendering
- Node highlighting from query results
- Interactive node inspection
- Responsive layout (split/graph/chat views)
- Message history management

---

### 2. Backend (FastAPI)

**Technologies:**
- FastAPI (web framework)
- NetworkX (graph library)
- Google Gemini Pro (LLM)
- Pydantic (data validation)

**Modules:**

```
backend/
├── app.py              # FastAPI application & routes
├── models.py           # Pydantic data models
├── config.py           # Configuration management
├── data_loader.py      # JSONL file ingestion
├── graph_builder.py    # Graph construction logic
└── query_engine.py     # NL query processing
```

**Architecture Pattern:**
- Layered architecture
- Dependency injection
- Singleton pattern for graph storage
- Request-response cycle

---

## Data Flow

### 1. System Initialization

```
Startup
  └─> DataLoader.load_all_entities()
       └─> Read JSONL files
            └─> Parse JSON objects
                 └─> Return entity dictionaries

  └─> GraphBuilder.build_graph()
       └─> Create nodes from entities
            └─> Create edges from relationships
                 └─> Return NetworkX graph

  └─> QueryEngine.initialize()
       └─> Configure Gemini API
            └─> Load system prompts
```

### 2. Query Processing Flow

```
User Query ("Find sales orders without deliveries")
  │
  ├─> Frontend: ChatInterface
  │    └─> POST /api/query
  │
  ├─> Backend: query_engine.process_query()
  │    │
  │    ├─> Guardrail Check
  │    │    └─> LLM validates domain relevance
  │    │         └─> Returns VALID/INVALID
  │    │
  │    ├─> Context Building
  │    │    └─> Get graph statistics
  │    │    └─> Build conversation history
  │    │    └─> Create system prompt
  │    │
  │    ├─> LLM Query
  │    │    └─> Send prompt to Gemini
  │    │    └─> Receive structured response
  │    │
  │    ├─> Response Parsing
  │    │    └─> Extract answer text
  │    │    └─> Extract query type
  │    │    └─> Extract highlighted nodes
  │    │
  │    └─> Graph Execution (if applicable)
  │         └─> Run graph algorithms
  │         └─> Collect node/edge data
  │
  └─> Frontend: Display Results
       ├─> Show answer in chat
       ├─> Highlight nodes in graph
       └─> Update conversation history
```

### 3. Graph Traversal Flow

```
Node Click (e.g., "SO_740533")
  │
  ├─> Frontend: onNodeClick()
  │    └─> GET /api/graph/node/SO_740533
  │
  ├─> Backend: get_node()
  │    └─> Find node in graph
  │    └─> Get neighbors (predecessors + successors)
  │    └─> Get connecting edges
  │    └─> Return node details
  │
  └─> Frontend: Display
       ├─> Update StatsPanel with properties
       └─> Optionally highlight neighbors
```

---

## Graph Model

### Entity-Relationship Model

```
Customer
  │
  ├─[PLACED]──────────> SalesOrder
  │                        │
  │                        ├─[HAS_ITEM]──> SalesOrderItem
  │                        │                     │
  │                        │                     ├─[REFERS_TO]──> Product
  │                        │                     │
  │                        │                     └─[PRODUCED_AT]──> Plant
  │                        │
  │                        └─[FULFILLED_BY]──> Delivery
  │                                               │
  │                                               └─[HAS_ITEM]──> DeliveryItem
  │                                                                    │
  │                                                                    ├─[FULFILLS]──> SalesOrderItem
  │                                                                    │
  │                                                                    └─[SHIPPED_FROM]──> Plant
  │
  ├─[HAS_ADDRESS]─────> Address
  │
  └─[BILLED_TO]<────── Invoice
                          │
                          └─[POSTED_AS]──> JournalEntry
                                              │
                                              └─[CLEARED_BY]──> Payment
```

### Graph Statistics (Typical Dataset)

```
Nodes:
  Customer:          ~1,000
  SalesOrder:        ~10,000
  SalesOrderItem:    ~50,000
  Delivery:          ~8,000
  DeliveryItem:      ~40,000
  Invoice:           ~7,000
  JournalEntry:      ~6,000
  Payment:           ~5,000
  Product:           ~5,000
  Plant:             ~50
  Address:           ~1,000

Total Nodes: ~133,050

Edges:
  PLACED:            ~10,000
  HAS_ITEM:          ~90,000
  REFERS_TO:         ~50,000
  FULFILLED_BY:      ~8,000
  FULFILLS:          ~40,000
  POSTED_AS:         ~7,000
  CLEARED_BY:        ~5,000
  HAS_ADDRESS:       ~1,000
  Others:            ~5,000

Total Edges: ~216,000
```

---

## API Design

### RESTful Endpoints

**Graph Operations:**
```
GET  /api/graph/data           # Full graph export
GET  /api/graph/stats          # Graph statistics
GET  /api/graph/nodes          # Query nodes (with filters)
GET  /api/graph/node/:id       # Get specific node + neighbors
GET  /api/graph/edges          # Query edges (with filters)
```

**Query Operations:**
```
POST /api/query                # Natural language query
  Body: {
    "query": string,
    "conversation_history": array
  }
  Response: {
    "answer": string,
    "query_type": string,
    "highlighted_nodes": array,
    "data": object
  }
```

**Analysis Operations:**
```
GET  /api/analyze/broken-flows  # Detect incomplete flows
GET  /api/trace/:node_id        # Trace document flow
GET  /api/search/nodes?q=...    # Text search
```

**Utility:**
```
GET  /                          # Root (version info)
GET  /api/health                # Health check
```

---

## LLM Integration Strategy

### Prompt Engineering

**System Prompt Structure:**
```python
{
  "context": {
    "graph_stats": {...},
    "entity_types": [...],
    "relationships": [...],
    "sample_ids": {...}
  },
  "conversation_history": [...],
  "user_query": "...",
  "instructions": "..."
}
```

**Response Format:**
```
QUERY_TYPE: aggregation|trace_flow|broken_flow|relationship|search
ANSWER: Natural language response with data
HIGHLIGHTED_NODES: node_id1,node_id2,...
DATA: Structured data (tables, lists)
```

### Guardrails Implementation

**Two-Layer Approach:**

1. **LLM Verification** (Primary)
   - Sends query to Gemini with domain description
   - Asks for VALID/INVALID classification
   - Requires explicit domain match

2. **Keyword Filtering** (Fallback)
   - Checks for domain-specific terms
   - Rejects obvious off-topic queries
   - Used if LLM check fails

**Rejected Query Response:**
```
"I can only answer questions related to the SAP Order-to-Cash 
dataset. Please ask about sales orders, deliveries, invoices, 
payments, customers, or products."
```

---

## Performance Optimization

### Backend Optimizations

1. **Graph Caching**
   - Graph built once on startup
   - Stored in memory for all requests
   - No rebuild unless data changes

2. **Query Optimization**
   - Early termination for guardrail failures
   - Limit node/edge returns in API
   - Pagination for large result sets

3. **API Response Compression**
   - GZIP compression for large payloads
   - Selective field inclusion

### Frontend Optimizations

1. **Graph Rendering**
   - Virtual rendering for large graphs
   - Lazy loading of node details
   - Debounced search inputs

2. **State Management**
   - Memoization of expensive computations
   - Throttled graph updates
   - Efficient re-rendering

3. **Bundle Optimization**
   - Code splitting
   - Tree shaking
   - Production builds

---

## Security Considerations

### Backend Security

- **API Key Protection**: Environment variables only
- **Input Validation**: Pydantic models
- **CORS Policy**: Configurable origins
- **Rate Limiting**: Can be added with middleware
- **Error Handling**: No sensitive data in errors

### Frontend Security

- **No secrets in code**: API URLs via env vars
- **XSS Prevention**: React's built-in escaping
- **HTTPS Only**: Production deployment
- **Content Security Policy**: Can be configured

---

## Testing Strategy

### Backend Tests

```python
# Unit Tests
- test_data_loader.py
- test_graph_builder.py
- test_query_engine.py

# Integration Tests
- test_api_endpoints.py

# System Tests
- test_system.py (provided)
```

### Frontend Tests

```javascript
// Component Tests
- GraphVisualization.test.js
- ChatInterface.test.js

// Integration Tests
- App.test.js

// E2E Tests
- cypress/integration/query_flow.spec.js
```

---

## Deployment Architecture

### Production Setup

```
                      Internet
                         │
                         ▼
                  ┌──────────────┐
                  │   Nginx      │
                  │  (Reverse    │
                  │   Proxy)     │
                  └──────────────┘
                    │         │
           ┌────────┘         └────────┐
           ▼                           ▼
    ┌─────────────┐          ┌─────────────┐
    │  Frontend   │          │  Backend    │
    │   (React)   │          │  (FastAPI)  │
    │   Port 80   │          │  Port 8000  │
    └─────────────┘          └─────────────┘
                                    │
                                    ▼
                             ┌─────────────┐
                             │  Gemini API │
                             │  (External) │
                             └─────────────┘
```

### Scaling Strategy

**Horizontal Scaling:**
- Multiple backend instances behind load balancer
- Stateless design (graph in shared memory/cache)
- Frontend served via CDN

**Vertical Scaling:**
- Increase instance memory for larger graphs
- More CPU cores for concurrent requests

---

## Monitoring & Observability

### Metrics to Track

**Backend:**
- Request rate (req/s)
- Response time (p50, p95, p99)
- Error rate (%)
- Graph build time (s)
- LLM API latency (s)
- Memory usage (MB)

**Frontend:**
- Page load time (s)
- Time to interactive (s)
- Graph render time (s)
- API call latency (ms)

### Logging Strategy

```python
# Structured logging
{
  "timestamp": "2026-03-22T10:30:00Z",
  "level": "INFO",
  "service": "sap-o2c-backend",
  "message": "Query processed",
  "query_type": "aggregation",
  "response_time_ms": 1234,
  "nodes_highlighted": 5
}
```

---

## Future Enhancements

### Phase 2 Features

1. **Persistent Storage**
   - Migrate to Neo4j
   - Real-time updates
   - Transaction support

2. **Advanced Analytics**
   - PageRank for important entities
   - Community detection
   - Shortest path algorithms

3. **User Management**
   - Authentication (JWT)
   - Role-based access
   - Query history per user

4. **Export Functionality**
   - CSV/Excel exports
   - GraphML format
   - PDF reports

5. **Real-time Collaboration**
   - WebSocket support
   - Shared sessions
   - Live cursors

---

## Technical Debt

### Known Limitations

1. **In-Memory Storage**: Not persistent, requires reload
2. **Single-threaded**: Graph building blocks startup
3. **No Caching**: LLM queries not cached
4. **Limited Error Recovery**: No retry logic
5. **Fixed Dataset**: No real-time ingestion

### Mitigation Plans

- Implement Redis caching layer
- Add background task queue (Celery)
- Migrate to Neo4j for persistence
- Add retry-with-backoff for LLM calls
- Implement webhook-based updates

---

**Document Version:** 1.0  
**Last Updated:** March 22, 2026  
**Author:** SAP O2C Graph System Team
