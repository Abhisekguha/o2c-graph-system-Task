import json
import os
from typing import Dict, List, Any
import networkx as nx
from collections import defaultdict

class DataLoader:
    """Load and parse JSONL data files from SAP O2C dataset"""
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.entities = {}
        
    def load_jsonl(self, folder: str) -> List[Dict]:
        """Load all JSONL files from a folder"""
        folder_path = os.path.join(self.data_path, folder)
        data = []
        
        if not os.path.exists(folder_path):
            return data
            
        for filename in os.listdir(folder_path):
            if filename.endswith('.jsonl'):
                file_path = os.path.join(folder_path, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            data.append(json.loads(line))
        return data
    
    def load_all_entities(self):
        """Load all entity types from the dataset"""
        self.entities = {
            'sales_order_headers': self.load_jsonl('sales_order_headers'),
            'sales_order_items': self.load_jsonl('sales_order_items'),
            'sales_order_schedule_lines': self.load_jsonl('sales_order_schedule_lines'),
            'outbound_delivery_headers': self.load_jsonl('outbound_delivery_headers'),
            'outbound_delivery_items': self.load_jsonl('outbound_delivery_items'),
            'billing_document_headers': self.load_jsonl('billing_document_headers'),
            'billing_document_items': self.load_jsonl('billing_document_items'),
            'billing_document_cancellations': self.load_jsonl('billing_document_cancellations'),
            'journal_entry_items_accounts_receivable': self.load_jsonl('journal_entry_items_accounts_receivable'),
            'payments_accounts_receivable': self.load_jsonl('payments_accounts_receivable'),
            'business_partners': self.load_jsonl('business_partners'),
            'business_partner_addresses': self.load_jsonl('business_partner_addresses'),
            'customer_company_assignments': self.load_jsonl('customer_company_assignments'),
            'customer_sales_area_assignments': self.load_jsonl('customer_sales_area_assignments'),
            'products': self.load_jsonl('products'),
            'product_descriptions': self.load_jsonl('product_descriptions'),
            'product_plants': self.load_jsonl('product_plants'),
            'product_storage_locations': self.load_jsonl('product_storage_locations'),
            'plants': self.load_jsonl('plants'),
        }
        return self.entities
    
    def get_entity_counts(self) -> Dict[str, int]:
        """Get count of records for each entity type"""
        return {k: len(v) for k, v in self.entities.items()}
