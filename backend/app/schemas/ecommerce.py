"""
E-Commerce Schemas

Pydantic schemas for e-commerce operations including shopping cart, wishlist,
product reviews, and promotional codes.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models.ecommerce import (
    CartStatus,
    PromoCodeType,
    PromoCodeStatus,
    ReviewStatus
)


# ==================== Shopping Cart Schemas ====================

class CartItemBase(BaseModel):
    """Base schema for cart items"""
    product_variant_id: UUID
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")


class CartItemCreate(CartItemBase):
    """Schema for adding item to cart"""
    pass


class CartItemUpdate(BaseModel):
    """Schema for updating cart item"""
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")


class CartItemResponse(CartItemBase):
    """Schema for cart item response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    cart_id: UUID
    unit_price: Decimal
    subtotal: Decimal
    added_at: datetime
    updated_at: datetime


class ShoppingCartSummary(BaseModel):
    """Summary schema for shopping cart"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: Optional[UUID]
    session_id: Optional[str]
    status: CartStatus
    item_count: int
    subtotal: Decimal
    created_at: datetime
    last_activity_at: datetime


class ShoppingCartResponse(ShoppingCartSummary):
    """Detailed schema for shopping cart response"""
    items: List[CartItemResponse]
    order_id: Optional[UUID]
    converted_at: Optional[datetime]


class AddToCartRequest(BaseModel):
    """Schema for adding items to cart"""
    product_variant_id: UUID
    quantity: int = Field(default=1, gt=0)


class UpdateCartItemRequest(BaseModel):
    """Schema for updating cart item quantity"""
    quantity: int = Field(..., gt=0)


class ApplyPromoCodeRequest(BaseModel):
    """Schema for applying promo code to cart"""
    promo_code: str = Field(..., max_length=50)


# ==================== Wishlist Schemas ====================

class WishlistItemBase(BaseModel):
    """Base schema for wishlist items"""
    product_variant_id: UUID
    priority: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None


class WishlistItemCreate(WishlistItemBase):
    """Schema for adding item to wishlist"""
    pass


class WishlistItemResponse(WishlistItemBase):
    """Schema for wishlist item response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    wishlist_id: UUID
    added_at: datetime


class WishlistBase(BaseModel):
    """Base schema for wishlist"""
    name: str = Field(default="My Wishlist", max_length=100)
    is_public: bool = False


class WishlistCreate(WishlistBase):
    """Schema for creating a wishlist"""
    pass


class WishlistUpdate(BaseModel):
    """Schema for updating a wishlist"""
    name: Optional[str] = Field(None, max_length=100)
    is_public: Optional[bool] = None


class WishlistResponse(WishlistBase):
    """Schema for wishlist response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    items: List[WishlistItemResponse]
    created_at: datetime
    updated_at: datetime


class WishlistSummary(BaseModel):
    """Summary schema for wishlist"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    is_public: bool
    item_count: int
    created_at: datetime


# ==================== Product Review Schemas ====================

class ProductReviewBase(BaseModel):
    """Base schema for product review"""
    product_variant_id: UUID
    rating: int = Field(..., ge=1, le=5, description="Rating must be between 1 and 5")
    title: Optional[str] = Field(None, max_length=200)
    review_text: Optional[str] = None


class ProductReviewCreate(ProductReviewBase):
    """Schema for creating a product review"""
    order_id: Optional[UUID] = Field(
        None,
        description="Order ID for verified purchase"
    )


class ProductReviewUpdate(BaseModel):
    """Schema for updating a product review"""
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, max_length=200)
    review_text: Optional[str] = None


class ProductReviewResponse(ProductReviewBase):
    """Schema for product review response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    order_id: Optional[UUID]
    status: ReviewStatus
    is_verified_purchase: bool
    helpful_count: int
    not_helpful_count: int
    created_at: datetime
    updated_at: datetime


class ProductReviewModeration(BaseModel):
    """Schema for moderating a review"""
    status: ReviewStatus
    moderator_notes: Optional[str] = None


class ReviewHelpfulnessVote(BaseModel):
    """Schema for voting on review helpfulness"""
    is_helpful: bool


class ProductReviewStats(BaseModel):
    """Schema for product review statistics"""
    total_reviews: int
    average_rating: Decimal
    rating_distribution: Dict[int, int]  # {1: count, 2: count, ...}
    verified_purchase_count: int


# ==================== Promotional Code Schemas ====================

class PromoCodeBase(BaseModel):
    """Base schema for promotional code"""
    code: str = Field(..., max_length=50)
    description: Optional[str] = None
    promo_type: PromoCodeType
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    discount_amount: Optional[Decimal] = Field(None, ge=0)
    minimum_order_value: Optional[Decimal] = Field(None, ge=0)
    maximum_discount_amount: Optional[Decimal] = Field(None, ge=0)
    usage_limit: Optional[int] = Field(None, gt=0)
    usage_per_customer: Optional[int] = Field(None, gt=0)
    valid_from: datetime
    valid_until: datetime
    new_customers_only: bool = False


class PromoCodeCreate(PromoCodeBase):
    """Schema for creating a promotional code"""
    applicable_categories: Optional[List[UUID]] = None
    applicable_products: Optional[List[UUID]] = None
    excluded_products: Optional[List[UUID]] = None
    customer_emails: Optional[List[str]] = None
    
    @field_validator('valid_until')
    @classmethod
    def validate_dates(cls, v, info):
        """Validate that valid_until is after valid_from"""
        if 'valid_from' in info.data and v <= info.data['valid_from']:
            raise ValueError("valid_until must be after valid_from")
        return v
    
    @field_validator('discount_percentage', 'discount_amount')
    @classmethod
    def validate_discount(cls, v, info):
        """Validate that appropriate discount field is set based on type"""
        promo_type = info.data.get('promo_type')
        field_name = info.field_name
        
        if promo_type == PromoCodeType.PERCENTAGE and field_name == 'discount_percentage' and v is None:
            raise ValueError("discount_percentage required for PERCENTAGE type")
        if promo_type == PromoCodeType.FIXED_AMOUNT and field_name == 'discount_amount' and v is None:
            raise ValueError("discount_amount required for FIXED_AMOUNT type")
        
        return v


class PromoCodeUpdate(BaseModel):
    """Schema for updating a promotional code"""
    description: Optional[str] = None
    status: Optional[PromoCodeStatus] = None
    usage_limit: Optional[int] = Field(None, gt=0)
    valid_until: Optional[datetime] = None


class PromoCodeResponse(PromoCodeBase):
    """Schema for promotional code response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    status: PromoCodeStatus
    current_usage_count: int
    applicable_categories: Optional[dict]
    applicable_products: Optional[dict]
    excluded_products: Optional[dict]
    customer_emails: Optional[dict]
    created_at: datetime
    updated_at: datetime


