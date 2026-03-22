import google.generativeai as genai
from typing import Dict, List, Any, Optional
import json
import networkx as nx
from config import config

class QueryEngine:
    """LLM-powered natural language query engine with guardrails"""
    
    def __init__(self, graph: nx.MultiDiGraph, entities: Dict[str, List[Dict]]):
        self.graph = graph
        self.entities = entities
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
    def process_query(self, query: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Process natural language query and return structured response"""
        
        # Step 1: Try keyword shortcuts (fast path for common queries)
        graph_result = self._try_graph_query(query)
        
        if graph_result:
            # Graph query succeeded - enhance the raw data with Gemini for a presentable answer
            enhanced = self._enhance_with_llm(query, graph_result)
            return enhanced
        
        # Step 2: Use LLM to generate graph query plan (universal graph queries)
        query_plan = self._generate_graph_query_plan(query)
        
        if query_plan:
            # Execute the graph plan
            graph_result = self._execute_graph_plan(query_plan)
            
            # Format with LLM
            formatted = self._format_graph_result(query, graph_result)
            return formatted
        
        # Step 3: Check guardrails for non-queryable requests
        if not self._is_valid_query(query):
            return {
                'answer': "This system is designed to answer questions related to the provided dataset only.",
                'query_type': 'invalid',
                'data': None,
                'highlighted_nodes': []
            }
        
        # Step 4: Fallback - LLM explanation only (no graph data)
        llm_response = self._generate_response(query, conversation_history)
        
        return llm_response
    
    def _enhance_with_llm(self, original_query: str, graph_result: Dict) -> Dict:
        """Enhance raw graph query results with Gemini for a polished, presentable response"""
        raw_data = graph_result.get('data', '') or graph_result.get('answer', '')
        query_type = graph_result.get('query_type', 'general')
        
        enhance_prompt = f"""You are a SAP Order-to-Cash business analyst presenting findings to a stakeholder.

The user asked: "{original_query}"

Here is the raw data retrieved from the SAP O2C graph database:

{raw_data}

Your task:
1. Present this data in a clear, professional, and well-structured response.
2. Use bullet points, numbered lists, or tables where appropriate.
3. Add brief business context or insights (e.g., "This could indicate...", "This is typical when...").
4. Highlight key findings or anomalies.
5. Keep it concise but informative — no more than 300 words.
6. Do NOT invent or hallucinate any data — only use what is provided above.
7. Use markdown formatting for readability.

Respond ONLY with the formatted answer. Do not include any preamble like "Here is..." or "Based on the data..."."""

        try:
            response = self.model.generate_content(enhance_prompt)
            enhanced_answer = response.text.strip()
            
            return {
                'answer': enhanced_answer,
                'query_type': query_type,
                'data': graph_result.get('data'),
                'highlighted_nodes': graph_result.get('highlighted_nodes', [])
            }
        except Exception as e:
            print(f"LLM enhancement failed, returning raw result: {e}")
            # Fallback to raw graph result if LLM fails
            return graph_result
    
    def _generate_graph_query_plan(self, query: str) -> Optional[Dict]:
        """Use LLM to generate a graph traversal plan from natural language"""
        
        # Get sample of actual node properties from the graph
        node_schema = self._get_node_property_schema()
        
        planner_prompt = f"""You are a graph database query planner for a SAP Order-to-Cash system.

=== AVAILABLE NODE TYPES AND PROPERTIES ===
{json.dumps(node_schema, indent=2)}

=== GRAPH RELATIONSHIPS ===
- Customer →[PLACED]→ SalesOrder
- SalesOrder →[HAS_ITEM]→ SalesOrderItem
- SalesOrder →[FULFILLED_BY]→ Delivery
- Delivery →[HAS_ITEM]→ DeliveryItem
- Invoice →[HAS_ITEM]→ InvoiceItem
- Invoice →[BILLED_TO]→ Customer
- InvoiceItem →[BILLS]→ Delivery
- InvoiceItem →[REFERS_TO]→ Product
- Invoice →[POSTED_AS]→ JournalEntry
- JournalEntry →[CLEARED_BY]→ Payment

=== USER QUERY ===
"{query}"

=== YOUR TASK ===
Generate a structured graph traversal plan in JSON format. If the query cannot be answered from the graph, set queryable to false.

Response format:
{{
  "queryable": true/false,
  "start_node_type": "NodeType",
  "filters": {{"propertyName": {{"operator": "==|contains|>|<|month_year", "value": "..."}}}},
  "traversal_path": ["→EDGE→NodeType", "←EDGE←NodeType"],
  "aggregation": {{"operation": "count|sum|avg|min|max", "property": "propertyName"}},
  "return_properties": ["prop1", "prop2"],
  "limit": 10
}}

Example 1: "How many invoices for customer CUST_320000082?"
{{
  "queryable": true,
  "start_node_type": "Customer",
  "filters": {{"id": {{"operator": "==", "value": "CUST_320000082"}}}},
  "traversal_path": ["←BILLED_TO←Invoice"],
  "aggregation": {{"operation": "count", "property": null}},
  "return_properties": ["label", "totalNetAmount"],
  "limit": null
}}

Example 2: "Average invoice amount in April 2025"
{{
  "queryable": true,
  "start_node_type": "Invoice",
  "filters": {{"creationDate": {{"operator": "month_year", "value": "2025-04"}}}},
  "traversal_path": [],
  "aggregation": {{"operation": "avg", "property": "totalNetAmount"}},
  "return_properties": ["totalNetAmount", "creationDate"],
  "limit": null
}}

Respond with ONLY the JSON plan, no explanation."""

        try:
            response = self.model.generate_content(planner_prompt)
            plan_text = response.text.strip()
            # Remove markdown code blocks if present
            if plan_text.startswith('```'):
                plan_text = plan_text.split('```')[1].replace('json', '').strip()
            plan = json.loads(plan_text)
            return plan if plan.get('queryable') else None
        except Exception as e:
            print(f"Query planning failed: {e}")
            return None
    
    def _execute_graph_plan(self, plan: Dict) -> Dict:
        """Execute a graph traversal plan generated by LLM"""
        from datetime import datetime
        
        # Step 1: Find starting nodes
        start_nodes = []
        node_type = plan.get('start_node_type')
        
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            if node_data.get('type') != node_type:
                continue
            
            # Apply filters
            matches = True
            for prop, condition in plan.get('filters', {}).items():
                operator = condition.get('operator', '==')
                value = condition.get('value')
                node_value = node_data.get(prop) if prop != 'id' else node_id
                
                if operator == '==':
                    if str(node_value).upper() != str(value).upper():
                        matches = False
                elif operator == 'contains':
                    if value.lower() not in str(node_value).lower():
                        matches = False
                elif operator == '>':
                    try:
                        if not (node_value and float(node_value) > float(value)):
                            matches = False
                    except:
                        matches = False
                elif operator == '<':
                    try:
                        if not (node_value and float(node_value) < float(value)):
                            matches = False
                    except:
                        matches = False
                elif operator == 'month_year':
                    try:
                        dt = datetime.fromisoformat(str(node_value).replace('Z', '+00:00'))
                        target = datetime.fromisoformat(value + '-01T00:00:00')
                        if dt.year != target.year or dt.month != target.month:
                            matches = False
                    except:
                        matches = False
            
            if matches:
                start_nodes.append(node_id)
        
        # Step 2: Traverse from starting nodes
        result_nodes = set(start_nodes)
        for path_spec in plan.get('traversal_path', []):
            # Parse: "→EDGE→NodeType" or "←EDGE←NodeType"
            if '→' in path_spec:
                direction = 'forward'
                parts = path_spec.split('→')
                edge_type = parts[1] if len(parts) > 1 else None
                target_type = parts[2] if len(parts) > 2 else None
            else:
                direction = 'backward'
                parts = path_spec.split('←')
                edge_type = parts[1] if len(parts) > 1 else None
                target_type = parts[2] if len(parts) > 2 else None
            
            new_results = set()
            for node in result_nodes:
                neighbors = (self.graph.successors(node) if direction == 'forward' 
                            else self.graph.predecessors(node))
                
                for neighbor in neighbors:
                    # Check edge type
                    edges = self.graph.get_edge_data(node, neighbor) if direction == 'forward' else self.graph.get_edge_data(neighbor, node)
                    if edges:
                        edge_matches = any(e.get('type') == edge_type for e in edges.values()) if edge_type else True
                        if edge_matches:
                            # Check target node type
                            neighbor_type = self.graph.nodes[neighbor].get('type')
                            if not target_type or neighbor_type == target_type:
                                new_results.add(neighbor)
            
            result_nodes = new_results
        
        # Step 3: Aggregate or collect properties
        agg_spec = plan.get('aggregation')
        return_props = plan.get('return_properties', [])
        
        if agg_spec:
            operation = agg_spec.get('operation')
            prop = agg_spec.get('property')
            
            values = []
            for node in result_nodes:
                if prop:
                    val = self.graph.nodes[node].get(prop)
                    if val is not None:
                        try:
                            values.append(float(val))
                        except:
                            pass
            
            if operation == 'count':
                result = len(result_nodes)
            elif operation == 'sum':
                result = sum(values)
            elif operation == 'avg':
                result = sum(values) / len(values) if values else 0
            elif operation == 'min':
                result = min(values) if values else 0
            elif operation == 'max':
                result = max(values) if values else 0
            else:
                result = len(result_nodes)
            
            return {
                'aggregation': {operation: result},
                'count': len(result_nodes),
                'nodes': list(result_nodes)[:10],
                'values': values[:10] if prop else []
            }
        else:
            # Return list of nodes with properties
            results = []
            limit = plan.get('limit', 10) or 10
            for node in list(result_nodes)[:limit]:
                node_result = {'id': node, 'label': self.graph.nodes[node].get('label', node)}
                for prop in return_props:
                    node_result[prop] = self.graph.nodes[node].get(prop)
                results.append(node_result)
            
            return {
                'nodes': results,
                'count': len(result_nodes)
            }
    
    def _format_graph_result(self, query: str, graph_result: Dict) -> Dict:
        """Format graph traversal results using LLM"""
        
        result_summary = json.dumps(graph_result, indent=2, default=str)
        
        format_prompt = f"""You are a SAP Order-to-Cash business analyst presenting findings to a stakeholder.

The user asked: "{query}"

Here is the raw data retrieved from the graph database:

{result_summary}

Your task:
1. Present this data in a clear, professional, and well-structured response.
2. Use bullet points, numbered lists, or tables where appropriate.
3. Add brief business context or insights (e.g., "This could indicate...", "This is typical when...").
4. Highlight key findings or anomalies.
5. Keep it concise but informative — no more than 300 words.
6. Do NOT invent or hallucinate any data — only use what is provided above.
7. Use markdown formatting for readability.

Respond ONLY with the formatted answer. Do not include any preamble like "Here is..." or "Based on the data..."."""

        try:
            response = self.model.generate_content(format_prompt)
            formatted_answer = response.text.strip()
            
            return {
                'answer': formatted_answer,
                'query_type': 'aggregation' if 'aggregation' in graph_result else 'search',
                'data': result_summary,
                'highlighted_nodes': graph_result.get('nodes', [])[:10]
            }
        except Exception as e:
            print(f"Result formatting failed: {e}")
            # Fallback to raw display
            count = graph_result.get('count', 0)
            agg = graph_result.get('aggregation', {})
            if agg:
                operation = list(agg.keys())[0]
                value = agg[operation]
                answer = f"Query result: {operation} = {value}, total records: {count}"
            else:
                answer = f"Found {count} matching records."
            
            return {
                'answer': answer,
                'query_type': 'aggregation' if agg else 'search',
                'data': result_summary,
                'highlighted_nodes': graph_result.get('nodes', [])[:10]
            }
    
    def _get_node_property_schema(self) -> Dict:
        """Get actual node properties from graph for LLM context"""
        schema = {}
        
        # Sample nodes of each type to discover properties
        sampled_types = set()
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            node_type = node_data.get('type', 'Unknown')
            
            # Sample up to 1 node per type
            if node_type not in sampled_types:
                sampled_types.add(node_type)
                
                properties = {}
                for prop, value in node_data.items():
                    if prop not in ['type']:
                        properties[prop] = {
                            'example': str(value)[:50] if value else 'null',
                            'type': type(value).__name__
                        }
                
                schema[node_type] = {
                    'sample_id': node_id,
                    'properties': properties
                }
            
            # Stop after sampling all types or 20 types
            if len(sampled_types) >= 20:
                break
        
        return schema
    
    def _try_graph_query(self, query: str) -> Optional[Dict]:
        """Try to execute a graph query based on keyword detection. Returns None if no match."""
        query_lower = query.lower()
        
        try:
            # Broken/incomplete flow detection
            if 'broken' in query_lower or 'incomplete' in query_lower:
                result = self._execute_broken_flow_query()
                if result:
                    return {
                        'answer': f"Here are the broken/incomplete flows detected in the SAP O2C data:\n\n{result['results']}",
                        'query_type': 'broken_flow',
                        'data': result['results'],
                        'highlighted_nodes': []
                    }
            
            # Product-billing aggregation
            elif 'product' in query_lower and ('billing' in query_lower or 'invoice' in query_lower):
                result = self._execute_product_billing_query()
                if result:
                    return {
                        'answer': result.get('answer', ''),
                        'query_type': 'aggregation',
                        'data': result.get('results', ''),
                        'highlighted_nodes': result.get('highlighted_nodes', [])
                    }
            
            # Trace flow
            elif 'trace' in query_lower or ('flow' in query_lower and 'billing' in query_lower):
                result = self._execute_trace_query(query)
                if result:
                    return {
                        'answer': f"Here is the complete document flow trace:\n\n{result['path']}",
                        'query_type': 'trace_flow',
                        'data': result['path'],
                        'highlighted_nodes': result.get('nodes', [])
                    }
            
            # Customer query
            elif 'customer' in query_lower and ('most' in query_lower or 'sales order' in query_lower):
                result = self._execute_customer_orders_query()
                if result:
                    return {
                        'answer': result.get('answer', ''),
                        'query_type': 'aggregation',
                        'data': result.get('results', ''),
                        'highlighted_nodes': result.get('highlighted_nodes', [])
                    }
            
            # Deliveries not billed
            elif 'deliver' in query_lower and ('not' in query_lower or "haven't" in query_lower or "not billed" in query_lower):
                result = self._execute_unbilled_deliveries_query()
                if result:
                    return {
                        'answer': f"Here are the deliveries that haven't been billed:\n\n{result['results']}",
                        'query_type': 'broken_flow',
                        'data': result['results'],
                        'highlighted_nodes': result.get('highlighted_nodes', [])
                    }
            
            # Customer invoice amount query
            elif 'customer' in query_lower and ('billed' in query_lower or 'invoice' in query_lower or 'amount' in query_lower or 'total' in query_lower):
                result = self._execute_customer_invoice_query(query)
                if result:
                    return {
                        'answer': result.get('answer', ''),
                        'query_type': 'aggregation',
                        'data': result.get('results', ''),
                        'highlighted_nodes': result.get('highlighted_nodes', [])
                    }
            
            # Date-based invoice queries (e.g., "invoices in April 2025")
            elif 'invoice' in query_lower and any(m in query_lower for m in ['january','february','march','april','may','june','july','august','september','october','november','december']):
                result = self._execute_invoice_date_query(query)
                if result:
                    return {
                        'answer': result.get('answer', ''),
                        'query_type': 'aggregation',
                        'data': result.get('results', ''),
                        'highlighted_nodes': result.get('highlighted_nodes', [])
                    }
            
            # Journal entries cleared/outstanding
            elif 'journal' in query_lower and ('clear' in query_lower or 'outstanding' in query_lower or 'unpaid' in query_lower or 'payment' in query_lower):
                result = self._execute_journal_entry_status_query()
                if result:
                    return {
                        'answer': result.get('answer', ''),
                        'query_type': 'broken_flow',
                        'data': result.get('results', ''),
                        'highlighted_nodes': result.get('highlighted_nodes', [])
                    }
            
            # Sales orders never delivered
            elif 'sales order' in query_lower and ('never' in query_lower or 'not' in query_lower or 'without' in query_lower or 'undelivered' in query_lower):
                result = self._execute_undelivered_orders_query()
                if result:
                    return {
                        'answer': result.get('answer', ''),
                        'query_type': 'broken_flow',
                        'data': result.get('results', ''),
                        'highlighted_nodes': result.get('highlighted_nodes', [])
                    }
            
            # Percentage delivered and billed
            elif 'percentage' in query_lower or 'percent' in query_lower or '%' in query_lower:
                result = self._execute_delivery_billing_percentage_query()
                if result:
                    return {
                        'answer': result.get('answer', ''),
                        'query_type': 'aggregation',
                        'data': result.get('results', ''),
                        'highlighted_nodes': result.get('highlighted_nodes', [])
                    }
            
        except Exception as e:
            print(f"Graph query execution error: {e}")
        
        return None
    
    def _is_valid_query(self, query: str) -> bool:
        """Guardrail: Check if query is related to the dataset"""
        
        guardrail_prompt = f"""You are a guardrail system for a SAP Order-to-Cash data query system.

Determine if the following query is relevant to the SAP O2C dataset, which includes:
- Sales Orders
- Deliveries
- Invoices/Billing Documents
- Journal Entries and Accounting
- Payments
- Customers and Business Partners
- Products
- Plants and Locations

Valid queries ask about:
- Relationships between entities
- Business flows and processes
- Data analysis and aggregations
- Specific records or patterns in the data

Invalid queries include:
- General knowledge questions
- Creative writing requests
- Unrelated topics (politics, entertainment, etc.)
- Personal questions
- Code generation requests (unless for querying this data)

Query: "{query}"

Respond with ONLY "VALID" or "INVALID".
"""
        
        try:
            response = self.model.generate_content(guardrail_prompt)
            result = response.text.strip().upper()
            return 'VALID' in result
        except Exception as e:
            print(f"Guardrail check error: {e}")
            return True  # Default to allowing if guardrail fails
    
    def _generate_response(self, query: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Generate response using LLM"""
        
        # Get graph statistics for context
        stats = self._get_graph_context()
        
        # Build conversation context
        history_text = ""
        if conversation_history:
            for msg in conversation_history[-3:]:  # Last 3 exchanges
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                history_text += f"{role.upper()}: {content}\n"
        
        # Create analysis prompt
        prompt = self._create_analysis_prompt(query, stats, history_text)
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text
            
            # Try to extract structured data
            answer, query_type, data, highlighted_nodes = self._parse_response(result_text, query)
            
            return {
                'answer': answer,
                'query_type': query_type,
                'data': data,
                'highlighted_nodes': highlighted_nodes
            }
            
        except Exception as e:
            return {
                'answer': f"I encountered an error processing your query: {str(e)}",
                'query_type': 'error',
                'data': None,
                'highlighted_nodes': []
            }
    
    def _create_analysis_prompt(self, query: str, stats: Dict, history: str) -> str:
        """Create the analysis prompt for the LLM"""
        
        return f"""You are a SAP Order-to-Cash data analyst. You have access to a graph database with the following structure:

=== GRAPH STATISTICS ===
{json.dumps(stats, indent=2)}

=== ENTITY RELATIONSHIPS ===
Core Business Flow:
Customer → Sales Order → Sales Order Item → Delivery → Delivery Item → Invoice → Invoice Item → Product
Invoice → Journal Entry → Payment

Key Relationships:
- PLACED: Customer places Sales Order
- HAS_ITEM: Orders, Deliveries, and Invoices have Items
- REFERS_TO: Items (Sales Order Item, Delivery Item, Invoice Item) reference Products
- FULFILLED_BY: Sales Orders fulfilled by Deliveries
- FULFILLS: Delivery Items fulfill Sales Order Items
- BILLS: Invoice Items bill Deliveries
- BILLED_TO: Invoices billed to Customers
- POSTED_AS: Invoices posted as Journal Entries
- CLEARED_BY: Journal Entries cleared by Payments
- HAS_ADDRESS: Customers have Addresses
- SHIPPED_FROM: Items shipped from Plants

=== CONVERSATION HISTORY ===
{history}

=== USER QUERY ===
{query}

=== YOUR TASK ===
Analyze this query and provide a comprehensive answer based on the available data.

1. Identify what type of query this is:
   - aggregation: Counting, summing, grouping
   - trace_flow: Following a document through the business process
   - broken_flow: Finding incomplete or missing links
   - relationship: Understanding connections between entities
   - search: Finding specific records

2. Execute the query logic by:
   - Determining which entities are involved
   - Identifying the relationships to traverse
   - Performing calculations if needed
   - Finding specific nodes or patterns

3. Provide your response in this format:

QUERY_TYPE: [type]
ANSWER: [Your natural language answer with specific data and numbers]
HIGHLIGHTED_NODES: [Comma-separated list of node IDs relevant to this query, e.g., SO_740533,CUST_320000082]
DATA: [Any structured data like tables or lists, in plain text format]

Important:
- Be specific and use actual data from the graph
- Include counts, IDs, and concrete examples
- If you can't answer with certainty, explain what data is missing
- For trace queries, show the complete path
- For broken flow queries, identify specific gaps
"""
    
    def _get_graph_context(self) -> Dict[str, Any]:
        """Get relevant context from the graph"""
        node_types = {}
        for node_id in self.graph.nodes():
            node_type = self.graph.nodes[node_id].get('type', 'Unknown')
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        edge_types = {}
        for _, _, _, edge_data in self.graph.edges(keys=True, data=True):
            edge_type = edge_data.get('type', 'Unknown')
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
        
        # Sample some IDs for reference
        sample_nodes = {}
        for node_type in list(set(node_types.keys()))[:5]:
            samples = [nid for nid in self.graph.nodes() if self.graph.nodes[nid].get('type') == node_type][:3]
            sample_nodes[node_type] = samples
        
        return {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'node_types': node_types,
            'edge_types': edge_types,
            'sample_node_ids': sample_nodes
        }
    
    def _parse_response(self, response_text: str, original_query: str) -> tuple:
        """Parse LLM response to extract structured components"""
        
        # Default values
        answer = response_text
        query_type = 'general'
        data = None
        highlighted_nodes = []
        
        # Try to extract structured sections
        lines = response_text.split('\n')
        current_section = None
        sections = {'ANSWER': [], 'DATA': [], 'HIGHLIGHTED_NODES': []}
        
        for line in lines:
            if line.startswith('QUERY_TYPE:'):
                query_type = line.replace('QUERY_TYPE:', '').strip()
            elif line.startswith('ANSWER:'):
                current_section = 'ANSWER'
                sections['ANSWER'].append(line.replace('ANSWER:', '').strip())
            elif line.startswith('HIGHLIGHTED_NODES:'):
                current_section = 'HIGHLIGHTED_NODES'
                nodes_text = line.replace('HIGHLIGHTED_NODES:', '').strip()
                if nodes_text:
                    sections['HIGHLIGHTED_NODES'].append(nodes_text)
            elif line.startswith('DATA:'):
                current_section = 'DATA'
                sections['DATA'].append(line.replace('DATA:', '').strip())
            elif current_section and line.strip():
                sections[current_section].append(line)
        
        # Build answer
        if sections['ANSWER']:
            answer = '\n'.join(sections['ANSWER']).strip()
        else:
            answer = response_text
        
        # Parse highlighted nodes
        if sections['HIGHLIGHTED_NODES']:
            nodes_text = ' '.join(sections['HIGHLIGHTED_NODES'])
            highlighted_nodes = [n.strip() for n in nodes_text.replace(',', ' ').split() if n.strip()]
        
        # Parse data section
        if sections['DATA']:
            data = '\n'.join(sections['DATA']).strip()
        
        return answer, query_type, data, highlighted_nodes
    
    def _execute_trace_query(self, query: str) -> Optional[Dict]:
        """Execute a trace query to follow document flow"""
        import re
        
        start_node = None
        
        # 1. Try to extract document IDs from query
        inv_match = re.search(r'(90\d{6}|invoice\s+\d+|INV_\d+)', query, re.IGNORECASE)
        so_match = re.search(r'(74\d{4}|sales.*order\s+\d+|SO_\d+)', query, re.IGNORECASE)
        del_match = re.search(r'(80\d{6}|delivery\s+\d+|DEL_\d+)', query, re.IGNORECASE)
        cust_match = re.search(r'CUST_\d+', query, re.IGNORECASE)
        
        if inv_match:
            doc_num = re.search(r'\d+', inv_match.group(0)).group(0)
            start_node = f"INV_{doc_num}"
        elif so_match:
            doc_num = re.search(r'\d+', so_match.group(0)).group(0)
            start_node = f"SO_{doc_num}"
        elif del_match:
            doc_num = re.search(r'\d+', del_match.group(0)).group(0)
            start_node = f"DEL_{doc_num}"
        elif cust_match:
            start_node = cust_match.group(0).upper()
        
        # 2. If no ID found, try to find customer by name in query
        if not start_node or not self.graph.has_node(start_node):
            # Extract potential names: quoted strings or capitalized multi-word names
            name_match = re.search(r"['\"]([^'\"]+)['\"]", query)
            if not name_match:
                # Try to find capitalized hyphenated or multi-word names (e.g., Bradley-Kelley, Nguyen-Davis)
                name_match = re.search(r'\b([A-Z][a-z]+-[A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+)?)\b', query)
            if not name_match:
                # Try capitalized words that look like company/person names
                name_match = re.search(r'\b([A-Z][a-z]+(?:[,\s]+[A-Z][a-z]+)+)\b', query)
            if not name_match:
                # Try single capitalized word at the end or after 'for'/'of' (e.g., "Cardenas", "for Cardenas")
                name_match = re.search(r'(?:for|of|from)?\s*\b([A-Z][a-z]{3,})\s*$', query)
            
            if name_match:
                search_name = name_match.group(1).lower().strip()
                for node_id in self.graph.nodes():
                    if node_id.startswith('CUST_'):
                        node_data = self.graph.nodes[node_id]
                        cust_name = node_data.get('businessPartnerFullName', node_data.get('label', '')).lower()
                        if search_name in cust_name or cust_name in search_name:
                            start_node = node_id
                            break
        
        # 3. If still nothing found and no name was detected, pick a sample invoice
        if not start_node or not self.graph.has_node(start_node):
            # Only fall back to sample if no specific entity was mentioned
            has_specific_entity = any(w in query.lower() for w in ['for ', 'of ', 'from '])
            if has_specific_entity:
                return None  # Don't return random data when user asked for a specific entity
            
            for node_id in self.graph.nodes():
                if node_id.startswith('INV_') and '_ITEM_' not in node_id:
                    has_je = False
                    has_item = False
                    for succ in self.graph.successors(node_id):
                        if succ.startswith('JE_'):
                            has_je = True
                        if succ.startswith('INV_') and '_ITEM_' in succ:
                            has_item = True
                    if has_je and has_item:
                        start_node = node_id
                        break
        
        if start_node and self.graph.has_node(start_node):
            nodes_in_flow = self._trace_document_flow(start_node)
            path_description = self._describe_path(nodes_in_flow)
            
            return {
                'nodes': list(nodes_in_flow),
                'path': path_description
            }
        
        return None
    
    def _trace_document_flow(self, start_node: str) -> set:
        """Trace all connected nodes in document flow - LIMITED to core O2C entities only"""
        visited = set()
        to_visit = [start_node]
        
        # Core flow node types - exclude Product and Address to avoid clutter
        flow_types = {'Customer', 'SalesOrder', 'SalesOrderItem', 'Delivery', 'DeliveryItem', 
                      'Invoice', 'InvoiceItem', 'JournalEntry', 'Payment'}
        
        while to_visit:
            current = to_visit.pop(0)
            if current in visited:
                continue
            
            # Check if current node is a flow type
            if self.graph.has_node(current):
                node_type = self.graph.nodes[current].get('type', 'Unknown')
                if node_type not in flow_types:
                    continue  # Skip non-flow nodes like Product, Address
            
            visited.add(current)
            
            # Get predecessors and successors (only flow types)
            for pred in self.graph.predecessors(current):
                if pred not in visited and self.graph.has_node(pred):
                    pred_type = self.graph.nodes[pred].get('type', 'Unknown')
                    if pred_type in flow_types:
                        to_visit.append(pred)
            
            for succ in self.graph.successors(current):
                if succ not in visited and self.graph.has_node(succ):
                    succ_type = self.graph.nodes[succ].get('type', 'Unknown')
                    if succ_type in flow_types:
                        to_visit.append(succ)
        
        return visited
    
    def _describe_path(self, nodes: set) -> str:
        """Describe the path through nodes"""
        # Order nodes by type
        type_order = ['Customer', 'SalesOrder', 'SalesOrderItem', 'Delivery', 'DeliveryItem', 'Invoice', 'InvoiceItem', 'JournalEntry', 'Payment']
        
        nodes_by_type = {}
        for node_id in nodes:
            if self.graph.has_node(node_id):
                node_type = self.graph.nodes[node_id].get('type', 'Unknown')
                if node_type not in nodes_by_type:
                    nodes_by_type[node_type] = []
                nodes_by_type[node_type].append(node_id)
        
        description = "Document Flow Trace:\n\n"
        
        # Show only key nodes (limit items to 3 each)
        for node_type in type_order:
            if node_type in nodes_by_type:
                node_list = nodes_by_type[node_type][:3]  # Limit to 3 items per type
                remaining = len(nodes_by_type[node_type]) - 3
                
                description += f"{node_type}:\n"
                for nid in node_list:
                    label = self.graph.nodes[nid].get('label', nid)
                    description += f"  • {label}\n"
                
                if remaining > 0:
                    description += f"  ... and {remaining} more\n"
                description += "\n"
        
        # Show the flow diagram
        description += "Flow Sequence: "
        flow_parts = []
        for node_type in type_order:
            if node_type in nodes_by_type:
                flow_parts.append(node_type)
        description += " → ".join(flow_parts)
        
        return description
    
    def _execute_broken_flow_query(self) -> Optional[Dict]:
        """Find orders with broken/incomplete flows"""
        broken_flows = []
        
        # Find sales orders without deliveries
        for node_id in self.graph.nodes():
            if node_id.startswith('SO_'):
                has_delivery = False
                for succ in self.graph.successors(node_id):
                    if succ.startswith('DEL_'):
                        has_delivery = True
                        break
                
                if not has_delivery:
                    broken_flows.append(f"Sales Order {node_id} has no delivery")
        
        # Find deliveries without invoices (check if any invoice item bills this delivery)
        for node_id in self.graph.nodes():
            if node_id.startswith('DEL_'):
                has_invoice = False
                # Check predecessors for invoice items that bill this delivery
                for pred in self.graph.predecessors(node_id):
                    if pred.startswith('INV_') and '_ITEM_' in pred:
                        has_invoice = True
                        break
                
                if not has_invoice:
                    broken_flows.append(f"Delivery {node_id} not billed")
        
        if broken_flows:
            results = "Broken/Incomplete Flows Found:\n\n"
            results += f"Total issues found: {len(broken_flows)}\n\n"
            results += "\n".join(broken_flows[:10])
            if len(broken_flows) > 10:
                results += f"\n\n... and {len(broken_flows) - 10} more issues"
            return {'results': results}
        
        return {'results': 'No broken or incomplete flows detected. All sales orders have been delivered and billed correctly.'}
    
    def _execute_product_billing_query(self) -> Optional[Dict]:
        """Find products with the most associated billing documents"""
        from collections import defaultdict
        
        # Count unique invoices per product
        product_invoice_count = defaultdict(set)
        
        # Traverse: Product <- InvoiceItem <- Invoice
        for node_id in self.graph.nodes():
            if node_id.startswith('PROD_'):
                # Find all invoice items that reference this product
                for pred in self.graph.predecessors(node_id):
                    if pred.startswith('INV_') and '_ITEM_' in pred:
                        # Extract the invoice ID from the invoice item ID
                        # Format: INV_90504248_ITEM_10 -> INV_90504248
                        invoice_id = pred.split('_ITEM_')[0]
                        product_invoice_count[node_id].add(invoice_id)
        
        # Convert sets to counts and sort
        product_counts = [(prod_id, len(invoices)) for prod_id, invoices in product_invoice_count.items()]
        product_counts.sort(key=lambda x: x[1], reverse=True)
        
        if not product_counts:
            return None
        
        # Get top 10 products
        top_products = product_counts[:10]
        
        # Build results table
        results = "Products with Most Billing Documents:\n\n"
        results += f"{'Product ID':<30} | {'Billing Doc Count':>18}\n"
        results += "-" * 50 + "\n"
        
        highlighted = []
        for prod_id, count in top_products:
            # Get product label
            prod_label = self.graph.nodes[prod_id].get('label', prod_id)
            results += f"{prod_label:<30} | {count:>18}\n"
            highlighted.append(prod_id)
        
        # Build answer
        top_prod = top_products[0]
        top_label = self.graph.nodes[top_prod[0]].get('label', top_prod[0])
        answer = f"The product '{top_label}' ({top_prod[0]}) is associated with the highest number of billing documents ({top_prod[1]} invoices).\n\n"
        answer += f"Top {len(top_products)} products by billing document count are shown in the data table."
        
        return {
            'results': results,
            'highlighted_nodes': highlighted,
            'answer': answer
        }
    
    def _execute_customer_orders_query(self) -> Optional[Dict]:
        """Find customers with the most sales orders"""
        from collections import defaultdict
        
        customer_orders = defaultdict(list)
        for node_id in self.graph.nodes():
            if node_id.startswith('CUST_'):
                for succ in self.graph.successors(node_id):
                    if succ.startswith('SO_'):
                        customer_orders[node_id].append(succ)
        
        customer_counts = [(cust_id, len(orders)) for cust_id, orders in customer_orders.items()]
        customer_counts.sort(key=lambda x: x[1], reverse=True)
        
        if not customer_counts:
            return None
        
        results = "Customers with Most Sales Orders:\n\n"
        results += f"{'Customer':<35} | {'Sales Orders':>12}\n"
        results += "-" * 50 + "\n"
        
        highlighted = []
        for cust_id, count in customer_counts[:10]:
            label = self.graph.nodes[cust_id].get('label', cust_id)
            results += f"{label:<35} | {count:>12}\n"
            highlighted.append(cust_id)
        
        top = customer_counts[0]
        top_label = self.graph.nodes[top[0]].get('label', top[0])
        answer = f"Customer '{top_label}' ({top[0]}) has the most sales orders ({top[1]}).\n\nTop customers by order count are shown in the data table."
        
        return {'results': results, 'highlighted_nodes': highlighted, 'answer': answer}
    
    def _execute_unbilled_deliveries_query(self) -> Optional[Dict]:
        """Find deliveries that haven't been billed"""
        unbilled = []
        highlighted = []
        
        for node_id in self.graph.nodes():
            if node_id.startswith('DEL_'):
                has_invoice = False
                for pred in self.graph.predecessors(node_id):
                    if pred.startswith('INV_') and '_ITEM_' in pred:
                        has_invoice = True
                        break
                if not has_invoice:
                    label = self.graph.nodes[node_id].get('label', node_id)
                    unbilled.append(f"{label} ({node_id})")
                    highlighted.append(node_id)
        
        if unbilled:
            results = f"Unbilled Deliveries Found: {len(unbilled)}\n\n"
            results += "\n".join(unbilled[:15])
            if len(unbilled) > 15:
                results += f"\n\n... and {len(unbilled) - 15} more"
        else:
            results = "All deliveries have been billed."
        
        return {'results': results, 'highlighted_nodes': highlighted[:10]}
    
    def _execute_customer_invoice_query(self, query: str) -> Optional[Dict]:
        """Find total billed amount and invoice count for a customer"""
        import re
        from collections import defaultdict
        
        # Extract customer ID or name from query
        cust_match = re.search(r'CUST_\d+', query, re.IGNORECASE)
        cust_name_match = re.search(r"['\"]([\w\s,\-&]+)['\"]", query)
        
        customer_id = None
        if cust_match:
            customer_id = cust_match.group(0).upper()
        elif cust_name_match:
            # Search for customer by name
            search_name = cust_name_match.group(1).lower()
            for node_id in self.graph.nodes():
                if node_id.startswith('CUST_'):
                    node_data = self.graph.nodes[node_id]
                    cust_name = node_data.get('businessPartnerFullName', node_data.get('label', '')).lower()
                    if search_name in cust_name or cust_name in search_name:
                        customer_id = node_id
                        break
        
        if not customer_id or not self.graph.has_node(customer_id):
            return None
        
        # Find all invoices for this customer (BILLED_TO edge: Invoice -> Customer)
        invoices = []
        total_amount = 0.0
        
        for pred in self.graph.predecessors(customer_id):
            if pred.startswith('INV_') and '_ITEM_' not in pred:
                invoice_data = self.graph.nodes[pred]
                invoices.append(pred)
                
                # Try to get the total amount (different possible field names)
                amount = invoice_data.get('totalNetAmount') or invoice_data.get('netAmount') or invoice_data.get('total_amount') or 0
                try:
                    total_amount += float(amount)
                except (ValueError, TypeError):
                    pass
        
        # Get customer name
        cust_data = self.graph.nodes[customer_id]
        cust_name = cust_data.get('businessPartnerFullName', cust_data.get('label', customer_id))
        currency = "INR"  # Default, could extract from first invoice
        
        results = f"Customer Invoice Summary for '{cust_name}' ({customer_id}):\n\n"
        results += f"Total Invoices: {len(invoices)}\n"
        results += f"Total Billed Amount: {currency} {total_amount:,.2f}\n"
        results += f"Average Invoice Amount: {currency} {(total_amount/len(invoices) if invoices else 0):,.2f}\n\n"
        
        if len(invoices) > 0:
            results += "Invoice List (first 10):\n"
            for inv_id in invoices[:10]:
                inv_data = self.graph.nodes[inv_id]
                inv_amount = inv_data.get('totalNetAmount', 'N/A')
                inv_label = inv_data.get('label', inv_id)
                results += f"  • {inv_label}: {currency} {inv_amount}\n"
            if len(invoices) > 10:
                results += f"  ... and {len(invoices) - 10} more invoices\n"
        
        answer = f"Customer '{cust_name}' ({customer_id}) has {len(invoices)} invoices with a total billed amount of {currency} {total_amount:,.2f}."
        
        return {
            'results': results,
            'highlighted_nodes': [customer_id] + invoices[:5],
            'answer': answer
        }
    
    def _execute_invoice_date_query(self, query: str) -> Optional[Dict]:
        """Find invoices created in a specific month/year with total value"""
        import re
        from datetime import datetime
        
        month_names = {'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                       'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12}
        
        query_lower = query.lower()
        target_month = None
        target_year = None
        
        for name, num in month_names.items():
            if name in query_lower:
                target_month = num
                break
        
        year_match = re.search(r'20\d{2}', query)
        if year_match:
            target_year = int(year_match.group(0))
        
        if not target_month:
            return None
        
        matching_invoices = []
        total_amount = 0.0
        currency = 'INR'
        highlighted = []
        
        for node_id in self.graph.nodes():
            if node_id.startswith('INV_') and '_ITEM_' not in node_id:
                node_data = self.graph.nodes[node_id]
                date_str = node_data.get('billingDocumentDate') or node_data.get('creationDate', '')
                if not date_str:
                    continue
                try:
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    if dt.month == target_month and (target_year is None or dt.year == target_year):
                        amount = float(node_data.get('totalNetAmount', 0) or 0)
                        currency = node_data.get('transactionCurrency', 'INR')
                        label = node_data.get('label', node_id)
                        matching_invoices.append((node_id, label, amount, dt.strftime('%Y-%m-%d')))
                        total_amount += amount
                        highlighted.append(node_id)
                except (ValueError, TypeError):
                    continue
        
        month_name = [k for k, v in month_names.items() if v == target_month][0].title()
        year_str = str(target_year) if target_year else 'all years'
        
        results = f"Invoices in {month_name} {year_str}:\n\n"
        results += f"Total Invoices: {len(matching_invoices)}\n"
        results += f"Total Value: {currency} {total_amount:,.2f}\n"
        results += f"Average Value: {currency} {(total_amount / len(matching_invoices) if matching_invoices else 0):,.2f}\n\n"
        
        if matching_invoices:
            results += f"{'Invoice':<25} | {'Date':<12} | {'Amount':>15}\n"
            results += "-" * 55 + "\n"
            for inv_id, label, amount, date in matching_invoices[:15]:
                results += f"{label:<25} | {date:<12} | {currency} {amount:>10,.2f}\n"
            if len(matching_invoices) > 15:
                results += f"\n... and {len(matching_invoices) - 15} more invoices\n"
        
        answer = f"In {month_name} {year_str}, {len(matching_invoices)} invoices were created with a total value of {currency} {total_amount:,.2f}."
        return {'results': results, 'highlighted_nodes': highlighted[:10], 'answer': answer}
    
    def _execute_journal_entry_status_query(self) -> Optional[Dict]:
        """Find which journal entries are cleared by payments and which are outstanding"""
        cleared = []
        outstanding = []
        
        for node_id in self.graph.nodes():
            if not node_id.startswith('JE_'):
                continue
            has_payment = False
            payment_id = None
            for succ in self.graph.successors(node_id):
                if succ.startswith('PAY_'):
                    has_payment = True
                    payment_id = succ
                    break
            label = self.graph.nodes[node_id].get('label', node_id)
            if has_payment:
                pay_label = self.graph.nodes[payment_id].get('label', payment_id)
                cleared.append((node_id, label, payment_id, pay_label))
            else:
                outstanding.append((node_id, label))
        
        results = f"Journal Entry Payment Status:\n\n"
        results += f"Total Journal Entries: {len(cleared) + len(outstanding)}\n"
        results += f"Cleared (paid): {len(cleared)}\n"
        results += f"Outstanding (unpaid): {len(outstanding)}\n\n"
        
        if outstanding:
            results += "Outstanding Journal Entries:\n"
            for je_id, label in outstanding:
                inv_label = 'N/A'
                for pred in self.graph.predecessors(je_id):
                    if pred.startswith('INV_') and '_ITEM_' not in pred:
                        inv_label = self.graph.nodes[pred].get('label', pred)
                        break
                results += f"  • {label} (from {inv_label})\n"
        
        results += "\nSample Cleared Journal Entries (first 5):\n"
        for je_id, label, pay_id, pay_label in cleared[:5]:
            results += f"  • {label} → cleared by {pay_label}\n"
        if len(cleared) > 5:
            results += f"  ... and {len(cleared) - 5} more cleared entries\n"
        
        highlighted = [je_id for je_id, _ in outstanding]
        answer = f"Out of {len(cleared) + len(outstanding)} journal entries, {len(cleared)} have been cleared by payments and {len(outstanding)} are still outstanding."
        return {'results': results, 'highlighted_nodes': highlighted, 'answer': answer}
    
    def _execute_undelivered_orders_query(self) -> Optional[Dict]:
        """Find sales orders that were created but never delivered"""
        delivered = []
        undelivered = []
        
        for node_id in self.graph.nodes():
            if not node_id.startswith('SO_'):
                continue
            has_delivery = False
            for succ in self.graph.successors(node_id):
                if succ.startswith('DEL_'):
                    has_delivery = True
                    break
            label = self.graph.nodes[node_id].get('label', node_id)
            if has_delivery:
                delivered.append(node_id)
            else:
                undelivered.append((node_id, label))
        
        total = len(delivered) + len(undelivered)
        results = f"Sales Order Delivery Status:\n\n"
        results += f"Total Sales Orders: {total}\n"
        results += f"Delivered: {len(delivered)}\n"
        results += f"Never Delivered: {len(undelivered)}\n\n"
        
        if undelivered:
            results += "Undelivered Sales Orders:\n"
            for so_id, label in undelivered:
                cust_label = 'Unknown'
                for pred in self.graph.predecessors(so_id):
                    if pred.startswith('CUST_'):
                        cust_label = self.graph.nodes[pred].get('label', pred)
                        break
                results += f"  • {label} (Customer: {cust_label})\n"
        
        highlighted = [so_id for so_id, _ in undelivered]
        answer = f"Out of {total} sales orders, {len(undelivered)} were created but never delivered ({(len(undelivered)/total*100) if total else 0:.1f}%)."
        return {'results': results, 'highlighted_nodes': highlighted, 'answer': answer}
    
    def _execute_delivery_billing_percentage_query(self) -> Optional[Dict]:
        """Calculate percentage of sales orders successfully delivered and billed"""
        total_so = 0
        delivered_so = 0
        delivered_and_billed_so = 0
        
        for node_id in self.graph.nodes():
            if not node_id.startswith('SO_'):
                continue
            total_so += 1
            deliveries = [succ for succ in self.graph.successors(node_id) if succ.startswith('DEL_')]
            if not deliveries:
                continue
            delivered_so += 1
            all_billed = True
            for del_id in deliveries:
                has_invoice = False
                for pred in self.graph.predecessors(del_id):
                    if pred.startswith('INV_') and '_ITEM_' in pred:
                        has_invoice = True
                        break
                if not has_invoice:
                    all_billed = False
                    break
            if all_billed:
                delivered_and_billed_so += 1
        
        pct_delivered = (delivered_so / total_so * 100) if total_so else 0
        pct_billed = (delivered_and_billed_so / total_so * 100) if total_so else 0
        
        results = f"Sales Order Fulfillment Analysis:\n\n"
        results += f"Total Sales Orders: {total_so}\n"
        results += f"Successfully Delivered: {delivered_so} ({pct_delivered:.1f}%)\n"
        results += f"Successfully Delivered AND Billed: {delivered_and_billed_so} ({pct_billed:.1f}%)\n"
        results += f"Not Yet Delivered: {total_so - delivered_so} ({((total_so - delivered_so)/total_so*100) if total_so else 0:.1f}%)\n"
        
        answer = f"{pct_billed:.1f}% of sales orders ({delivered_and_billed_so} out of {total_so}) have been successfully delivered and billed."
        return {'results': results, 'highlighted_nodes': [], 'answer': answer}
