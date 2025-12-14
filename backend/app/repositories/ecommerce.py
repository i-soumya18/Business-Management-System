"""
E-Commerce Repository

Data access layer for e-commerce operations including shopping cart, wishlist,
product reviews, and promotional codes.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ecommerce import (
    ShoppingCart,
    CartItem,
    Wishlist,
    WishlistItem,
    ProductReview,
    PromoCode,
    PromoCodeUsage,
    CartStatus,
    PromoCodeStatus,
    ReviewStatus
)
from app.repositories.base import BaseRepository


class ShoppingCartRepository(BaseRepository[ShoppingCart]):
    """Repository for shopping cart operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(ShoppingCart, db)
    
    async def get_active_cart_by_user(self, user_id: UUID) -> Optional[ShoppingCart]:
        """Get active cart for a user"""
        result = await self.db.execute(
            select(ShoppingCart)
            .where(
                and_(
                    ShoppingCart.user_id == user_id,
                    ShoppingCart.status == CartStatus.ACTIVE
                )
            )
            .options(selectinload(ShoppingCart.items))
        )
        return result.scalar_one_or_none()
    
    async def get_cart_by_session(self, session_id: str) -> Optional[ShoppingCart]:
        """Get cart by session ID (for guest users)"""
        result = await self.db.execute(
            select(ShoppingCart)
            .where(
                and_(
                    ShoppingCart.session_id == session_id,
                    ShoppingCart.status == CartStatus.ACTIVE
                )
            )
            .options(selectinload(ShoppingCart.items))
        )
        return result.scalar_one_or_none()
    
    async def get_abandoned_carts(
        self,
        days_abandoned: int = 1,
        skip: int = 0,
        limit: int = 100
    ) -> List[ShoppingCart]:
        """Get abandoned carts (no activity for specified days)"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_abandoned)
        
        result = await self.db.execute(
            select(ShoppingCart)
            .where(
                and_(
                    ShoppingCart.status == CartStatus.ACTIVE,
                    ShoppingCart.last_activity_at < cutoff_date
                )
            )
            .options(selectinload(ShoppingCart.items))
            .order_by(ShoppingCart.last_activity_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def mark_as_converted(self, cart_id: UUID, order_id: UUID) -> ShoppingCart:
        """Mark cart as converted to order"""
        cart = await self.get(cart_id)
        if not cart:
            raise ValueError(f"Cart {cart_id} not found")
        
        cart.status = CartStatus.CONVERTED
        cart.order_id = order_id
        cart.converted_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(cart)
        return cart


class CartItemRepository(BaseRepository[CartItem]):
    """Repository for cart item operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(CartItem, db)
    
    async def get_by_cart_and_variant(
        self,
        cart_id: UUID,
        product_variant_id: UUID
    ) -> Optional[CartItem]:
        """Get cart item by cart and product variant"""
        result = await self.db.execute(
            select(CartItem).where(
                and_(
                    CartItem.cart_id == cart_id,
                    CartItem.product_variant_id == product_variant_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def clear_cart(self, cart_id: UUID) -> None:
        """Remove all items from cart"""
        await self.db.execute(
            select(CartItem).where(CartItem.cart_id == cart_id)
        )
        await self.db.commit()


class WishlistRepository(BaseRepository[Wishlist]):
    """Repository for wishlist operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Wishlist, db)
    
    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Wishlist]:
        """Get all wishlists for a user"""
        result = await self.db.execute(
            select(Wishlist)
            .where(Wishlist.user_id == user_id)
            .options(selectinload(Wishlist.items))
            .order_by(Wishlist.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_default_wishlist(self, user_id: UUID) -> Optional[Wishlist]:
        """Get or create default wishlist for user"""
        result = await self.db.execute(
            select(Wishlist)
            .where(
                and_(
                    Wishlist.user_id == user_id,
                    Wishlist.name == "My Wishlist"
                )
            )
            .options(selectinload(Wishlist.items))
        )
        wishlist = result.scalar_one_or_none()
        
        if not wishlist:
            wishlist = Wishlist(
                user_id=user_id,
                name="My Wishlist",
                is_public=False
            )
            self.db.add(wishlist)
            await self.db.commit()
            await self.db.refresh(wishlist)
        
        return wishlist


class WishlistItemRepository(BaseRepository[WishlistItem]):
    """Repository for wishlist item operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(WishlistItem, db)
    
    async def get_by_wishlist_and_variant(
        self,
        wishlist_id: UUID,
        product_variant_id: UUID
    ) -> Optional[WishlistItem]:
        """Get wishlist item by wishlist and product variant"""
        result = await self.db.execute(
            select(WishlistItem).where(
                and_(
                    WishlistItem.wishlist_id == wishlist_id,
                    WishlistItem.product_variant_id == product_variant_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_wishlist(
        self,
        wishlist_id: UUID
    ) -> List[WishlistItem]:
        """Get all items in a wishlist"""
        result = await self.db.execute(
            select(WishlistItem)
            .where(WishlistItem.wishlist_id == wishlist_id)
            .order_by(WishlistItem.priority.asc().nullslast(), WishlistItem.added_at.desc())
        )
        return list(result.scalars().all())


class ProductReviewRepository(BaseRepository[ProductReview]):
    """Repository for product review operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(ProductReview, db)
    
    async def get_by_product(
        self,
        product_variant_id: UUID,
        status: Optional[ReviewStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProductReview]:
        """Get reviews for a product"""
        query = select(ProductReview).where(
            ProductReview.product_variant_id == product_variant_id
        )
        
        if status:
            query = query.where(ProductReview.status == status)
        else:
            query = query.where(ProductReview.status == ReviewStatus.APPROVED)
        
        query = query.order_by(ProductReview.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProductReview]:
        """Get reviews by a user"""
        result = await self.db.execute(
            select(ProductReview)
            .where(ProductReview.user_id == user_id)
            .order_by(ProductReview.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_pending_reviews(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProductReview]:
        """Get pending reviews for moderation"""
        result = await self.db.execute(
            select(ProductReview)
            .where(ProductReview.status == ReviewStatus.PENDING)
            .order_by(ProductReview.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_product_rating_stats(self, product_variant_id: UUID) -> dict:
        """Get rating statistics for a product"""
        result = await self.db.execute(
            select(
                func.count(ProductReview.id).label("total_reviews"),
                func.avg(ProductReview.rating).label("average_rating"),
                func.sum(
                    func.case((ProductReview.is_verified_purchase == True, 1), else_=0)
                ).label("verified_count")
            ).where(
                and_(
                    ProductReview.product_variant_id == product_variant_id,
                    ProductReview.status == ReviewStatus.APPROVED
                )
            )
        )
        
        row = result.first()
        
        # Get rating distribution
        distribution_result = await self.db.execute(
            select(
                ProductReview.rating,
                func.count(ProductReview.id).label("count")
            )
            .where(
                and_(
                    ProductReview.product_variant_id == product_variant_id,
                    ProductReview.status == ReviewStatus.APPROVED
                )
            )
            .group_by(ProductReview.rating)
        )
        
        rating_distribution = {r.rating: r.count for r in distribution_result.all()}
        
        return {
            "total_reviews": row.total_reviews or 0,
            "average_rating": row.average_rating or Decimal("0.0"),
            "rating_distribution": rating_distribution,
            "verified_purchase_count": row.verified_count or 0
        }
    
    async def update_helpfulness(
        self,
        review_id: UUID,
        is_helpful: bool
    ) -> ProductReview:
        """Update review helpfulness count"""
        review = await self.get(review_id)
        if not review:
            raise ValueError(f"Review {review_id} not found")
        
        if is_helpful:
            review.helpful_count += 1
        else:
            review.not_helpful_count += 1
        
        await self.db.commit()
        await self.db.refresh(review)
        return review


class PromoCodeRepository(BaseRepository[PromoCode]):
    """Repository for promotional code operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(PromoCode, db)
    
    async def get_by_code(self, code: str) -> Optional[PromoCode]:
        """Get promo code by code string"""
        result = await self.db.execute(
            select(PromoCode).where(PromoCode.code == code.upper())
        )
        return result.scalar_one_or_none()
    
    async def get_active_codes(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[PromoCode]:
        """Get all active promo codes"""
        now = datetime.utcnow()
        
        result = await self.db.execute(
            select(PromoCode)
            .where(
                and_(
                    PromoCode.status == PromoCodeStatus.ACTIVE,
                    PromoCode.valid_from <= now,
                    PromoCode.valid_until >= now
                )
            )
            .order_by(PromoCode.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def increment_usage(self, promo_code_id: UUID) -> PromoCode:
        """Increment usage count for promo code"""
        promo_code = await self.get(promo_code_id)
        if not promo_code:
            raise ValueError(f"Promo code {promo_code_id} not found")
        
        promo_code.current_usage_count += 1
        
        # Check if usage limit reached
        if promo_code.usage_limit and promo_code.current_usage_count >= promo_code.usage_limit:
            promo_code.status = PromoCodeStatus.EXHAUSTED
        
        await self.db.commit()
        await self.db.refresh(promo_code)
        return promo_code
    
    async def get_customer_usage_count(
        self,
        promo_code_id: UUID,
        user_id: UUID
    ) -> int:
        """Get usage count for a specific customer"""
        result = await self.db.execute(
            select(func.count(PromoCodeUsage.id))
            .where(
                and_(
                    PromoCodeUsage.promo_code_id == promo_code_id,
                    PromoCodeUsage.user_id == user_id
                )
            )
        )
        return result.scalar() or 0
    
    async def expire_outdated_codes(self) -> int:
        """Mark expired promo codes as expired"""
        now = datetime.utcnow()
        
        result = await self.db.execute(
            select(PromoCode).where(
                and_(
                    PromoCode.status == PromoCodeStatus.ACTIVE,
                    PromoCode.valid_until < now
                )
            )
        )
        
        codes = result.scalars().all()
        count = 0
        
        for code in codes:
            code.status = PromoCodeStatus.EXPIRED
            count += 1
        
        await self.db.commit()
        return count


class PromoCodeUsageRepository(BaseRepository[PromoCodeUsage]):
    """Repository for promo code usage operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(PromoCodeUsage, db)
    
    async def get_by_promo_code(
        self,
        promo_code_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[PromoCodeUsage]:
        """Get usage history for a promo code"""
        result = await self.db.execute(
            select(PromoCodeUsage)
            .where(PromoCodeUsage.promo_code_id == promo_code_id)
            .order_by(PromoCodeUsage.used_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[PromoCodeUsage]:
        """Get promo code usage history for a user"""
        result = await self.db.execute(
            select(PromoCodeUsage)
            .where(PromoCodeUsage.user_id == user_id)
            .order_by(PromoCodeUsage.used_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_usage_statistics(self, promo_code_id: UUID) -> dict:
        """Get usage statistics for a promo code"""
        result = await self.db.execute(
            select(
                func.count(PromoCodeUsage.id).label("total_uses"),
                func.sum(PromoCodeUsage.discount_amount).label("total_discount"),
                func.avg(PromoCodeUsage.discount_amount).label("average_discount"),
                func.count(func.distinct(PromoCodeUsage.user_id)).label("unique_users")
            ).where(PromoCodeUsage.promo_code_id == promo_code_id)
        )
        
        row = result.first()
        
        return {
            "total_uses": row.total_uses or 0,
            "total_discount": row.total_discount or Decimal("0.00"),
            "average_discount": row.average_discount or Decimal("0.00"),
            "unique_users": row.unique_users or 0
        }
