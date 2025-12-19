"""
Retail Customer API - B2C CRM

API endpoints for retail customer management including:
- Customer registration and profile management
- Loyalty program operations
- Customer preferences
- RFM analysis and CLV calculation
- Customer analytics and segmentation
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.retail_customer import CustomerTierLevel, CustomerPreferenceType
from app.schemas.retail_customer import (
    # Customer schemas
    RetailCustomerCreate,
    RetailCustomerUpdate,
    RetailCustomerResponse,
    RetailCustomerListResponse,
    RetailCustomerRegistration,
    RetailCustomerVerification,
    RetailCustomerSearchFilters,
    
    # Loyalty schemas
    LoyaltyTransactionResponse,
    LoyaltyPointsEarn,
    LoyaltyPointsRedeem,
    LoyaltyPointsAdjust,
    LoyaltyBalanceResponse,
    LoyaltyTierUpdate,
    
    # Preference schemas
    CustomerPreferenceCreate,
    CustomerPreferenceUpdate,
    CustomerPreferenceResponse,
    CustomerPreferencesBulkUpdate,
    
    # RFM schemas
    RFMScoresResponse,
    RFMAnalysisRequest,
    RFMAnalysisResponse,
    
    # CLV schemas
    CLVCalculationRequest,
    CLVResponse,
    CLVAnalysisResponse,
    
    # Analytics schemas
    PurchaseHistorySummary,
    CustomerAnalytics,
    CustomerAcquisitionMetrics,
    CustomerRetentionMetrics,
    LoyaltyProgramMetrics,
    
    # Bulk operations
    BulkCustomerStatusUpdate,
    BulkLoyaltyTierUpdate,
    BulkTagUpdate,
)
from app.repositories.retail_customer import (
    RetailCustomerRepository,
    LoyaltyTransactionRepository,
    CustomerPreferenceRepository
)
from app.services.retail_customer import RetailCustomerService


router = APIRouter(prefix="/retail-customers", tags=["Retail Customers (B2C)"])


# ============================================================================
# Customer Management Endpoints
# ============================================================================

@router.post(
    "/",
    response_model=RetailCustomerResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_retail_customer(
    customer_data: RetailCustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new retail customer
    
    Requires: Admin or Sales role
    """
    service = RetailCustomerService(db)
    
    # Check if email already exists
    repo = RetailCustomerRepository(db)
    existing = await repo.get_by_email(customer_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if phone already exists
    existing = await repo.get_by_phone(customer_data.phone)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )
    
    # Create customer
    customer, _ = await service.register_customer(
        customer_data.model_dump(exclude_unset=True)
    )
    
    return customer


@router.post(
    "/register",
    response_model=RetailCustomerResponse,
    status_code=status.HTTP_201_CREATED
)
async def register_customer(
    registration_data: RetailCustomerRegistration,
    db: AsyncSession = Depends(get_db)
):
    """
    Customer self-registration (public endpoint)
    
    Creates customer account and awards welcome bonus
    """
    service = RetailCustomerService(db)
    repo = RetailCustomerRepository(db)
    
    # Check if email already exists
    existing = await repo.get_by_email(registration_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if phone already exists
    existing = await repo.get_by_phone(registration_data.phone)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )
    
    # Create user account (simplified - would integrate with auth service)
    # For now, just create customer profile
    customer_data = registration_data.model_dump(exclude={"password", "referral_code"})
    
    customer, loyalty_txn = await service.register_customer(
        customer_data,
        welcome_bonus=100
    )
    
    return customer


@router.get("/{customer_id}", response_model=RetailCustomerResponse)
async def get_retail_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get retail customer by ID"""
    repo = RetailCustomerRepository(db)
    customer = await repo.get(customer_id)
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    return customer


@router.get("/number/{customer_number}", response_model=RetailCustomerResponse)
async def get_customer_by_number(
    customer_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get retail customer by customer number"""
    repo = RetailCustomerRepository(db)
    customer = await repo.get_by_customer_number(customer_number)
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    return customer