class PromoCodeValidation(BaseModel):
    """Schema for promo code validation result"""
    is_valid: bool
    promo_code: Optional[PromoCodeResponse] = None
    discount_amount: Optional[Decimal] = None
    message: Optional[str] = None


class PromoCodeUsageResponse(BaseModel):
    """Schema for promo code usage response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    promo_code_id: UUID
    user_id: Optional[UUID]
    order_id: UUID
    discount_amount: Decimal
    used_at: datetime


# ==================== Checkout Schemas ====================

class CheckoutItemRequest(BaseModel):
    """Schema for checkout item"""
    product_variant_id: UUID
    quantity: int = Field(..., gt=0)


class CheckoutRequest(BaseModel):
    """Schema for checkout request"""
    cart_id: Optional[UUID] = Field(
        None,
        description="Cart ID to checkout (if using existing cart)"
    )
    items: Optional[List[CheckoutItemRequest]] = Field(
        None,
        description="Items to checkout (if not using cart)"
    )
    promo_code: Optional[str] = None
    
    # Shipping Information
    shipping_address_line1: str
    shipping_address_line2: Optional[str] = None
    shipping_city: str
    shipping_state: str
    shipping_postal_code: str
    shipping_country: str
    
    # Billing Information (if different)
    billing_same_as_shipping: bool = True
    billing_address_line1: Optional[str] = None
    billing_address_line2: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    billing_postal_code: Optional[str] = None
    billing_country: Optional[str] = None
    
    # Payment
    payment_method: str = Field(..., description="Payment method (stripe, razorpay, etc.)")
    
    # Customer Notes
    notes: Optional[str] = None
    
    @field_validator('items', 'cart_id')
    @classmethod
    def validate_checkout_source(cls, v, info):
        """Validate that either cart_id or items is provided"""
        field_name = info.field_name
        
        if field_name == 'items':
            cart_id = info.data.get('cart_id')
            if not cart_id and not v:
                raise ValueError("Either cart_id or items must be provided")
            if cart_id and v:
                raise ValueError("Cannot provide both cart_id and items")
        
        return v


class CheckoutResponse(BaseModel):
    """Schema for checkout response"""
    order_id: UUID
    order_number: str
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    shipping_cost: Decimal
    total: Decimal
    payment_status: str
    payment_intent_id: Optional[str] = None
    created_at: datetime


# ==================== Order Tracking Schemas ====================

class OrderTrackingResponse(BaseModel):
    """Schema for order tracking response"""
    model_config = ConfigDict(from_attributes=True)
    
    order_id: UUID
    order_number: str
    status: str
    payment_status: str
    shipping_status: Optional[str]
    tracking_number: Optional[str]
    estimated_delivery: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# ==================== Abandoned Cart Schemas ====================

class AbandonedCartInfo(BaseModel):
    """Schema for abandoned cart information"""
    cart_id: UUID
    user_id: Optional[UUID]
    email: Optional[str]
    item_count: int
    cart_value: Decimal
    last_activity_at: datetime
    days_abandoned: int


class AbandonedCartRecovery(BaseModel):
    """Schema for abandoned cart recovery action"""
    cart_id: UUID
    recovery_email_sent: bool
    recovery_discount_code: Optional[str]


# ==================== Product Catalog Schemas ====================

class ProductCatalogFilter(BaseModel):
    """Schema for product catalog filtering"""
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    min_price: Optional[Decimal] = Field(None, ge=0)
    max_price: Optional[Decimal] = Field(None, ge=0)
    size: Optional[str] = None
    color: Optional[str] = None
    in_stock_only: bool = True
    rating_min: Optional[int] = Field(None, ge=1, le=5)
    sort_by: Optional[str] = Field(
        default="created_at",
        description="Sort field (price, rating, created_at, name)"
    )
    sort_order: Optional[str] = Field(
        default="desc",
        pattern="^(asc|desc)$"
    )


class ProductCatalogItem(BaseModel):
    """Schema for product in catalog"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    description: Optional[str]
    price: Decimal
    image_url: Optional[str]
    average_rating: Optional[Decimal]
    review_count: int
    in_stock: bool


# ==================== Search Schemas ====================

class ProductSearchRequest(BaseModel):
    """Schema for product search request"""
    query: str = Field(..., min_length=2)
    filters: Optional[ProductCatalogFilter] = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class ProductSearchResponse(BaseModel):
    """Schema for product search response"""
    total: int
    results: List[ProductCatalogItem]
    skip: int
    limit: int
