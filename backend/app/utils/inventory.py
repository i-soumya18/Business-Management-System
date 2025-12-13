"""
Inventory Utilities

Utility functions for SKU generation, barcode generation, slug creation, etc.
"""

import random
import string
from typing import Optional
from datetime import datetime


def generate_sku(
    category_code: str,
    brand_code: Optional[str] = None,
    product_code: Optional[str] = None,
    variant_code: Optional[str] = None
) -> str:
    """
    Generate a SKU based on category, brand, product, and variant
    
    Format: CAT-BRN-PROD-VAR
    Example: CLO-NIK-TS01-BLK-M
    
    Args:
        category_code: 3-letter category code (e.g., 'CLO' for clothing)
        brand_code: 3-letter brand code (e.g., 'NIK' for Nike)
        product_code: Product code (e.g., 'TS01')
        variant_code: Variant code (e.g., 'BLK-M' for black medium)
        
    Returns:
        Generated SKU string
    """
    parts = [category_code.upper()]
    
    if brand_code:
        parts.append(brand_code.upper())
    
    if product_code:
        parts.append(product_code.upper())
    
    if variant_code:
        parts.append(variant_code.upper())
    
    return "-".join(parts)


def generate_random_sku(prefix: str = "PRD", length: int = 8) -> str:
    """
    Generate a random SKU with prefix
    
    Format: PREFIX-RANDOM
    Example: PRD-A8K9D2F7
    
    Args:
        prefix: SKU prefix
        length: Length of random part
        
    Returns:
        Random SKU string
    """
    random_part = ''.join(
        random.choices(string.ascii_uppercase + string.digits, k=length)
    )
    return f"{prefix.upper()}-{random_part}"


def generate_barcode_ean13() -> str:
    """
    Generate a valid EAN-13 barcode with check digit
    
    Returns:
        13-digit EAN-13 barcode string
    """
    # Generate 12 random digits
    code = ''.join(random.choices(string.digits, k=12))
    
    # Calculate check digit
    odd_sum = sum(int(code[i]) for i in range(0, 12, 2))
    even_sum = sum(int(code[i]) for i in range(1, 12, 2))
    total = odd_sum + (even_sum * 3)
    check_digit = (10 - (total % 10)) % 10
    
    return code + str(check_digit)


def generate_barcode_ean8() -> str:
    """
    Generate a valid EAN-8 barcode with check digit
    
    Returns:
        8-digit EAN-8 barcode string
    """
    # Generate 7 random digits
    code = ''.join(random.choices(string.digits, k=7))
    
    # Calculate check digit
    odd_sum = sum(int(code[i]) for i in range(1, 7, 2))
    even_sum = sum(int(code[i]) for i in range(0, 7, 2))
    total = (odd_sum * 3) + even_sum
    check_digit = (10 - (total % 10)) % 10
    
    return code + str(check_digit)


def validate_ean13(barcode: str) -> bool:
    """
    Validate an EAN-13 barcode check digit
    
    Args:
        barcode: 13-digit barcode string
        
    Returns:
        True if valid, False otherwise
    """
    if not barcode or len(barcode) != 13 or not barcode.isdigit():
        return False
    
    code = barcode[:12]
    check_digit = int(barcode[12])
    
    odd_sum = sum(int(code[i]) for i in range(0, 12, 2))
    even_sum = sum(int(code[i]) for i in range(1, 12, 2))
    total = odd_sum + (even_sum * 3)
    calculated_check = (10 - (total % 10)) % 10
    
    return calculated_check == check_digit


def create_slug(text: str, max_length: int = 100) -> str:
    """
    Create a URL-friendly slug from text
    
    Args:
        text: Input text
        max_length: Maximum slug length
        
    Returns:
        URL-friendly slug
    """
    # Convert to lowercase
    slug = text.lower()
    
    # Replace spaces and underscores with hyphens
    slug = slug.replace(' ', '-').replace('_', '-')
    
    # Remove special characters
    allowed = string.ascii_lowercase + string.digits + '-'
    slug = ''.join(c for c in slug if c in allowed)
    
    # Remove multiple consecutive hyphens
    while '--' in slug:
        slug = slug.replace('--', '-')
    
    # Trim hyphens from ends
    slug = slug.strip('-')
    
    # Limit length
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip('-')
    
    return slug


