# SAP Order-to-Cash Graph System

A production-ready graph-based data modeling and natural language query system for SAP Order-to-Cash (O2C) data. This system transforms fragmented business data into an interconnected graph and provides an LLM-powered interface for exploring relationships and querying business flows using natural language.

![System Architecture](https://img.shields.io/badge/Architecture-Graph--Based-blue)
![Backend](https://img.shields.io/badge/Backend-FastAPI-green)
![Frontend](https://img.shields.io/badge/Frontend-React-blue)
![LLM](https://img.shields.io/badge/LLM-Gemini--Pro-yellow)

---

## 🎯 Overview

This system solves a critical problem in enterprise data analysis: **making sense of fragmented, interconnected business data**. It unifies SAP O2C data (orders, deliveries, invoices, payments) into a queryable graph and allows users to explore it naturally through conversation.

### Key Features

✅ **Graph-Based Data Model**: Entities and relationships modeled as nodes and edges  
✅ **Interactive Visualization**: 2D force-directed graph with zoom, pan, and node inspection  
✅ **Natural Language Queries**: Ask questions in plain English, get data-backed answers  
✅ **LLM-Powered Intelligence**: Gemini Pro translates queries to structured operations  
✅ **Query Guardrails**: Restricts queries to dataset domain, rejects off-topic prompts  
✅ **Document Flow Tracing**: Follow complete lifecycle from order to payment  
✅ **Broken Flow Detection**: Identify incomplete processes (e.g., delivered but not billed)  
✅ **Real-time Highlighting**: Nodes referenced in answers are highlighted in the graph  
✅ **Conversational Memory**: Maintains context across multiple queries  

---

## 🏗️ System Architecture

### Tech Stack

**Backend:**
- **FastAPI** - Modern, high-performance Python web framework
- **NetworkX** - Graph construction and analysis
- **Google Gemini Pro** - LLM for natural language understanding
- **Pydantic** - Data validation and serialization

**Frontend:**
- **React 18** - UI framework
- **react-force-graph** - Interactive 2D graph visualization
- **Axios** - HTTP client for API communication
- **Material-UI** - Component library for UI elements

**Database:**
- In-memory graph (NetworkX MultiDiGraph)
- JSONL files as data source

### Architecture Decisions

#### 1. **Graph Database Choice: NetworkX (In-Memory)**

**Why NetworkX:**
- **Fast Development**: Pure Python, no separate database server needed
- **Rich Graph Algorithms**: Built-in support for pathfinding, traversal, analysis
- **Sufficient Scale**: Dataset has ~10K-100K nodes, fits comfortably in memory
- **Simple Deployment**: No database setup, single process deployment

**Trade-offs:**
- ✅ **Pros**: Fast queries, simple architecture, rich Python ecosystem
- ⚠️ **Cons**: Not persistent (reloads on startup), limited scalability beyond ~1M nodes

**Alternative Considered**: Neo4j would be better for persistent storage and datasets >1M nodes, but adds deployment complexity.

#### 2. **LLM Choice: Google Gemini Pro**

**Why Gemini:**
- **Free Tier**: Generous limits (60 RPM) without credit card
- **Strong Reasoning**: Excellent at structured output generation
- **Fast Response**: Low latency for conversational queries
- **Context Window**: 30K tokens sufficient for our prompts

**Prompting Strategy:**
1. **Guardrail Check**: First prompt validates if query is domain-relevant
2. **Context Injection**: Providing graph statistics, entity types, sample IDs
3. **Structured Output**: Requesting specific format (QUERY_TYPE, ANSWER, HIGHLIGHTED_NODES)
4. **Conversation History**: Last 3 exchanges included for context

**Alternative Considered**: OpenAI GPT-4 has better reasoning but requires paid API.

#### 3. **Graph Model Design**

**Node Types:**
- `Customer` - Business partners
- `SalesOrder`, `SalesOrderItem` - Order data
- `Delivery`, `DeliveryItem` - Fulfillment data
- `Invoice` - Billing documents
- `JournalEntry` - Accounting entries
- `Payment` - Payment/clearing documents
- `Product`, `Plant`, `Address` - Supporting entities

**Edge Types:**
- `PLACED` - Customer → SalesOrder
- `HAS_ITEM` - Order/Delivery → Items
- `REFERS_TO` - Item → Product
- `FULFILLED_BY` - Order → Delivery
- `FULFILLS` - Delivery Item → Order Item
- `BILLED_BY` - Delivery → Invoice
- `POSTED_AS` - Invoice → Journal Entry
- `CLEARED_BY` - Journal Entry → Payment 

**Key Design Choice**: MultiDiGraph allows multiple edges between nodes (e.g., multiple line items), critical for business flows.

---

## 📊 Graph Construction Logic

### Entity Identification

```python
# Primary Keys and Foreign Keys (Implicit Relationships)
SalesOrder: salesOrder
DeliveryItem: referenceSdDocument → SalesOrder.salesOrder
Invoice: accountingDocument → JournalEntry.accountingDocument
JournalEntry: clearingAccountingDocument → Payment.accountingDocument
```

### Critical Join Logic

**Sales → Delivery:**
```python
delivery_items.referenceSdDocument = sales_order.salesOrder
delivery_items.referenceSdDocumentItem = sales_order_items.salesOrderItem
```

**Delivery → Billing:**
```python
# Inferred via customer + date proximity (not explicit in this dataset)
# OR via sales order → invoice linkage
```

**Billing → Accounting:**
```python
billing.accountingDocument = journal.accountingDocument
```

**Accounting → Payment:**
```python
journal.clearingAccountingDocument = payment.accountingDocument
```

---

## 🤖 Query Examples

### 1. Aggregation Queries
```
Which products are associated with the highest number of billing documents?
```

### 2. Document Flow Tracing
```
Trace the full flow of billing document 90504248
```
**Expected Output**: Shows Sales Order → Delivery → Invoice → Journal Entry → Payment

### 3. Broken Flow Detection
```
Identify sales orders that have broken or incomplete flows
```
**Expected Output**: Lists orders without deliveries, deliveries without invoices, etc.

### 4. Relationship Queries
```
Show me all deliveries from plant WB05 that haven't been billed
```

### 5. Customer Analysis
```
What customers have the most unpaid invoices?
```

---

## 🛡️ Guardrails Strategy

### Implementation

**Two-Stage Validation:**

1. **LLM-Based Guardrail** (Primary):
   ```python
   def _is_valid_query(query: str) -> bool:
       # Sends prompt to Gemini asking if query is domain-relevant
       # Returns True/False based on "VALID" or "INVALID" response
   ```

2. **Keyword Filtering** (Fallback):
   - Checks for domain-specific terms (sales, delivery, invoice, customer, etc.)
   - Rejects if no relevant keywords found

**Guardrail Prompt:**
```
You are a guardrail system for a SAP O2C data query system.
Determine if this query is relevant to [domain description].
Valid queries ask about: relationships, business flows, data analysis...
Invalid queries include: general knowledge, creative writing, unrelated topics...
Query: "{user_query}"
Respond with ONLY "VALID" or "INVALID".
```

**Rejection Response:**
```
"I can only answer questions related to the SAP Order-to-Cash dataset. 
Please ask about sales orders, deliveries, invoices, payments, customers, or products."
```

---

## 🚀 Installation & Setup

### Prerequisites

- Python 3.9+
- Node.js 16+
- Google Gemini API Key (free at https://ai.google.dev)

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Start the server
python app.py
```

Backend runs on `http://localhost:8000`

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

Frontend runs on `http://localhost:3000`

---

## 📁 Project Structure

```
sap-o2c-graph-system/
├── backend/
│   ├── app.py                 # FastAPI application & API endpoints
│   ├── models.py              # Pydantic models for request/response
│   ├── config.py              # Configuration management
│   ├── data_loader.py         # JSONL file ingestion
│   ├── graph_builder.py       # Graph construction logic
│   ├── query_engine.py        # LLM-powered query processing
│   ├── requirements.txt       # Python dependencies
│   └── .env.example          # Environment configuration template
│
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── components/
│   │   │   ├── GraphVisualization.js  # 2D graph component
│   │   │   ├── ChatInterface.js       # Chat UI
│   │   │   ├── Header.js              # Top bar
│   │   │   └── StatsPanel.js          # Statistics display
│   │   ├── services/
│   │   │   └── api.js                 # API client
│   │   ├── App.js                     # Main application
│   │   └── index.js                   # Entry point
│   ├── package.json
│   └── README.md
│
└── README.md                  # This file
```

---

## 🔌 API Endpoints

### Graph Data
- `GET /api/graph/data` - Full graph (nodes + edges)
- `GET /api/graph/stats` - Graph statistics
- `GET /api/graph/nodes` - Query nodes with filters
- `GET /api/graph/node/{id}` - Get specific node + neighbors

### Query
- `POST /api/query` - Natural language query
  ```json
  {
    "query": "Find all unpaid invoices",
    "conversation_history": []
  }
  ```

### Analysis
- `GET /api/analyze/broken-flows` - Detect incomplete document flows
- `GET /api/trace/{node_id}` - Trace complete flow from a node
- `GET /api/search/nodes?q={query}` - Search nodes by text

---

## 🧪 Testing the System

### 1. Health Check
```bash
curl http://localhost:8000/api/health
```

### 2. Get Graph Stats
```bash
curl http://localhost:8000/api/graph/stats
```

### 3. Query Example
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How many sales orders are there?"}'
```

### 4. Analyze Broken Flows
```bash
curl http://localhost:8000/api/analyze/broken-flows
```

---

## 💡 Sample Queries to Try

**Aggregation:**
- "Which products appear in the most sales orders?"
- "How many invoices are there for customer 320000082?"
- "What is the total value of unpaid invoices?"

**Tracing:**
- "Trace the flow of sales order 740533"
- "Show me the complete journey of invoice 90504248"

**Analysis:**
- "Find sales orders without deliveries"
- "Which deliveries haven't been invoiced?"
- "Show me incomplete payment flows"

**Business Insights:**
- "Which plant has the most deliveries?"
- "What customers have blocked accounts?"

---

## 🎨 UI Features

### Graph Visualization
- **Interactive Navigation**: Zoom, pan, drag nodes
- **Color-Coded Nodes**: Different colors for entity types
- **Relationship Arrows**: Directional edges with labels
- **Highlighting**: Query results highlighted in yellow
- **Node Inspector**: Click nodes to view properties
- **Fit to View**: Auto-zoom to see entire graph

### Chat Interface
- **Natural Language Input**: Plain English queries
- **Streaming Responses**: Real-time answer generation
- **Query Type Badges**: Visual indicators (aggregation, trace, etc.)
- **Conversation History**: Scrollable message log
- **Example Queries**: Quick-start templates
- **Error Handling**: Graceful failure messages

### View Modes
- **Split View**: Graph + Chat side-by-side
- **Graph Only**: Full-screen graph exploration
- **Chat Only**: Focus on conversation

---

## 🔧 Configuration

### Environment Variables

**Backend (.env):**
```bash
GEMINI_API_KEY=your_api_key_here
PORT=8000
DATA_PATH=../../  # Path to dataset root
```

**Frontend (.env):**
```bash
REACT_APP_API_URL=http://localhost:8000
```

### Adjusting Graph Visualization

Edit `GraphVisualization.js`:
```javascript
// Node size
nodeRelSize={6}  // Increase for larger nodes

// Force simulation
cooldownTime={3000}  // Time to stabilize
d3AlphaDecay={0.02}  // Simulation decay rate
d3VelocityDecay={0.3}  // Node movement damping
```

---

## 🐛 Troubleshooting

### Backend Issues

**"Failed to load graph data"**
- Check if dataset files exist in correct path
- Verify DATA_PATH in config.py points to parent directory

**"Invalid API key"**
- Ensure GEMINI_API_KEY is set in .env
- Get free key at https://ai.google.dev

**"Port already in use"**
- Change PORT in .env or kill process on 8000

### Frontend Issues

**"Network Error"**
- Verify backend is running on http://localhost:8000
- Check CORS middleware is enabled in backend

**"Blank screen"**
- Open browser console (F12) for errors
- Ensure all dependencies installed (`npm install`)

---

## 📈 Performance Considerations

### Current Scale
- **Nodes**: ~50K-100K
- **Edges**: ~200K-500K
- **Query Time**: <2s for most queries
- **Graph Load**: ~5-10s on startup

### Optimization Tips

**For Larger Datasets:**
1. Use sampling for visualization (show subset of nodes)
2. Implement pagination for API endpoints
3. Add caching layer (Redis) for frequent queries
4. Consider migrating to Neo4j for persistent storage

**For Faster Queries:**
1. Pre-compute common aggregations
2. Index frequently queried node properties
3. Use streaming responses for long-running queries

---

## 🚢 Deployment

### Docker Deployment (Recommended)

**Dockerfile (Backend):**
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Dockerfile (Frontend):**
```dockerfile
FROM node:16-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
CMD ["npx", "serve", "-s", "build", "-l", "3000"]
```

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ../../:/data
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

---

## 📝 Future Enhancements

**Potential Improvements:**
- [ ] Neo4j integration for persistent storage
- [ ] User authentication & multi-tenancy
- [ ] Query result caching
- [ ] Advanced graph analytics (PageRank, clustering)
- [ ] Export functionality (CSV, JSON, GraphML)
- [ ] Real-time data updates via WebSocket
- [ ] Advanced filtering and faceted search
- [ ] Query history and saved queries

---

## 📄 License

This project is provided as-is for evaluation purposes.

---

## 🙏 Acknowledgments

- **FastAPI** for the excellent web framework
- **React Force Graph** for visualization capabilities
- **Google Gemini** for LLM capabilities
- **NetworkX** for graph algorithms

---

## 📧 Contact

For questions or feedback, please reach out via the submission form.

---

**Built with ❤️ for SAP O2C Data Analysis**
