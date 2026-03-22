import networkx as nx
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import json

class GraphBuilder:
    """Construct graph representation of SAP O2C data"""
    
    def __init__(self, entities: Dict[str, List[Dict]]):
        self.entities = entities
        self.graph = nx.MultiDiGraph()
        self.node_index = {}  # For quick lookups
        
    def build_graph(self) -> nx.MultiDiGraph:
        """Build the complete graph with all nodes and edges"""
        # Add nodes for each entity type
        self._add_sales_order_nodes()
        self._add_delivery_nodes()
        self._add_billing_nodes()
        self._add_journal_entry_nodes()
        self._add_payment_nodes()
        self._add_customer_nodes()
        self._add_product_nodes()
        self._add_plant_nodes()
        
        # Add edges to represent relationships
        self._add_sales_relationships()
        self._add_delivery_relationships()
        self._add_billing_relationships()
        self._add_accounting_relationships()
        self._add_customer_relationships()
        self._add_product_relationships()
        
        return self.graph
    
    # ===== NODE CREATION =====
    
    def _add_sales_order_nodes(self):
        """Add sales order headers and items as nodes"""
        for so in self.entities.get('sales_order_headers', []):
            node_id = f"SO_{so['salesOrder']}"
            self.graph.add_node(
                node_id,
                type='SalesOrder',
                label=f"SO {so['salesOrder']}",
                **self._clean_properties(so)
            )
            self.node_index[node_id] = so
        
        for item in self.entities.get('sales_order_items', []):
            node_id = f"SOI_{item['salesOrder']}_{item['salesOrderItem']}"
            self.graph.add_node(
                node_id,
                type='SalesOrderItem',
                label=f"Item {item['salesOrderItem']}",
                **self._clean_properties(item)
            )
            self.node_index[node_id] = item
    
    def _add_delivery_nodes(self):
        """Add delivery headers and items as nodes"""
        for delivery in self.entities.get('outbound_delivery_headers', []):
            node_id = f"DEL_{delivery['deliveryDocument']}"
            self.graph.add_node(
                node_id,
                type='Delivery',
                label=f"Delivery {delivery['deliveryDocument']}",
                **self._clean_properties(delivery)
            )
            self.node_index[node_id] = delivery
        
        for item in self.entities.get('outbound_delivery_items', []):
            node_id = f"DELI_{item['deliveryDocument']}_{item['deliveryDocumentItem']}"
            self.graph.add_node(
                node_id,
                type='DeliveryItem',
                label=f"Item {item['deliveryDocumentItem']}",
                **self._clean_properties(item)
            )
            self.node_index[node_id] = item
    
    def _add_billing_nodes(self):
        """Add billing documents as nodes"""
        for billing in self.entities.get('billing_document_headers', []):
            node_id = f"INV_{billing['billingDocument']}"
            self.graph.add_node(
                node_id,
                type='Invoice',
                label=f"Invoice {billing['billingDocument']}",
                **self._clean_properties(billing)
            )
            self.node_index[node_id] = billing
        
        # Add billing document items
        for item in self.entities.get('billing_document_items', []):
            node_id = f"INV_{item['billingDocument']}_ITEM_{item['billingDocumentItem']}"
            self.graph.add_node(
                node_id,
                type='InvoiceItem',
                label=f"Invoice Item {item['billingDocument']}-{item['billingDocumentItem']}",
                **self._clean_properties(item)
            )
            self.node_index[node_id] = item

    
    def _add_journal_entry_nodes(self):
        """Add journal entries as nodes"""
        # Group by accounting document
        je_groups = defaultdict(list)
        for je in self.entities.get('journal_entry_items_accounts_receivable', []):
            key = f"{je['companyCode']}_{je['fiscalYear']}_{je['accountingDocument']}"
            je_groups[key].append(je)
        
        for key, items in je_groups.items():
            first_item = items[0]
            node_id = f"JE_{first_item['companyCode']}_{first_item['fiscalYear']}_{first_item['accountingDocument']}"
            self.graph.add_node(
                node_id,
                type='JournalEntry',
                label=f"JE {first_item['accountingDocument']}",
                companyCode=first_item['companyCode'],
                fiscalYear=first_item['fiscalYear'],
                accountingDocument=first_item['accountingDocument'],
                postingDate=first_item.get('postingDate'),
                items=len(items)
            )
            self.node_index[node_id] = first_item
    
    def _add_payment_nodes(self):
        """Add payments as nodes (derived from clearing documents)"""
        # Payments are identified by clearing documents in journal entries
        clearing_docs = set()
        for je in self.entities.get('journal_entry_items_accounts_receivable', []):
            if je.get('clearingAccountingDocument'):
                clearing_docs.add((je['companyCode'], je['clearingDocFiscalYear'], je['clearingAccountingDocument']))
        
        for company_code, fiscal_year, doc in clearing_docs:
            node_id = f"PAY_{company_code}_{fiscal_year}_{doc}"
            self.graph.add_node(
                node_id,
                type='Payment',
                label=f"Payment {doc}",
                companyCode=company_code,
                fiscalYear=fiscal_year,
                clearingDocument=doc
            )
    
    def _add_customer_nodes(self):
        """Add customers and addresses as nodes"""
        for bp in self.entities.get('business_partners', []):
            node_id = f"CUST_{bp['businessPartner']}"
            self.graph.add_node(
                node_id,
                type='Customer',
                label=bp.get('businessPartnerFullName', bp['businessPartner']),
                **self._clean_properties(bp)
            )
            self.node_index[node_id] = bp
        
        for addr in self.entities.get('business_partner_addresses', []):
            node_id = f"ADDR_{addr['businessPartner']}_{addr['addressId']}"
            self.graph.add_node(
                node_id,
                type='Address',
                label=f"{addr.get('cityName', '')} {addr.get('region', '')}".strip() or f"Address {addr['addressId']}",
                **self._clean_properties(addr)
            )
            self.node_index[node_id] = addr
    
    def _add_product_nodes(self):
        """Add products as nodes"""
        for product in self.entities.get('products', []):
            node_id = f"PROD_{product['product']}"
            
            # Find product description
            description = ""
            for desc in self.entities.get('product_descriptions', []):
                if desc['product'] == product['product']:
                    description = desc.get('productDescription', '')
                    break
            
            self.graph.add_node(
                node_id,
                type='Product',
                label=description or product['product'],
                **self._clean_properties(product)
            )
            self.node_index[node_id] = product
    
    def _add_plant_nodes(self):
        """Add plants as nodes"""
        for plant in self.entities.get('plants', []):
            node_id = f"PLANT_{plant['plant']}"
            self.graph.add_node(
                node_id,
                type='Plant',
                label=plant.get('plantName', plant['plant']),
                **self._clean_properties(plant)
            )
            self.node_index[node_id] = plant
    
    # ===== EDGE CREATION =====
    
    def _add_sales_relationships(self):
        """Add relationships within sales entities"""
        # Customer -> Sales Order
        for so in self.entities.get('sales_order_headers', []):
            cust_id = f"CUST_{so['soldToParty']}"
            so_id = f"SO_{so['salesOrder']}"
            if self.graph.has_node(cust_id) and self.graph.has_node(so_id):
                self.graph.add_edge(cust_id, so_id, type='PLACED', label='placed')
        
        # Sales Order -> Sales Order Items
        for item in self.entities.get('sales_order_items', []):
            so_id = f"SO_{item['salesOrder']}"
            item_id = f"SOI_{item['salesOrder']}_{item['salesOrderItem']}"
            if self.graph.has_node(so_id) and self.graph.has_node(item_id):
                self.graph.add_edge(so_id, item_id, type='HAS_ITEM', label='has item')
        
        # Sales Order Item -> Product
        for item in self.entities.get('sales_order_items', []):
            if item.get('material'):
                item_id = f"SOI_{item['salesOrder']}_{item['salesOrderItem']}"
                prod_id = f"PROD_{item['material']}"
                if self.graph.has_node(item_id) and self.graph.has_node(prod_id):
                    self.graph.add_edge(item_id, prod_id, type='REFERS_TO', label='references')
        
        # Sales Order Item -> Plant
        for item in self.entities.get('sales_order_items', []):
            if item.get('productionPlant'):
                item_id = f"SOI_{item['salesOrder']}_{item['salesOrderItem']}"
                plant_id = f"PLANT_{item['productionPlant']}"
                if self.graph.has_node(item_id) and self.graph.has_node(plant_id):
                    self.graph.add_edge(item_id, plant_id, type='PRODUCED_AT', label='produced at')
    
    def _add_delivery_relationships(self):
        """Add delivery-related relationships"""
        # Delivery Item -> Sales Order Item (via referenceSdDocument)
        for del_item in self.entities.get('outbound_delivery_items', []):
            if del_item.get('referenceSdDocument') and del_item.get('referenceSdDocumentItem'):
                del_item_id = f"DELI_{del_item['deliveryDocument']}_{del_item['deliveryDocumentItem']}"
                so_item_id = f"SOI_{del_item['referenceSdDocument']}_{del_item['referenceSdDocumentItem']}"
                if self.graph.has_node(del_item_id) and self.graph.has_node(so_item_id):
                    self.graph.add_edge(del_item_id, so_item_id, type='FULFILLS', label='fulfills')
        
        # Delivery Header -> Delivery Items
        for del_item in self.entities.get('outbound_delivery_items', []):
            del_id = f"DEL_{del_item['deliveryDocument']}"
            del_item_id = f"DELI_{del_item['deliveryDocument']}_{del_item['deliveryDocumentItem']}"
            if self.graph.has_node(del_id) and self.graph.has_node(del_item_id):
                self.graph.add_edge(del_id, del_item_id, type='HAS_ITEM', label='has item')
        
        # Delivery Item -> Plant
        for del_item in self.entities.get('outbound_delivery_items', []):
            if del_item.get('plant'):
                del_item_id = f"DELI_{del_item['deliveryDocument']}_{del_item['deliveryDocumentItem']}"
                plant_id = f"PLANT_{del_item['plant']}"
                if self.graph.has_node(del_item_id) and self.graph.has_node(plant_id):
                    self.graph.add_edge(del_item_id, plant_id, type='SHIPPED_FROM', label='shipped from')
        
        # Sales Order -> Delivery (infer from delivery items)
        so_to_delivery = defaultdict(set)
        for del_item in self.entities.get('outbound_delivery_items', []):
            if del_item.get('referenceSdDocument'):
                so_to_delivery[del_item['referenceSdDocument']].add(del_item['deliveryDocument'])
        
        for so, deliveries in so_to_delivery.items():
            so_id = f"SO_{so}"
            for delivery in deliveries:
                del_id = f"DEL_{delivery}"
                if self.graph.has_node(so_id) and self.graph.has_node(del_id):
                    self.graph.add_edge(so_id, del_id, type='FULFILLED_BY', label='fulfilled by')
    
    def _add_billing_relationships(self):
        """Add billing-related relationships"""
        # Invoice -> Customer
        for billing in self.entities.get('billing_document_headers', []):
            inv_id = f"INV_{billing['billingDocument']}"
            cust_id = f"CUST_{billing['soldToParty']}"
            if self.graph.has_node(inv_id) and self.graph.has_node(cust_id):
                self.graph.add_edge(inv_id, cust_id, type='BILLED_TO', label='billed to')
        
        # Invoice -> InvoiceItem (HAS_ITEM)
        for item in self.entities.get('billing_document_items', []):
            inv_id = f"INV_{item['billingDocument']}"
            item_id = f"INV_{item['billingDocument']}_ITEM_{item['billingDocumentItem']}"
            if self.graph.has_node(inv_id) and self.graph.has_node(item_id):
                self.graph.add_edge(inv_id, item_id, type='HAS_ITEM', label='has item')
        
        # InvoiceItem -> Delivery (references delivery)
        for item in self.entities.get('billing_document_items', []):
            if item.get('referenceSdDocument'):
                item_id = f"INV_{item['billingDocument']}_ITEM_{item['billingDocumentItem']}"
                del_id = f"DEL_{item['referenceSdDocument']}"
                if self.graph.has_node(item_id) and self.graph.has_node(del_id):
                    self.graph.add_edge(item_id, del_id, type='BILLS', label='bills')
        
        # InvoiceItem -> Product
        for item in self.entities.get('billing_document_items', []):
            if item.get('material'):
                item_id = f"INV_{item['billingDocument']}_ITEM_{item['billingDocumentItem']}"
                prod_id = f"PROD_{item['material']}"
                if self.graph.has_node(item_id) and self.graph.has_node(prod_id):
                    self.graph.add_edge(item_id, prod_id, type='REFERS_TO', label='refers to')
    
    def _add_accounting_relationships(self):
        """Add accounting-related relationships"""
        # Invoice -> Journal Entry (via accountingDocument)
        for billing in self.entities.get('billing_document_headers', []):
            if billing.get('accountingDocument'):
                inv_id = f"INV_{billing['billingDocument']}"
                je_id = f"JE_{billing['companyCode']}_{billing['fiscalYear']}_{billing['accountingDocument']}"
                if self.graph.has_node(inv_id) and self.graph.has_node(je_id):
                    self.graph.add_edge(inv_id, je_id, type='POSTED_AS', label='posted as')
        
        # Journal Entry -> Payment (via clearing document)
        for je in self.entities.get('journal_entry_items_accounts_receivable', []):
            if je.get('clearingAccountingDocument'):
                je_id = f"JE_{je['companyCode']}_{je['fiscalYear']}_{je['accountingDocument']}"
                pay_id = f"PAY_{je['companyCode']}_{je['clearingDocFiscalYear']}_{je['clearingAccountingDocument']}"
                if self.graph.has_node(je_id) and self.graph.has_node(pay_id):
                    self.graph.add_edge(je_id, pay_id, type='CLEARED_BY', label='cleared by')
    
    def _add_customer_relationships(self):
        """Add customer-related relationships"""
        # Customer -> Address
        for addr in self.entities.get('business_partner_addresses', []):
            cust_id = f"CUST_{addr['businessPartner']}"
            addr_id = f"ADDR_{addr['businessPartner']}_{addr['addressId']}"
            if self.graph.has_node(cust_id) and self.graph.has_node(addr_id):
                self.graph.add_edge(cust_id, addr_id, type='HAS_ADDRESS', label='has address')
    
    def _add_product_relationships(self):
        """Add product-related relationships"""
        # Product -> Plant (via product_plants)
        for pp in self.entities.get('product_plants', []):
            prod_id = f"PROD_{pp['product']}"
            plant_id = f"PLANT_{pp['plant']}"
            if self.graph.has_node(prod_id) and self.graph.has_node(plant_id):
                self.graph.add_edge(prod_id, plant_id, type='AVAILABLE_AT', label='available at')
    
    def _clean_properties(self, data: Dict) -> Dict:
        """Clean properties for storage in nodes"""
        cleaned = {}
        for key, value in data.items():
            # Convert complex types to strings
            if isinstance(value, (dict, list)):
                cleaned[key] = json.dumps(value)
            elif value is not None and value != "":
                cleaned[key] = value
        return cleaned
    
    def get_graph_data(self) -> Dict[str, Any]:
        """Export graph as nodes and edges for API"""
        nodes = []
        edges = []
        
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            nodes.append({
                'id': node_id,
                'type': node_data.get('type', 'Unknown'),
                'label': node_data.get('label', node_id),
                'properties': {k: v for k, v in node_data.items() if k not in ['type', 'label']}
            })
        
        for source, target, key, edge_data in self.graph.edges(keys=True, data=True):
            edges.append({
                'source': source,
                'target': target,
                'type': edge_data.get('type', 'RELATED'),
                'label': edge_data.get('label', ''),
                'properties': {k: v for k, v in edge_data.items() if k not in ['type', 'label']}
            })
        
        return {'nodes': nodes, 'edges': edges}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics"""
        return {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'node_types': self._get_node_type_counts(),
            'edge_types': self._get_edge_type_counts()
        }
    
    def _get_node_type_counts(self) -> Dict[str, int]:
        """Count nodes by type"""
        counts = defaultdict(int)
        for node_id in self.graph.nodes():
            node_type = self.graph.nodes[node_id].get('type', 'Unknown')
            counts[node_type] += 1
        return dict(counts)
    
    def _get_edge_type_counts(self) -> Dict[str, int]:
        """Count edges by type"""
        counts = defaultdict(int)
        for _, _, _, edge_data in self.graph.edges(keys=True, data=True):
            edge_type = edge_data.get('type', 'Unknown')
            counts[edge_type] += 1
        return dict(counts)
