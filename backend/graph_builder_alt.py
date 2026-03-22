"""
REFERENCE IMPLEMENTATION ONLY - DO NOT USE IN PRODUCTION

This is an alternative graph builder implementation provided for reference.
It contains some good patterns but should NOT replace the existing graph_builder.py.

See ALTERNATIVE_GRAPH_BUILDER_ANALYSIS.md for detailed comparison.

Key differences from production code:
1. Combines data loading + graph building (vs. separation of concerns)
2. Different node naming: customer_ vs CUST_, sales_order_ vs SO_
3. Nested entity storage (slightly better but not worth refactoring)
4. Explicit mapping tables (cleaner pattern)
5. Better null checking (worth adopting)
6. Type-specific export details (worth adopting)

Patterns worth learning from:
- Defensive programming with null checks
- Explicit relationship mapping tables
- Structured export with type-specific details
- Limit parameter for large graph exports

Integration Status: ❌ NOT INTEGRATED - Reference only
"""

import os
import json
import glob
from pathlib import Path
from typing import Dict, List, Any, Optional
import networkx as nx
from collections import defaultdict


class O2CGraphBuilder:
    """
    REFERENCE IMPLEMENTATION - Alternative approach to building SAP O2C graph.
    
    Flow: Customer → Sales Order → Delivery → Billing → Journal Entry → Payment
    
    This is provided as a reference for comparing different design patterns.
    Use the production graph_builder.py for actual implementation.
    """
    
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.graph = nx.MultiDiGraph()
        
        # Store raw data for query processing
        self.entities = {
            'customers': {},
            'sales_orders': {},
            'sales_order_items': {},
            'deliveries': {},
            'delivery_items': {},
            'invoices': {},
            'invoice_items': {},
            'journal_entries': {},
            'payments': {},
            'products': {},
            'plants': {},
            'addresses': {}
        }
        
        # Mapping tables for relationships
        self.delivery_to_sales_order = {}
        self.invoice_to_journal = {}
        self.journal_to_payment = {}
        
    def load_jsonl_files(self, folder_name: str) -> List[Dict]:
        """Load all JSONL files from a specific folder."""
        folder_path = self.data_path.parent / folder_name
        data = []
        
        if not folder_path.exists():
            print(f"Warning: Folder {folder_name} not found")
            return data
            
        for file_path in folder_path.glob("*.jsonl"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            data.append(json.loads(line))
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
                
        return data
    
    def build_graph(self):
        """Main method to build the complete graph."""
        print("Loading data...")
        
        # Load all entities
        customers = self.load_jsonl_files('business_partners')
        addresses = self.load_jsonl_files('business_partner_addresses')
        sales_order_headers = self.load_jsonl_files('sales_order_headers')
        sales_order_items = self.load_jsonl_files('sales_order_items')
        delivery_headers = self.load_jsonl_files('outbound_delivery_headers')
        delivery_items = self.load_jsonl_files('outbound_delivery_items')
        billing_headers = self.load_jsonl_files('billing_document_headers')
        billing_items = self.load_jsonl_files('billing_document_items')
        journal_entries = self.load_jsonl_files('journal_entry_items_accounts_receivable')
        payments = self.load_jsonl_files('payments_accounts_receivable')
        products = self.load_jsonl_files('products')
        product_descriptions = self.load_jsonl_files('product_descriptions')
        plants = self.load_jsonl_files('plants')
        
        print(f"Loaded: {len(customers)} customers, {len(sales_order_headers)} sales orders, "
              f"{len(delivery_headers)} deliveries, {len(billing_headers)} invoices")
        
        # Build nodes and relationships
        self._add_customers(customers, addresses)
        self._add_products(products, product_descriptions)
        self._add_plants(plants)
        self._add_sales_orders(sales_order_headers, sales_order_items)
        self._add_deliveries(delivery_headers, delivery_items)
        self._add_invoices(billing_headers, billing_items)
        self._add_journal_entries(journal_entries)
        self._add_payments(payments)
        
        # Create cross-entity relationships
        self._link_deliveries_to_sales_orders()
        self._link_invoices_to_journal_entries()
        self._link_journal_entries_to_payments()
        
        print(f"Graph built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
        
        return self.graph
    
    def _add_customers(self, customers: List[Dict], addresses: List[Dict]):
        """Add customer nodes and their addresses."""
        for customer in customers:
            customer_id = customer.get('businessPartner') or customer.get('customer')
            if not customer_id:
                continue
                
            node_id = f"customer_{customer_id}"
            self.entities['customers'][customer_id] = customer
            
            self.graph.add_node(
                node_id,
                type='Customer',
                id=customer_id,
                name=customer.get('businessPartnerFullName', ''),
                category=customer.get('businessPartnerCategory', ''),
                is_blocked=customer.get('businessPartnerIsBlocked', False),
                data=customer
            )
        
        # Add addresses
        address_to_customer = {}
        for addr in addresses:
            addr_id = addr.get('addressId')
            bp = addr.get('businessPartner')
            if addr_id and bp:
                address_to_customer[addr_id] = bp
                self.entities['addresses'][addr_id] = addr
                
                addr_node_id = f"address_{addr_id}"
                self.graph.add_node(
                    addr_node_id,
                    type='Address',
                    id=addr_id,
                    city=addr.get('cityName', ''),
                    country=addr.get('country', ''),
                    postal_code=addr.get('postalCode', ''),
                    data=addr
                )
                
                # Link customer to address
                customer_node_id = f"customer_{bp}"
                if self.graph.has_node(customer_node_id):
                    self.graph.add_edge(
                        customer_node_id,
                        addr_node_id,
                        type='HAS_ADDRESS'
                    )
    
    def _add_products(self, products: List[Dict], descriptions: List[Dict]):
        """Add product nodes."""
        # Create description lookup
        desc_map = {d['product']: d.get('productDescription', '') 
                    for d in descriptions if 'product' in d}
        
        for product in products:
            product_id = product.get('product')
            if not product_id:
                continue
                
            node_id = f"product_{product_id}"
            self.entities['products'][product_id] = product
            
            self.graph.add_node(
                node_id,
                type='Product',
                id=product_id,
                description=desc_map.get(product_id, ''),
                product_type=product.get('productType', ''),
                product_group=product.get('productGroup', ''),
                base_unit=product.get('baseUnit', ''),
                data=product
            )
    
    def _add_plants(self, plants: List[Dict]):
        """Add plant nodes."""
        for plant in plants:
            plant_id = plant.get('plant')
            if not plant_id:
                continue
                
            node_id = f"plant_{plant_id}"
            self.entities['plants'][plant_id] = plant
            
            self.graph.add_node(
                node_id,
                type='Plant',
                id=plant_id,
                name=plant.get('plantName', ''),
                data=plant
            )
    
    def _add_sales_orders(self, headers: List[Dict], items: List[Dict]):
        """Add sales order nodes and items."""
        for order in headers:
            order_id = order.get('salesOrder')
            if not order_id:
                continue
                
            node_id = f"sales_order_{order_id}"
            self.entities['sales_orders'][order_id] = order
            
            self.graph.add_node(
                node_id,
                type='SalesOrder',
                id=order_id,
                total_amount=float(order.get('totalNetAmount', 0)),
                currency=order.get('transactionCurrency', ''),
                creation_date=order.get('creationDate', ''),
                delivery_status=order.get('overallDeliveryStatus', ''),
                billing_status=order.get('overallOrdReltdBillgStatus', ''),
                data=order
            )
            
            # Link to customer
            customer_id = order.get('soldToParty')
            if customer_id:
                customer_node = f"customer_{customer_id}"
                if self.graph.has_node(customer_node):
                    self.graph.add_edge(
                        customer_node,
                        node_id,
                        type='PLACED_ORDER'
                    )
        
        # Add sales order items
        for item in items:
            order_id = item.get('salesOrder')
            item_id = item.get('salesOrderItem')
            if not order_id or not item_id:
                continue
                
            item_node_id = f"sales_order_item_{order_id}_{item_id}"
            
            # Store in entities with composite key
            if order_id not in self.entities['sales_order_items']:
                self.entities['sales_order_items'][order_id] = {}
            self.entities['sales_order_items'][order_id][item_id] = item
            
            self.graph.add_node(
                item_node_id,
                type='SalesOrderItem',
                id=f"{order_id}-{item_id}",
                order_id=order_id,
                item_id=item_id,
                material=item.get('material', ''),
                quantity=float(item.get('requestedQuantity', 0)),
                amount=float(item.get('netAmount', 0)),
                plant=item.get('productionPlant', ''),
                data=item
            )
            
            # Link to sales order
            order_node = f"sales_order_{order_id}"
            if self.graph.has_node(order_node):
                self.graph.add_edge(
                    order_node,
                    item_node_id,
                    type='HAS_ITEM'
                )
            
            # Link to product
            material = item.get('material')
            if material:
                product_node = f"product_{material}"
                if self.graph.has_node(product_node):
                    self.graph.add_edge(
                        item_node_id,
                        product_node,
                        type='REFERS_TO_PRODUCT'
                    )
            
            # Link to plant
            plant = item.get('productionPlant')
            if plant:
                plant_node = f"plant_{plant}"
                if self.graph.has_node(plant_node):
                    self.graph.add_edge(
                        item_node_id,
                        plant_node,
                        type='PRODUCED_AT'
                    )
    
    def _add_deliveries(self, headers: List[Dict], items: List[Dict]):
        """Add delivery nodes and items."""
        for delivery in headers:
            delivery_id = delivery.get('deliveryDocument')
            if not delivery_id:
                continue
                
            node_id = f"delivery_{delivery_id}"
            self.entities['deliveries'][delivery_id] = delivery
            
            self.graph.add_node(
                node_id,
                type='Delivery',
                id=delivery_id,
                creation_date=delivery.get('creationDate', ''),
                shipping_point=delivery.get('shippingPoint', ''),
                goods_movement_status=delivery.get('overallGoodsMovementStatus', ''),
                picking_status=delivery.get('overallPickingStatus', ''),
                data=delivery
            )
        
        # Add delivery items and track relationships
        for item in items:
            delivery_id = item.get('deliveryDocument')
            item_id = item.get('deliveryDocumentItem')
            if not delivery_id or not item_id:
                continue
                
            item_node_id = f"delivery_item_{delivery_id}_{item_id}"
            
            # Store in entities
            if delivery_id not in self.entities['delivery_items']:
                self.entities['delivery_items'][delivery_id] = {}
            self.entities['delivery_items'][delivery_id][item_id] = item
            
            self.graph.add_node(
                item_node_id,
                type='DeliveryItem',
                id=f"{delivery_id}-{item_id}",
                delivery_id=delivery_id,
                item_id=item_id,
                quantity=float(item.get('actualDeliveryQuantity', 0)),
                plant=item.get('plant', ''),
                data=item
            )
            
            # Link to delivery
            delivery_node = f"delivery_{delivery_id}"
            if self.graph.has_node(delivery_node):
                self.graph.add_edge(
                    delivery_node,
                    item_node_id,
                    type='HAS_ITEM'
                )
            
            # Track relationship to sales order for later linking
            ref_order = item.get('referenceSdDocument')
            ref_item = item.get('referenceSdDocumentItem')
            if ref_order and ref_item:
                self.delivery_to_sales_order[item_node_id] = (ref_order, ref_item)
            
            # Link to plant
            plant = item.get('plant')
            if plant:
                plant_node = f"plant_{plant}"
                if self.graph.has_node(plant_node):
                    self.graph.add_edge(
                        item_node_id,
                        plant_node,
                        type='SHIPPED_FROM'
                    )
    
    def _add_invoices(self, headers: List[Dict], items: List[Dict]):
        """Add invoice nodes."""
        for invoice in headers:
            invoice_id = invoice.get('billingDocument')
            if not invoice_id:
                continue
                
            node_id = f"invoice_{invoice_id}"
            self.entities['invoices'][invoice_id] = invoice
            
            self.graph.add_node(
                node_id,
                type='Invoice',
                id=invoice_id,
                amount=float(invoice.get('totalNetAmount', 0)),
                currency=invoice.get('transactionCurrency', ''),
                creation_date=invoice.get('creationDate', ''),
                is_cancelled=invoice.get('billingDocumentIsCancelled', False),
                accounting_document=invoice.get('accountingDocument', ''),
                data=invoice
            )
            
            # Link to customer
            customer_id = invoice.get('soldToParty')
            if customer_id:
                customer_node = f"customer_{customer_id}"
                if self.graph.has_node(customer_node):
                    self.graph.add_edge(
                        customer_node,
                        node_id,
                        type='BILLED_TO'
                    )
            
            # Track accounting document for linking
            acct_doc = invoice.get('accountingDocument')
            if acct_doc:
                self.invoice_to_journal[acct_doc] = invoice_id
        
        # Add invoice items
        for item in items:
            invoice_id = item.get('billingDocument')
            item_id = item.get('billingDocumentItem')
            if not invoice_id or not item_id:
                continue
                
            # Store in entities
            if invoice_id not in self.entities['invoice_items']:
                self.entities['invoice_items'][invoice_id] = {}
            self.entities['invoice_items'][invoice_id][item_id] = item
    
    def _add_journal_entries(self, entries: List[Dict]):
        """Add journal entry nodes."""
        for entry in entries:
            acct_doc = entry.get('accountingDocument')
            item = entry.get('accountingDocumentItem')
            if not acct_doc or not item:
                continue
                
            entry_id = f"{acct_doc}_{item}"
            node_id = f"journal_{entry_id}"
            
            # Store in entities
            if acct_doc not in self.entities['journal_entries']:
                self.entities['journal_entries'][acct_doc] = {}
            self.entities['journal_entries'][acct_doc][item] = entry
            
            self.graph.add_node(
                node_id,
                type='JournalEntry',
                id=entry_id,
                accounting_document=acct_doc,
                item=item,
                amount=float(entry.get('amountInTransactionCurrency', 0)),
                currency=entry.get('transactionCurrency', ''),
                customer=entry.get('customer', ''),
                gl_account=entry.get('glAccount', ''),
                posting_date=entry.get('postingDate', ''),
                clearing_document=entry.get('clearingAccountingDocument', ''),
                data=entry
            )
            
            # Link to customer
            customer_id = entry.get('customer')
            if customer_id:
                customer_node = f"customer_{customer_id}"
                if self.graph.has_node(customer_node):
                    self.graph.add_edge(
                        node_id,
                        customer_node,
                        type='RELATES_TO_CUSTOMER'
                    )
            
            # Track for payment linking
            clearing_doc = entry.get('clearingAccountingDocument')
            if clearing_doc:
                if clearing_doc not in self.journal_to_payment:
                    self.journal_to_payment[clearing_doc] = []
                self.journal_to_payment[clearing_doc].append(node_id)
    
    def _add_payments(self, payments: List[Dict]):
        """Add payment nodes."""
        for payment in payments:
            acct_doc = payment.get('accountingDocument')
            if not acct_doc:
                continue
                
            node_id = f"payment_{acct_doc}"
            self.entities['payments'][acct_doc] = payment
            
            self.graph.add_node(
                node_id,
                type='Payment',
                id=acct_doc,
                amount=float(payment.get('amountInTransactionCurrency', 0)),
                currency=payment.get('transactionCurrency', ''),
                posting_date=payment.get('postingDate', ''),
                customer=payment.get('customer', ''),
                data=payment
            )
            
            # Link to customer
            customer_id = payment.get('customer')
            if customer_id:
                customer_node = f"customer_{customer_id}"
                if self.graph.has_node(customer_node):
                    self.graph.add_edge(
                        customer_node,
                        node_id,
                        type='MADE_PAYMENT'
                    )
    
    def _link_deliveries_to_sales_orders(self):
        """Create edges from delivery items to sales order items."""
        for delivery_item_node, (order_id, order_item) in self.delivery_to_sales_order.items():
            sales_order_item_node = f"sales_order_item_{order_id}_{order_item}"
            
            if self.graph.has_node(sales_order_item_node):
                self.graph.add_edge(
                    sales_order_item_node,
                    delivery_item_node,
                    type='FULFILLED_BY'
                )
                
                # Also link parent entities
                delivery_id = delivery_item_node.split('_')[2]
                delivery_node = f"delivery_{delivery_id}"
                sales_order_node = f"sales_order_{order_id}"
                
                if self.graph.has_node(delivery_node) and self.graph.has_node(sales_order_node):
                    # Check if edge doesn't already exist
                    if not self.graph.has_edge(sales_order_node, delivery_node):
                        self.graph.add_edge(
                            sales_order_node,
                            delivery_node,
                            type='FULFILLED_BY_DELIVERY'
                        )
    
    def _link_invoices_to_journal_entries(self):
        """Create edges from invoices to journal entries via accounting document."""
        for acct_doc, invoice_id in self.invoice_to_journal.items():
            invoice_node = f"invoice_{invoice_id}"
            
            # Find all journal entries with this accounting document
            if acct_doc in self.entities['journal_entries']:
                for item in self.entities['journal_entries'][acct_doc].keys():
                    journal_node = f"journal_{acct_doc}_{item}"
                    
                    if self.graph.has_node(invoice_node) and self.graph.has_node(journal_node):
                        self.graph.add_edge(
                            invoice_node,
                            journal_node,
                            type='POSTED_AS'
                        )
    
    def _link_journal_entries_to_payments(self):
        """Create edges from journal entries to payments via clearing document."""
        for clearing_doc, journal_nodes in self.journal_to_payment.items():
            payment_node = f"payment_{clearing_doc}"
            
            if self.graph.has_node(payment_node):
                for journal_node in journal_nodes:
                    if self.graph.has_node(journal_node):
                        self.graph.add_edge(
                            journal_node,
                            payment_node,
                            type='CLEARED_BY'
                        )
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the graph."""
        node_types = defaultdict(int)
        edge_types = defaultdict(int)
        
        for node, data in self.graph.nodes(data=True):
            node_types[data.get('type', 'Unknown')] += 1
        
        for u, v, data in self.graph.edges(data=True):
            edge_types[data.get('type', 'Unknown')] += 1
        
        return {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'node_types': dict(node_types),
            'edge_types': dict(edge_types),
            'is_directed': self.graph.is_directed()
        }
    
    def export_for_visualization(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Export graph data in a format suitable for frontend visualization."""
        nodes = []
        edges = []
        
        node_list = list(self.graph.nodes(data=True))
        if limit:
            node_list = node_list[:limit]
            
        node_ids = {node for node, _ in node_list}
        
        for node, data in node_list:
            # Create a clean node object
            node_obj = {
                'id': node,
                'type': data.get('type', 'Unknown'),
                'label': data.get('id', node),
                'name': data.get('name', ''),
            }
            
            # Add type-specific fields
            if data.get('type') == 'Customer':
                node_obj['details'] = {
                    'name': data.get('name', ''),
                    'is_blocked': data.get('is_blocked', False)
                }
            elif data.get('type') == 'SalesOrder':
                node_obj['details'] = {
                    'amount': data.get('total_amount', 0),
                    'currency': data.get('currency', ''),
                    'status': data.get('delivery_status', '')
                }
            elif data.get('type') == 'Invoice':
                node_obj['details'] = {
                    'amount': data.get('amount', 0),
                    'currency': data.get('currency', ''),
                    'is_cancelled': data.get('is_cancelled', False)
                }
            
            nodes.append(node_obj)
        
        for u, v, data in self.graph.edges(data=True):
            if u in node_ids and v in node_ids:
                edges.append({
                    'source': u,
                    'target': v,
                    'type': data.get('type', 'Unknown')
                })
        
        return {
            'nodes': nodes,
            'edges': edges
        }


# Example usage (DO NOT RUN - REFERENCE ONLY):
if __name__ == "__main__":
    print("=" * 60)
    print("⚠️  WARNING: This is a reference implementation")
    print("   Do not use in production!")
    print("   Use graph_builder.py instead")
    print("=" * 60)
