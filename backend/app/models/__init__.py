"""
Models package initialization - SQLAlchemy models
"""

from app.models.user import User
from app.models.role import Role, Permission
from app.models.category import Category
from app.models.brand import Brand
from app.models.supplier import Supplier
from app.models.product import Product, ProductVariant
from app.models.inventory import (
    StockLocation,
    InventoryLevel,
    InventoryMovement,
    StockAdjustment,
    LowStockAlert,
    MovementType
)
from app.models.garment import (
    SizeChart,
    Color,
    Fabric,
    Style,
    Collection,
    MeasurementSpec,
    GarmentImage,
    ProductFabric,
    SizeCategory,
    Region,
    Season
)
from app.models.order import (
    Order,
    OrderItem,
    PricingTier,
    PaymentTransaction,
    ShippingDetails,
    SalesChannel,
    OrderStatus,
    PaymentStatus,
    PaymentMethod,
    ShippingStatus,
    PricingTierType
)
from app.models.order_management import (
    OrderHistory,
    OrderNote,
    OrderFulfillment,
    InventoryReservation,
    OrderHistoryAction,
    FulfillmentStatus
)
from app.models.wholesale import (
    WholesaleCustomer,
    ContractPricing,
    CustomerType,
    CustomerStatus,
    PaymentTerms,
    CreditStatus
)
from app.models.pos import (
    CashierShift,
    CashDrawer,
    POSTransaction,
    ReturnExchange,
    ShiftStatus,
    CashDrawerStatus,
    POSTransactionType,
    ReturnReason
)
from app.models.ecommerce import (
    ShoppingCart,
    CartItem,
    Wishlist,
    WishlistItem,
    ProductReview,
    PromoCode,
    PromoCodeUsage,
    CartStatus,
    PromoCodeType,
    PromoCodeStatus,
    ReviewStatus
)
from app.models.pricing import (
    PricingRule,
    PricingRuleProduct,
    PricingRuleCategory,
    PricingRuleCustomer,
    ChannelPrice,
    VolumeDiscount,
    Promotion,
    PromotionUsage,
    PriceHistory,
    CompetitorPrice,
    CustomerPricingTier,
    PricingRuleType,
    DiscountType,
    PricingRuleStatus,
    CustomerTier,
    PriceChangeReason
)

__all__ = [
    "User",
    "Role",
    "Permission",
    "Category",
    "Brand",
    "Supplier",
    "Product",
    "ProductVariant",
    "StockLocation",
    "InventoryLevel",
    "InventoryMovement",
    "StockAdjustment",
    "LowStockAlert",
    "MovementType",
    "SizeChart",
    "Color",
    "Fabric",
    "Style",
    "Collection",
    "MeasurementSpec",
    "GarmentImage",
    "ProductFabric",
    "SizeCategory",
    "Region",
    "Season",
    "Order",
    "OrderItem",
    "PricingTier",
    "PaymentTransaction",
    "ShippingDetails",
    "SalesChannel",
    "OrderStatus",
    "PaymentStatus",
    "PaymentMethod",
    "ShippingStatus",
    "PricingTierType",
    "OrderHistory",
    "OrderNote",
    "OrderFulfillment",
    "InventoryReservation",
    "OrderHistoryAction",
    "FulfillmentStatus",
    "WholesaleCustomer",
    "ContractPricing",
    "CustomerType",
    "CustomerStatus",
    "PaymentTerms",
    "CreditStatus",
    "CashierShift",
    "CashDrawer",
    "POSTransaction",
    "ReturnExchange",
    "ShiftStatus",
    "CashDrawerStatus",
    "POSTransactionType",
    "ReturnReason",
    "ShoppingCart",
    "CartItem",
    "Wishlist",
    "WishlistItem",
    "ProductReview",
    "PromoCode",
    "PromoCodeUsage",
    "CartStatus",
    "PromoCodeType",
    "PromoCodeStatus",
    "ReviewStatus",
    # Pricing Engine
    "PricingRule",
    "PricingRuleProduct",
    "PricingRuleCategory",
    "PricingRuleCustomer",
    "ChannelPrice",
    "VolumeDiscount",
    "Promotion",
    "PromotionUsage",
    "PriceHistory",
    "CompetitorPrice",
    "CustomerPricingTier",
    "PricingRuleType",
    "DiscountType",
    "PricingRuleStatus",
    "CustomerTier",
    "PriceChangeReason",
]