@router.get("/email/{email}", response_model=RetailCustomerResponse)
async def get_customer_by_email(
    email: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get retail customer by email"""
    repo = RetailCustomerRepository(db)
    customer = await repo.get_by_email(email)
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    return customer


@router.get("/", response_model=List[RetailCustomerListResponse])
async def list_retail_customers(
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    loyalty_tier: Optional[CustomerTierLevel] = None,
    rfm_segment: Optional[str] = None,
    city: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List retail customers with filtering and search
    
    Supports:
    - Full-text search on name, email, phone, customer number
    - Filter by status, tier, segment, city
    """
    repo = RetailCustomerRepository(db)
    
    customers = await repo.search_customers(
        search=search,
        is_active=is_active,
        loyalty_tier=loyalty_tier,
        rfm_segment=rfm_segment,
        city=city,
        skip=skip,
        limit=limit
    )
    
    return customers


@router.post("/search", response_model=List[RetailCustomerListResponse])
async def search_retail_customers(
    filters: RetailCustomerSearchFilters,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Advanced customer search with comprehensive filters
    
    Supports filtering by:
    - Demographics, spending, orders, dates
    - Marketing consent, tier, segment
    """
    repo = RetailCustomerRepository(db)
    
    customers = await repo.search_customers(
        **filters.model_dump(exclude_unset=True),
        skip=skip,
        limit=limit
    )
    
    return customers


@router.put("/{customer_id}", response_model=RetailCustomerResponse)
async def update_retail_customer(
    customer_id: UUID,
    customer_data: RetailCustomerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update retail customer profile"""
    repo = RetailCustomerRepository(db)
    
    customer = await repo.get(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Check email uniqueness if changed
    if customer_data.email and customer_data.email != customer.email:
        existing = await repo.get_by_email(customer_data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
    
    # Check phone uniqueness if changed
    if customer_data.phone and customer_data.phone != customer.phone:
        existing = await repo.get_by_phone(customer_data.phone)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already in use"
            )
    
    updated = await repo.update(
        customer_id,
        customer_data.model_dump(exclude_unset=True)
    )
    
    return updated


@router.post("/{customer_id}/verify-email", response_model=RetailCustomerResponse)
async def verify_customer_email(
    customer_id: UUID,
    verification: RetailCustomerVerification,
    db: AsyncSession = Depends(get_db)
):
    """Verify customer email (public endpoint with code)"""
    if verification.verification_type != "email":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification type"
        )
    
    # TODO: Validate verification code
    # For now, just mark as verified
    
    service = RetailCustomerService(db)
    customer = await service.verify_email(customer_id)
    
    return customer


@router.post("/{customer_id}/verify-phone", response_model=RetailCustomerResponse)
async def verify_customer_phone(
    customer_id: UUID,
    verification: RetailCustomerVerification,
    db: AsyncSession = Depends(get_db)
):
    """Verify customer phone (public endpoint with code)"""
    if verification.verification_type != "phone":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification type"
        )
    
    # TODO: Validate verification code
    # For now, just mark as verified
    
    service = RetailCustomerService(db)
    customer = await service.verify_phone(customer_id)
    
    return customer


@router.post("/{customer_id}/deactivate", response_model=RetailCustomerResponse)
async def deactivate_customer(
    customer_id: UUID,
    reason: str = Query(..., min_length=1, max_length=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deactivate a customer account"""
    service = RetailCustomerService(db)
    customer = await service.deactivate_customer(customer_id, reason)
    return customer


@router.post("/{customer_id}/reactivate", response_model=RetailCustomerResponse)
async def reactivate_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reactivate a customer account"""
    service = RetailCustomerService(db)
    customer = await service.reactivate_customer(customer_id)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_retail_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a retail customer (soft delete recommended)"""
    repo = RetailCustomerRepository(db)
    
    customer = await repo.get(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Soft delete by deactivating
    service = RetailCustomerService(db)
    await service.deactivate_customer(customer_id, "Account deleted")
    
    return None


# ============================================================================
# Loyalty Program Endpoints
# ============================================================================

@router.get(
    "/{customer_id}/loyalty/balance",
    response_model=LoyaltyBalanceResponse
)
async def get_loyalty_balance(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get customer loyalty points balance and expiry info"""
    service = RetailCustomerService(db)
    
    try:
        balance = await service.get_loyalty_balance(customer_id)
        return balance
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "/{customer_id}/loyalty/transactions",
    response_model=List[LoyaltyTransactionResponse]
)
async def get_loyalty_transactions(
    customer_id: UUID,
    transaction_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get customer loyalty transaction history"""
    repo = LoyaltyTransactionRepository(db)
    transactions = await repo.get_customer_transactions(
        customer_id,
        transaction_type,
        skip,
        limit
    )
    return transactions


@router.post(
    "/loyalty/earn",
    response_model=LoyaltyTransactionResponse,
    status_code=status.HTTP_201_CREATED
)
async def earn_loyalty_points(
    earn_data: LoyaltyPointsEarn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Award loyalty points to customer"""
    service = RetailCustomerService(db)
    
    try:
        transaction = await service.earn_loyalty_points(
            customer_id=earn_data.customer_id,
            points=earn_data.points,
            description=earn_data.description,
            order_id=earn_data.order_id,
            expiry_days=earn_data.expiry_days
        )
        return transaction
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/loyalty/redeem",
    response_model=LoyaltyTransactionResponse,
    status_code=status.HTTP_201_CREATED
)
async def redeem_loyalty_points(
    redeem_data: LoyaltyPointsRedeem,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Redeem loyalty points"""
    service = RetailCustomerService(db)
    
    try:
        transaction = await service.redeem_loyalty_points(
            customer_id=redeem_data.customer_id,
            points=redeem_data.points,
            description=redeem_data.description,
            order_id=redeem_data.order_id
        )
        return transaction
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/loyalty/adjust",
    response_model=LoyaltyTransactionResponse,
    status_code=status.HTTP_201_CREATED
)
async def adjust_loyalty_points(
    adjust_data: LoyaltyPointsAdjust,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually adjust loyalty points (admin only)"""
    service = RetailCustomerService(db)
    
    try:
        transaction = await service.adjust_loyalty_points(
            customer_id=adjust_data.customer_id,
            points=adjust_data.points,
            reason=adjust_data.reason
        )
        return transaction
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/loyalty/expire-points")
async def expire_loyalty_points(
    customer_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Expire loyalty points that have passed expiry date
    
    If customer_id is provided, expires for that customer only.
    Otherwise, expires for all customers.
    """
    service = RetailCustomerService(db)
    total_expired = await service.expire_loyalty_points(customer_id)
    
    return {
        "message": f"Expired {total_expired} loyalty points",
        "points_expired": total_expired
    }


@router.put("/loyalty/tier", response_model=RetailCustomerResponse)
async def update_loyalty_tier(
    tier_data: LoyaltyTierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update customer loyalty tier (admin only)"""
    repo = RetailCustomerRepository(db)
    
    try:
        customer = await repo.update_loyalty_tier(
            customer_id=tier_data.customer_id,
            tier=tier_data.new_tier,
            tier_expiry_date=tier_data.tier_expiry_date
        )
        return customer
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{customer_id}/loyalty/auto-tier", response_model=RetailCustomerResponse)
async def auto_update_loyalty_tier(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Auto-calculate and update customer loyalty tier based on points"""
    service = RetailCustomerService(db)
    
    try:
        customer = await service.update_loyalty_tier(customer_id, auto_calculate=True)
        return customer
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================================================
# Customer Preferences Endpoints
# ============================================================================

@router.get(
    "/{customer_id}/preferences",
    response_model=List[CustomerPreferenceResponse]
)
async def get_customer_preferences(
    customer_id: UUID,
    preference_type: Optional[CustomerPreferenceType] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get customer preferences"""
    service = RetailCustomerService(db)
    preferences = await service.get_customer_preferences(customer_id, preference_type)
    return preferences


@router.post(
    "/{customer_id}/preferences",
    response_model=CustomerPreferenceResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_customer_preference(
    customer_id: UUID,
    preference_data: CustomerPreferenceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a customer preference"""
    # Override customer_id from path
    preference_data.customer_id = customer_id
    
    repo = CustomerPreferenceRepository(db)
    preference = await repo.upsert_preference(
        customer_id=customer_id,
        preference_type=preference_data.preference_type,
        preference_key=preference_data.preference_key,
        preference_value=preference_data.preference_value
    )
    
    return preference


@router.put(
    "/{customer_id}/preferences/{preference_id}",
    response_model=CustomerPreferenceResponse
)
async def update_customer_preference(
    customer_id: UUID,
    preference_id: UUID,
    preference_data: CustomerPreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a customer preference"""
    repo = CustomerPreferenceRepository(db)
    
    preference = await repo.get(preference_id)
    if not preference or preference.customer_id != customer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preference not found"
        )
    
    updated = await repo.update(
        preference_id,
        preference_data.model_dump(exclude_unset=True)
    )
    
    return updated


@router.post("/{customer_id}/preferences/bulk", response_model=List[CustomerPreferenceResponse])
async def bulk_update_preferences(
    customer_id: UUID,
    bulk_data: CustomerPreferencesBulkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk create/update customer preferences"""
    # Override customer_id from path
    bulk_data.customer_id = customer_id
    
    service = RetailCustomerService(db)
    preferences = await service.update_customer_preferences(
        customer_id,
        bulk_data.preferences
    )
    
    return preferences


@router.delete("/{customer_id}/preferences/{preference_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer_preference(
    customer_id: UUID,
    preference_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a customer preference"""
    repo = CustomerPreferenceRepository(db)
    
    preference = await repo.get(preference_id)
    if not preference or preference.customer_id != customer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preference not found"
        )
    
    await repo.delete(preference_id)
    return None


# ============================================================================
# RFM Analysis Endpoints
# ============================================================================

@router.post("/analytics/rfm/calculate")
async def calculate_rfm_scores(
    request: RFMAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calculate RFM scores for customers
    
    RFM Analysis segments customers based on:
    - Recency: How recently they purchased
    - Frequency: How often they purchase
    - Monetary: How much they spend
    """
    service = RetailCustomerService(db)
    
    customers = await service.calculate_rfm_scores(request.customer_ids)
    
    return {
        "message": f"RFM scores calculated for {len(customers)} customers",
        "customers_updated": len(customers)
    }


@router.get("/{customer_id}/analytics/rfm", response_model=RFMScoresResponse)
async def get_customer_rfm_scores(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get RFM scores for a specific customer"""
    repo = RetailCustomerRepository(db)
    customer = await repo.get(customer_id)
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    if not customer.rfm_recency_score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RFM scores not calculated for this customer"
        )
    
    days_since_last_order = None
    if customer.last_order_date:
        days_since_last_order = (datetime.utcnow() - customer.last_order_date).days
    
    return RFMScoresResponse(
        customer_id=customer.id,
        customer_number=customer.customer_number,
        customer_name=customer.full_name,
        recency_score=customer.rfm_recency_score,
        frequency_score=customer.rfm_frequency_score,
        monetary_score=customer.rfm_monetary_score,
        rfm_segment=customer.rfm_segment,
        total_orders=customer.total_orders,
        total_spent=customer.total_spent,
        last_order_date=customer.last_order_date,
        days_since_last_order=days_since_last_order,
        calculated_at=customer.rfm_last_calculated
    )


@router.get("/analytics/rfm/distribution", response_model=RFMAnalysisResponse)
async def get_rfm_segment_distribution(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get RFM segment distribution across all customers"""
    service = RetailCustomerService(db)
    analysis = await service.get_rfm_segment_distribution()
    
    return RFMAnalysisResponse(
        total_customers_analyzed=analysis["total_customers_analyzed"],
        segment_distribution=analysis["segment_distribution"],
        analysis_date=datetime.utcnow(),
        champion_count=analysis["champion_count"],
        loyal_count=analysis["loyal_count"],
        potential_loyalist_count=analysis["potential_loyalist_count"],
        new_customers_count=analysis["new_customers_count"],
        promising_count=analysis["promising_count"],
        need_attention_count=analysis["need_attention_count"],
        about_to_sleep_count=analysis["about_to_sleep_count"],
        at_risk_count=analysis["at_risk_count"],
        cannot_lose_count=analysis["cannot_lose_count"],
        hibernating_count=analysis["hibernating_count"],
        lost_count=analysis["lost_count"]
    )


# ============================================================================
# CLV (Customer Lifetime Value) Endpoints
# ============================================================================

@router.post("/analytics/clv/calculate")
async def calculate_clv(
    request: CLVCalculationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculate Customer Lifetime Value for customers"""
    service = RetailCustomerService(db)
    
    customers = await service.calculate_clv(
        request.customer_ids,
        request.prediction_months
    )
    
    return {
        "message": f"CLV calculated for {len(customers)} customers",
        "customers_updated": len(customers),
        "prediction_months": request.prediction_months
    }


@router.get("/{customer_id}/analytics/clv", response_model=CLVResponse)
async def get_customer_clv(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get CLV for a specific customer"""
    repo = RetailCustomerRepository(db)
    customer = await repo.get(customer_id)
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Calculate derived metrics
    age_days = (datetime.utcnow() - customer.created_at).days
    age_months = max(age_days / 30, 1)
    purchase_frequency = customer.total_orders / age_months
    
    return CLVResponse(
        customer_id=customer.id,
        customer_number=customer.customer_number,
        customer_name=customer.full_name,
        clv=customer.clv,
        predicted_orders=int(purchase_frequency * 12),  # Next 12 months
        predicted_revenue=customer.clv,
        average_order_value=customer.average_order_value,
        purchase_frequency=purchase_frequency,
        customer_lifespan_months=12,  # Default prediction window
        calculated_at=customer.clv_last_calculated or datetime.utcnow()
    )


@router.get("/analytics/clv/analysis", response_model=CLVAnalysisResponse)
async def get_clv_analysis(
    limit: int = Query(100, ge=10, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get CLV analysis and distribution"""
    service = RetailCustomerService(db)
    analysis = await service.get_clv_analysis(limit)
    
    # Convert top customers to CLVResponse
    top_customers_response = []
    for customer in analysis["top_customers"]:
        age_days = (datetime.utcnow() - customer.created_at).days
        age_months = max(age_days / 30, 1)
        purchase_frequency = customer.total_orders / age_months
        
        top_customers_response.append(
            CLVResponse(
                customer_id=customer.id,
                customer_number=customer.customer_number,
                customer_name=customer.full_name,
                clv=customer.clv,
                predicted_orders=int(purchase_frequency * 12),
                predicted_revenue=customer.clv,
                average_order_value=customer.average_order_value,
                purchase_frequency=purchase_frequency,
                customer_lifespan_months=12,
                calculated_at=customer.clv_last_calculated or datetime.utcnow()
            )
        )
    
    return CLVAnalysisResponse(
        total_customers_analyzed=analysis["total_customers_analyzed"],
        total_clv=analysis["total_clv"],
        average_clv=analysis["average_clv"],
        median_clv=analysis["median_clv"],
        distribution=analysis["distribution"],
        top_customers=top_customers_response,
        analysis_date=datetime.utcnow()
    )


# ============================================================================
# Bulk Operations Endpoints
# ============================================================================

@router.post("/bulk/status")
async def bulk_update_customer_status(
    bulk_data: BulkCustomerStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk update customer status"""
    repo = RetailCustomerRepository(db)
    count = await repo.bulk_update_status(
        bulk_data.customer_ids,
        bulk_data.is_active
    )
    
    return {
        "message": f"Updated status for {count} customers",
        "customers_updated": count
    }


@router.post("/bulk/tier")
async def bulk_update_loyalty_tier(
    bulk_data: BulkLoyaltyTierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk update loyalty tier"""
    repo = RetailCustomerRepository(db)
    count = await repo.bulk_update_tier(
        bulk_data.customer_ids,
        bulk_data.new_tier,
        bulk_data.tier_expiry_date
    )
    
    return {
        "message": f"Updated tier for {count} customers",
        "customers_updated": count
    }


# ============================================================================
# Analytics Endpoints
# ============================================================================

@router.get("/analytics/loyalty/metrics", response_model=LoyaltyProgramMetrics)
async def get_loyalty_program_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get loyalty program metrics and statistics"""
    repo = RetailCustomerRepository(db)
    
    total_members = await repo.count_customers(is_active=True)
    bronze = await repo.count_customers(is_active=True, loyalty_tier=CustomerTierLevel.BRONZE)
    silver = await repo.count_customers(is_active=True, loyalty_tier=CustomerTierLevel.SILVER)
    gold = await repo.count_customers(is_active=True, loyalty_tier=CustomerTierLevel.GOLD)
    platinum = await repo.count_customers(is_active=True, loyalty_tier=CustomerTierLevel.PLATINUM)
    
    # Get points statistics from transactions
    # This is a simplified version - in production, would use aggregated queries
    
    return LoyaltyProgramMetrics(
        total_members=total_members,
        active_members=total_members,
        bronze_members=bronze,
        silver_members=silver,
        gold_members=gold,
        platinum_members=platinum,
        total_points_issued=0,  # TODO: Calculate from transactions
        total_points_redeemed=0,  # TODO: Calculate from transactions
        total_points_expired=0,  # TODO: Calculate from transactions
        current_outstanding_points=0,  # TODO: Sum of all customer balances
        redemption_rate=0  # TODO: Calculate redemption rate
    )


@router.get("/{customer_id}/analytics/summary", response_model=CustomerAnalytics)
async def get_customer_analytics(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive analytics for a customer"""
    repo = RetailCustomerRepository(db)
    customer = await repo.get(customer_id)
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    purchase_summary = PurchaseHistorySummary(
        customer_id=customer.id,
        total_orders=customer.total_orders,
        total_spent=customer.total_spent,
        average_order_value=customer.average_order_value,
        first_order_date=customer.first_order_date,
        last_order_date=customer.last_order_date,
        favorite_category=None,  # TODO: Calculate from orders
        favorite_brand=None,  # TODO: Calculate from orders
        most_purchased_product=None,  # TODO: Calculate from orders
        purchase_frequency_days=None  # TODO: Calculate from order dates
    )
    
    return CustomerAnalytics(
        customer_id=customer.id,
        customer_number=customer.customer_number,
        customer_name=customer.full_name,
        email=customer.email,
        purchase_summary=purchase_summary,
        loyalty_tier=customer.loyalty_tier,
        loyalty_points=customer.loyalty_points,
        rfm_recency_score=customer.rfm_recency_score,
        rfm_frequency_score=customer.rfm_frequency_score,
        rfm_monetary_score=customer.rfm_monetary_score,
        rfm_segment=customer.rfm_segment,
        clv=customer.clv,
        email_open_rate=customer.email_open_rate,
        email_click_rate=customer.email_click_rate,
        last_activity_at=customer.last_activity_at
    )
