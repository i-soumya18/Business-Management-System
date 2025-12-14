# Phase 2.4: E-Commerce Module - Quick Reference

## API Endpoints Quick Reference

### Shopping Cart
```
GET    /api/v1/ecommerce/cart                              # Get cart
POST   /api/v1/ecommerce/cart/items                        # Add to cart
PUT    /api/v1/ecommerce/cart/items/{item_id}              # Update quantity
DELETE /api/v1/ecommerce/cart/items/{item_id}              # Remove item
DELETE /api/v1/ecommerce/cart                              # Clear cart
POST   /api/v1/ecommerce/cart/apply-promo                  # Apply promo code
```

### Wishlist
```
GET    /api/v1/ecommerce/wishlists                         # Get wishlists
POST   /api/v1/ecommerce/wishlists                         # Create wishlist
PUT    /api/v1/ecommerce/wishlists/{wishlist_id}           # Update wishlist
DELETE /api/v1/ecommerce/wishlists/{wishlist_id}           # Delete wishlist
POST   /api/v1/ecommerce/wishlists/items                   # Add to wishlist
DELETE /api/v1/ecommerce/wishlists/items/{item_id}         # Remove from wishlist
POST   /api/v1/ecommerce/wishlists/items/{item_id}/move-to-cart  # Move to cart
```

### Product Reviews
```
GET    /api/v1/ecommerce/products/{variant_id}/reviews     # Get reviews
GET    /api/v1/ecommerce/products/{variant_id}/reviews/stats  # Get stats
POST   /api/v1/ecommerce/reviews                           # Create review
PUT    /api/v1/ecommerce/reviews/{review_id}               # Update review
DELETE /api/v1/ecommerce/reviews/{review_id}               # Delete review
POST   /api/v1/ecommerce/reviews/{review_id}/vote          # Vote helpful/not
```

### Admin: Reviews
```
GET    /api/v1/ecommerce/admin/reviews/pending             # Pending reviews
POST   /api/v1/ecommerce/admin/reviews/{id}/moderate       # Moderate review
```

### Admin: Promo Codes
```
GET    /api/v1/ecommerce/admin/promo-codes                 # List promo codes
POST   /api/v1/ecommerce/admin/promo-codes                 # Create promo code
PUT    /api/v1/ecommerce/admin/promo-codes/{id}            # Update promo code
DELETE /api/v1/ecommerce/admin/promo-codes/{id}            # Delete promo code
```

### Admin: Abandoned Carts
```
GET    /api/v1/ecommerce/admin/abandoned-carts             # Get abandoned carts
```

## Database Tables

### shopping_carts
- **Purpose:** User and guest shopping carts
- **Key Fields:** user_id, session_id, status, promo_code_id, discount_amount, order_id
- **Statuses:** ACTIVE, ABANDONED, CONVERTED, MERGED
- **Properties:** subtotal, total, item_count

### cart_items
- **Purpose:** Items in shopping carts
- **Key Fields:** cart_id, product_variant_id, quantity, unit_price
- **Property:** subtotal (calculated)

### wishlists
- **Purpose:** Customer wishlists
- **Key Fields:** user_id, name, description, is_public
- **Features:** Multiple wishlists per user, public/private visibility

### wishlist_items
- **Purpose:** Items in wishlists
- **Key Fields:** wishlist_id, product_variant_id, priority, notes
- **Features:** Priority ranking (1-5), personal notes

### product_reviews
- **Purpose:** Product reviews with moderation
- **Key Fields:** user_id, product_variant_id, rating, title, review_text, status, is_verified_purchase
- **Statuses:** PENDING, APPROVED, REJECTED, FLAGGED
- **Features:** Helpfulness voting, moderation tracking

### promo_codes
- **Purpose:** Promotional codes
- **Key Fields:** code, promo_type, discount_percentage, discount_amount, usage_limit, valid_from, valid_until, status
- **Types:** PERCENTAGE, FIXED_AMOUNT, FREE_SHIPPING, BUY_X_GET_Y
- **Statuses:** ACTIVE, INACTIVE, EXPIRED, EXHAUSTED

### promo_code_usages
- **Purpose:** Track promo code usage
- **Key Fields:** promo_code_id, user_id, order_id, discount_amount, used_at

## Common Use Cases

### 1. Add Item to Cart
```python
POST /api/v1/ecommerce/cart/items
{
  "product_variant_id": "uuid",
  "quantity": 2
}
```