def generate_adjustment_number(count: int) -> str:
    """
    Generate a stock adjustment number
    
    Format: ADJ-YYYYMMDD-####
    Example: ADJ-20240115-0001
    
    Args:
        count: Sequential count for the day
        
    Returns:
        Adjustment number string
    """
    date_str = datetime.utcnow().strftime('%Y%m%d')
    return f"ADJ-{date_str}-{count:04d}"


def generate_transfer_number(count: int) -> str:
    """
    Generate a stock transfer number
    
    Format: TRN-YYYYMMDD-####
    Example: TRN-20240115-0001
    
    Args:
        count: Sequential count for the day
        
    Returns:
        Transfer number string
    """
    date_str = datetime.utcnow().strftime('%Y%m%d')
    return f"TRN-{date_str}-{count:04d}"


def generate_variant_code(
    size: Optional[str] = None,
    color: Optional[str] = None,
    style: Optional[str] = None
) -> str:
    """
    Generate a variant code from attributes
    
    Format: SIZE-COLOR-STYLE
    Example: M-BLK-SLM (Medium, Black, Slim)
    
    Args:
        size: Size attribute
        color: Color attribute
        style: Style attribute
        
    Returns:
        Variant code string
    """
    parts = []
    
    if size:
        parts.append(size.upper())
    
    if color:
        # Use first 3 letters of color
        color_code = color.upper()[:3]
        parts.append(color_code)
    
    if style:
        # Use first 3 letters of style
        style_code = style.upper()[:3]
        parts.append(style_code)
    
    return "-".join(parts) if parts else "STD"


def format_currency(amount: float, currency: str = "INR") -> str:
    """
    Format amount as currency string
    
    Args:
        amount: Numeric amount
        currency: Currency code
        
    Returns:
        Formatted currency string
    """
    if currency == "INR":
        return f"₹{amount:,.2f}"
    elif currency == "USD":
        return f"${amount:,.2f}"
    elif currency == "EUR":
        return f"€{amount:,.2f}"
    else:
        return f"{currency} {amount:,.2f}"


def calculate_stock_value(
    quantity: int,
    unit_cost: float
) -> float:
    """
    Calculate total stock value
    
    Args:
        quantity: Quantity in stock
        unit_cost: Cost per unit
        
    Returns:
        Total value
    """
    return quantity * unit_cost


def calculate_reorder_quantity(
    current_stock: int,
    reorder_point: int,
    max_stock_level: Optional[int] = None,
    avg_daily_usage: Optional[int] = None,
    lead_time_days: Optional[int] = None
) -> int:
    """
    Calculate recommended reorder quantity
    
    Args:
        current_stock: Current stock level
        reorder_point: Reorder point threshold
        max_stock_level: Maximum stock level
        avg_daily_usage: Average daily usage
        lead_time_days: Lead time in days
        
    Returns:
        Recommended order quantity
    """
    if max_stock_level:
        # Order up to max level
        return max(0, max_stock_level - current_stock)
    
    if avg_daily_usage and lead_time_days:
        # Economic order quantity approach
        lead_time_demand = avg_daily_usage * lead_time_days
        safety_stock = reorder_point - lead_time_demand
        return lead_time_demand + safety_stock
    
    # Default: double the difference from reorder point
    return max(0, (reorder_point * 2) - current_stock)


def normalize_sku(sku: str) -> str:
    """
    Normalize SKU to standard format (uppercase, no extra spaces)
    
    Args:
        sku: Input SKU
        
    Returns:
        Normalized SKU
    """
    return sku.strip().upper()


def normalize_barcode(barcode: str) -> str:
    """
    Normalize barcode to standard format (uppercase, no spaces)
    
    Args:
        barcode: Input barcode
        
    Returns:
        Normalized barcode
    """
    return barcode.strip().upper().replace(' ', '')
