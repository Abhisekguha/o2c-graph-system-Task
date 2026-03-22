from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class Node(BaseModel):
    id: str
    type: str
    label: str
    properties: Dict[str, Any]

class Edge(BaseModel):
    source: str
    target: str
    type: str
    properties: Optional[Dict[str, Any]] = {}

class GraphData(BaseModel):
    nodes: List[Node]
    edges: List[Edge]

class QueryRequest(BaseModel):
    query: str
    conversation_history: Optional[List[Dict[str, str]]] = []

class QueryResponse(BaseModel):
    answer: str
    query_type: Optional[str] = None
    structured_query: Optional[str] = None
    data: Optional[Any] = None
    highlighted_nodes: Optional[List[str]] = []