### 2. Apply Promo Code
```python
POST /api/v1/ecommerce/cart/apply-promo
{
  "code": "SAVE20"
}
```

### 3. Create Review
```python
POST /api/v1/ecommerce/reviews
{
  "product_variant_id": "uuid",
  "rating": 5,
  "title": "Great product!",
  "review_text": "Highly recommended",
  "order_id": "uuid"  # optional
}
```

### 4. Add to Wishlist
```python
POST /api/v1/ecommerce/wishlists/items
{
  "product_variant_id": "uuid",
  "priority": 1,
  "notes": "Must have!"
}
```

### 5. Create Promo Code (Admin)
```python
POST /api/v1/ecommerce/admin/promo-codes
{
  "code": "SAVE20",
  "promo_type": "PERCENTAGE",
  "discount_percentage": 20.00,
  "minimum_order_value": 50.00,
  "usage_limit": 100,
  "usage_per_customer": 1,
  "valid_from": "2024-01-01T00:00:00",
  "valid_until": "2024-12-31T23:59:59",
  "is_active": true
}
```

## Service Layer Methods

### ShoppingCartService
- `get_or_create_cart(user_id, session_id)` - Get or create cart
- `add_to_cart(request, user_id, session_id)` - Add item
- `update_cart_item(item_id, request)` - Update quantity
- `remove_from_cart(item_id)` - Remove item
- `clear_cart(cart_id)` - Clear all items
- `merge_carts(guest_cart_id, user_cart_id)` - Merge on login

### PromoCodeService
- `validate_promo_code(code, user_id, subtotal)` - Validate code
- `apply_promo_code(promo_code_id, user_id, order_id, discount_amount)` - Apply to order

### WishlistService
- `add_to_wishlist(user_id, request, wishlist_id)` - Add item
- `remove_from_wishlist(item_id, user_id)` - Remove item
- `move_to_cart(item_id, user_id, cart_service)` - Move to cart

### ProductReviewService
- `create_review(user_id, request)` - Create review (PENDING status)
- `update_review(review_id, user_id, request)` - Update review
- `moderate_review(review_id, moderator_id, request)` - Moderate (admin)
- `vote_helpfulness(review_id, is_helpful)` - Vote on helpfulness
- `get_product_reviews(product_variant_id, status, skip, limit)` - Get reviews
- `get_product_rating_stats(product_variant_id)` - Get rating statistics

### AbandonedCartService
- `get_abandoned_carts(days_abandoned, skip, limit)` - Get abandoned carts
- `mark_as_abandoned(cart_id)` - Mark as abandoned

## Key Features

### Guest User Support
- Session-based carts via `session_id`
- Cart merge on login (guest + user carts)
- Preserved pricing and items

### Cart Management
- Add/update/remove items
- Automatic quantity updates for existing items
- Real-time subtotal/total calculations
- Promo code application

### Wishlist Features
- Multiple wishlists per user
- Public/private visibility
- Priority ranking
- Personal notes
- One-click move to cart

### Review System
- Moderation workflow (PENDING → APPROVED/REJECTED/FLAGGED)
- Verified purchase badges
- Helpfulness voting
- Rating distribution statistics
- Admin moderation notes

### Promotional Codes
- 4 discount types (percentage, fixed, free shipping, buy-x-get-y)
- Restrictions (minimum order, categories, products, customers)
- Usage limits (total and per customer)
- Automatic expiration
- Usage tracking and statistics

### Abandoned Cart Recovery
- Configurable abandonment threshold
- Last activity tracking
- Status workflow
- Recovery campaign support

## Integration Points

### With User System
- Cart ownership (`user_id`)
- Wishlist ownership (`user_id`)
- Review authorship (`user_id`)
- Promo code usage tracking (`user_id`)

### With Product Catalog
- Cart items (`product_variant_id`)
- Wishlist items (`product_variant_id`)
- Reviews (`product_variant_id`)

### With Order System (Ready)
- Cart conversion (`order_id`)
- Verified purchases (`order_id` in reviews)
- Promo code application (`order_id`)

## Testing
21 comprehensive test cases covering:
- Cart operations (create, add, update, remove, merge)
- Wishlist operations (create, add, remove, move to cart)
- Review operations (create, update, vote)
- Promo code operations (create, validate, track usage)
- Abandoned cart detection
- Integration flows

## Next Steps
Phase 2.5: Order Management System to integrate cart checkout with order processing.

---
**Last Updated:** December 14, 2024  
**Status:** ✅ Complete
