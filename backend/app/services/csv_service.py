"""
CSV Import/Export Service

Service for bulk importing and exporting inventory data.
"""

import csv
import io
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID

from fastapi import UploadFile, HTTPException, status


class CSVImportExportService:
    """Service for CSV operations"""
    
    @staticmethod
    async def export_products_to_csv(products: List[Dict[str, Any]]) -> str:
        """
        Export products to CSV format
        
        Args:
            products: List of product dictionaries
            
        Returns:
            CSV string
        """
        if not products:
            return ""
        
        output = io.StringIO()
        fieldnames = [
            'sku', 'name', 'description', 'category_id', 'brand_id',
            'supplier_id', 'unit_cost', 'wholesale_price', 'retail_price',
            'fabric_type', 'fabric_composition', 'care_instructions',
            'season', 'collection', 'is_active'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for product in products:
            row = {field: product.get(field, '') for field in fieldnames}
            writer.writerow(row)
        
        return output.getvalue()
    
    @staticmethod
    async def export_variants_to_csv(variants: List[Dict[str, Any]]) -> str:
        """
        Export product variants to CSV format
        
        Args:
            variants: List of variant dictionaries
            
        Returns:
            CSV string
        """
        if not variants:
            return ""
        
        output = io.StringIO()
        fieldnames = [
            'sku', 'barcode', 'product_id', 'size', 'color', 'style',
            'unit_cost', 'wholesale_price', 'retail_price', 'sale_price',
            'weight', 'length', 'width', 'height', 'is_active'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for variant in variants:
            row = {field: variant.get(field, '') for field in fieldnames}
            writer.writerow(row)
        
        return output.getvalue()
    
    @staticmethod
    async def export_inventory_to_csv(inventory_levels: List[Dict[str, Any]]) -> str:
        """
        Export inventory levels to CSV format
        
        Args:
            inventory_levels: List of inventory level dictionaries
            
        Returns:
            CSV string
        """
        if not inventory_levels:
            return ""
        
        output = io.StringIO()
        fieldnames = [
            'variant_id', 'location_id', 'quantity_on_hand', 'quantity_reserved',
            'quantity_available', 'reorder_point', 'reorder_quantity',
            'max_stock_level', 'last_counted_at'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for level in inventory_levels:
            row = {field: level.get(field, '') for field in fieldnames}
            writer.writerow(row)
        
        return output.getvalue()
    
    @staticmethod
    async def parse_products_csv(file: UploadFile) -> List[Dict[str, Any]]:
        """
        Parse products from CSV file
        
        Args:
            file: Uploaded CSV file
            
        Returns:
            List of product dictionaries
            
        Raises:
            HTTPException: If CSV is invalid
        """
        try:
            content = await file.read()
            decoded = content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(decoded))
            
            products = []
            for row in csv_reader:
                # Convert empty strings to None
                product = {
                    k: (v if v != '' else None)
                    for k, v in row.items()
                }
                
                # Convert boolean strings
                if 'is_active' in product:
                    product['is_active'] = product['is_active'].lower() in ('true', '1', 'yes')
                
                # Convert numeric fields
                for field in ['unit_cost', 'wholesale_price', 'retail_price']:
                    if field in product and product[field]:
                        try:
                            product[field] = float(product[field])
                        except ValueError:
                            product[field] = None
                
                products.append(product)
            
            return products
        
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid CSV file: {str(e)}"
            )
    
    @staticmethod
    async def parse_variants_csv(file: UploadFile) -> List[Dict[str, Any]]:
        """
        Parse product variants from CSV file
        
        Args:
            file: Uploaded CSV file
            
        Returns:
            List of variant dictionaries
            
        Raises:
            HTTPException: If CSV is invalid
        """
        try:
            content = await file.read()
            decoded = content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(decoded))
            
            variants = []
            for row in csv_reader:
                # Convert empty strings to None
                variant = {
                    k: (v if v != '' else None)
                    for k, v in row.items()
                }
                
                # Convert boolean strings
                if 'is_active' in variant:
                    variant['is_active'] = variant['is_active'].lower() in ('true', '1', 'yes')
                
                # Convert numeric fields
                numeric_fields = [
                    'unit_cost', 'wholesale_price', 'retail_price', 'sale_price',
                    'weight', 'length', 'width', 'height'
                ]
                for field in numeric_fields:
                    if field in variant and variant[field]:
                        try:
                            variant[field] = float(variant[field])
                        except ValueError:
                            variant[field] = None
                
                variants.append(variant)
            
            return variants
        
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid CSV file: {str(e)}"
            )
    
    @staticmethod
    async def parse_inventory_csv(file: UploadFile) -> List[Dict[str, Any]]:
        """
        Parse inventory levels from CSV file
        
        Args:
            file: Uploaded CSV file
            
        Returns:
            List of inventory level dictionaries
            
        Raises:
            HTTPException: If CSV is invalid
        """
        try:
            content = await file.read()
            decoded = content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(decoded))
            
            levels = []
            for row in csv_reader:
                # Convert empty strings to None
                level = {
                    k: (v if v != '' else None)
                    for k, v in row.items()
                }
                
                # Convert numeric fields
                numeric_fields = [
                    'quantity_on_hand', 'quantity_reserved', 'quantity_available',
                    'reorder_point', 'reorder_quantity', 'max_stock_level'
                ]
                for field in numeric_fields:
                    if field in level and level[field]:
                        try:
                            level[field] = int(level[field])
                        except ValueError:
                            level[field] = None
                
                levels.append(level)
            
            return levels
        
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid CSV file: {str(e)}"
            )
    
    @staticmethod
    def validate_csv_headers(file_content: str, expected_headers: List[str]) -> bool:
        """
        Validate CSV headers
        
        Args:
            file_content: CSV file content
            expected_headers: List of expected header names
            
        Returns:
            True if headers are valid
        """
        csv_reader = csv.DictReader(io.StringIO(file_content))
        headers = csv_reader.fieldnames or []
        
        missing_headers = set(expected_headers) - set(headers)
        return len(missing_headers) == 0
