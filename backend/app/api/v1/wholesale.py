"""
Wholesale API Endpoints

REST API endpoints for B2B wholesale customer management, credit management,
contract pricing, and wholesale order operations.
"""

from typing import List, Optional
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.wholesale import CustomerStatus, CustomerType
from app.schemas.wholesale import (
    WholesaleCustomerCreate,
    WholesaleCustomerUpdate,
    WholesaleCustomerResponse,
    WholesaleCustomerList,
    CreditLimitUpdate,
    CustomerApproval,
    ContractPricingCreate,
    ContractPricingUpdate,
    ContractPricingResponse,
    ContractPricingList,
    WholesaleOrderValidation,
    BulkPricingCalculation,
    BulkPricingResponse
)
from app.repositories.wholesale import WholesaleCustomerRepository, ContractPricingRepository
from app.services.wholesale import WholesaleService


router = APIRouter(prefix="/wholesale", tags=["Wholesale B2B"])


# ==================== Customer Management ====================

@router.post("/customers", response_model=WholesaleCustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_wholesale_customer(
    customer_data: WholesaleCustomerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new wholesale customer
    
    Creates a new B2B wholesale customer account with credit management,
    payment terms, and pricing settings.
    """
    repo = WholesaleCustomerRepository(db)
    
    # Check for duplicates
    existing = await repo.get_by_company_name(customer_data.company_name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer with this company name already exists"
        )
    
    if customer_data.primary_email:
        existing = await repo.get_by_email(customer_data.primary_email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer with this email already exists"
            )
    
    if customer_data.tax_id:
        existing = await repo.get_by_tax_id(customer_data.tax_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer with this tax ID already exists"
            )
    
    # Create customer
    customer = await repo.create(customer_data.model_dump())
    return customer


@router.get("/customers", response_model=WholesaleCustomerList)
async def list_wholesale_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[CustomerStatus] = None,
    customer_type: Optional[CustomerType] = None,
    search: Optional[str] = None,
    sales_rep_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List wholesale customers with filtering and pagination
    
    Supports filtering by:
    - Status (active, inactive, pending_approval, etc.)
    - Customer type (retailer, distributor, wholesaler, etc.)
    - Search term (company name, email, phone, tax ID)
    - Sales representative
    """
    repo = WholesaleCustomerRepository(db)
    
    if search:
        customers, total = await repo.search_customers(
            search_term=search,
            customer_type=customer_type,
            status=status,
            skip=skip,
            limit=limit
        )
    elif sales_rep_id:
        customers, total = await repo.get_by_sales_rep(
            sales_rep_id=sales_rep_id,
            status=status,
            skip=skip,
            limit=limit
        )
    elif status:
        customers, total = await repo.get_by_status(
            status=status,
            skip=skip,
            limit=limit
        )
    else:
        customers, total = await repo.get_all(skip=skip, limit=limit)
    
    pages = (total + limit - 1) // limit
    
    return WholesaleCustomerList(
        items=customers,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
        pages=pages
    )


@router.get("/customers/pending-approval", response_model=WholesaleCustomerList)
async def get_pending_approvals(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all customers pending approval"""
    repo = WholesaleCustomerRepository(db)
    customers, total = await repo.get_pending_approvals(skip=skip, limit=limit)
    
    pages = (total + limit - 1) // limit
    
    return WholesaleCustomerList(
        items=customers,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
        pages=pages
    )


@router.get("/customers/{customer_id}", response_model=WholesaleCustomerResponse)
async def get_wholesale_customer(
    customer_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific wholesale customer by ID"""
    repo = WholesaleCustomerRepository(db)
    customer = await repo.get_by_id_with_relationships(customer_id)
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    return customer


@router.patch("/customers/{customer_id}", response_model=WholesaleCustomerResponse)
async def update_wholesale_customer(
    customer_id: UUID,
    customer_data: WholesaleCustomerUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a wholesale customer"""
    repo = WholesaleCustomerRepository(db)
    
    # Get existing customer
    customer = await repo.get_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Check for email conflicts if email is being updated
    if customer_data.primary_email and customer_data.primary_email != customer.primary_email:
        existing = await repo.get_by_email(customer_data.primary_email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer with this email already exists"
            )
    
    # Update customer
    update_data = customer_data.model_dump(exclude_unset=True)
    updated_customer = await repo.update(customer_id, update_data)
    return updated_customer


@router.delete("/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wholesale_customer(
    customer_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a wholesale customer"""
    repo = WholesaleCustomerRepository(db)
    
    customer = await repo.get_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    await repo.delete(customer_id)


# ==================== Customer Approval ====================

@router.post("/customers/{customer_id}/approve", response_model=WholesaleCustomerResponse)
async def approve_customer(
    customer_id: UUID,
    approval_data: CustomerApproval,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Approve or reject a pending customer application"""
    repo = WholesaleCustomerRepository(db)
    
    customer = await repo.get_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    if customer.status != CustomerStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Customer is not pending approval (status: {customer.status.value})"
        )
    
    if approval_data.approved:
        updated_customer = await repo.approve_customer(customer_id, current_user.id)
    else:
        updated_customer = await repo.reject_customer(customer_id)
    
    # Add notes if provided
    if approval_data.notes:
        notes = customer.notes or ""
        notes += f"\n[{current_user.full_name}]: {approval_data.notes}"
        await repo.update(customer_id, {"notes": notes})
    
    return updated_customer


@router.post("/customers/{customer_id}/suspend", response_model=WholesaleCustomerResponse)
async def suspend_customer(
    customer_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Suspend a customer account"""
    repo = WholesaleCustomerRepository(db)
    
    customer = await repo.get_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    updated_customer = await repo.suspend_customer(customer_id)
    return updated_customer


@router.post("/customers/{customer_id}/reactivate", response_model=WholesaleCustomerResponse)
async def reactivate_customer(
    customer_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reactivate a suspended/inactive customer account"""
    repo = WholesaleCustomerRepository(db)
    
    customer = await repo.get_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    updated_customer = await repo.reactivate_customer(customer_id)
    return updated_customer


# ==================== Credit Management ====================

@router.patch("/customers/{customer_id}/credit-limit", response_model=WholesaleCustomerResponse)
async def update_credit_limit(
    customer_id: UUID,
    credit_data: CreditLimitUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update customer credit limit"""
    repo = WholesaleCustomerRepository(db)
    
    customer = await repo.get_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    updated_customer = await repo.update_credit_limit(customer_id, credit_data.credit_limit)
    
    # Add note about credit limit change
    if credit_data.notes:
        notes = customer.notes or ""
        notes += f"\n[{current_user.full_name}] Credit limit updated to {credit_data.credit_limit}: {credit_data.notes}"
        await repo.update(customer_id, {"notes": notes})
    
    return updated_customer


@router.get("/customers/{customer_id}/credit-status")
async def get_credit_status(
    customer_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed credit status for a customer"""
    service = WholesaleService(db)
    
    try:
        credit_status = await service.check_credit_status(customer_id)
        return credit_status
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/customers/alerts/credit")
async def get_credit_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get customers with credit issues (exceeded or near limit)"""
    repo = WholesaleCustomerRepository(db)
    
    exceeded = await repo.get_customers_exceeding_credit()
    near_limit = await repo.get_customers_near_credit_limit(threshold=0.9)
    
    return {
        "exceeded_limit": [
            {
                "id": str(c.id),
                "company_name": c.company_name,
                "credit_limit": float(c.credit_limit),
                "credit_used": float(c.credit_used),
                "credit_available": float(c.credit_available)
            }
            for c in exceeded
        ],
        "near_limit": [
            {
                "id": str(c.id),
                "company_name": c.company_name,
                "credit_limit": float(c.credit_limit),
                "credit_used": float(c.credit_used),
                "credit_available": float(c.credit_available),
                "utilization_percentage": float((c.credit_used / c.credit_limit * 100) if c.credit_limit > 0 else 0)
            }
            for c in near_limit
        ]
    }


# ==================== Contract Pricing ====================

@router.post("/contract-pricing", response_model=ContractPricingResponse, status_code=status.HTTP_201_CREATED)
async def create_contract_pricing(
    pricing_data: ContractPricingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a contract price for a customer"""
    repo = ContractPricingRepository(db)
    
    # Verify customer exists
    customer_repo = WholesaleCustomerRepository(db)
    customer = await customer_repo.get_by_id(pricing_data.customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Create contract pricing
    pricing_dict = pricing_data.model_dump()
    pricing_dict["created_by_id"] = current_user.id
    
    pricing = await repo.create(pricing_dict)
    return pricing


@router.get("/contract-pricing/customer/{customer_id}", response_model=ContractPricingList)
async def get_customer_contract_pricing(
    customer_id: UUID,
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all contract prices for a customer"""
    repo = ContractPricingRepository(db)
    
    prices, total = await repo.get_by_customer(
        customer_id=customer_id,
        active_only=active_only,
        skip=skip,
        limit=limit
    )
    
    pages = (total + limit - 1) // limit
    
    return ContractPricingList(
        items=prices,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
        pages=pages
    )


@router.get("/contract-pricing/{pricing_id}", response_model=ContractPricingResponse)
async def get_contract_pricing(
    pricing_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific contract price"""
    repo = ContractPricingRepository(db)
    pricing = await repo.get_by_id(pricing_id)
    
    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract pricing not found"
        )
    
    return pricing


@router.patch("/contract-pricing/{pricing_id}", response_model=ContractPricingResponse)
async def update_contract_pricing(
    pricing_id: UUID,
    pricing_data: ContractPricingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a contract price"""
    repo = ContractPricingRepository(db)
    
    pricing = await repo.get_by_id(pricing_id)
    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract pricing not found"
        )
    
    update_data = pricing_data.model_dump(exclude_unset=True)
    updated_pricing = await repo.update(pricing_id, update_data)
    return updated_pricing


@router.delete("/contract-pricing/{pricing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract_pricing(
    pricing_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a contract price"""
    repo = ContractPricingRepository(db)
    
    pricing = await repo.get_by_id(pricing_id)
    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract pricing not found"
        )
    
    await repo.delete(pricing_id)


# ==================== Order Validation & Pricing ====================

@router.post("/orders/validate", response_model=WholesaleOrderValidation)
async def validate_wholesale_order(
    customer_id: UUID,
    items: List[dict],
    apply_credit_check: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate a wholesale order
    
    Validates:
    - Customer status and eligibility
    - Minimum Order Quantity (MOQ)
    - Minimum Order Value (MOV)
    - Credit limit availability
    - Product availability
    - Contract pricing applicability
    """
    service = WholesaleService(db)
    validation = await service.validate_wholesale_order(
        customer_id=customer_id,
        items=items,
        apply_credit_check=apply_credit_check
    )
    return validation


@router.post("/orders/calculate-pricing", response_model=BulkPricingResponse)
async def calculate_bulk_pricing(
    pricing_calc: BulkPricingCalculation,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate bulk pricing for wholesale orders
    
    Applies:
    - Contract pricing (if available)
    - Volume discounts
    - Customer default discounts
    - Pricing tier rules
    """
    service = WholesaleService(db)
    
    try:
        pricing = await service.calculate_bulk_pricing(
            customer_id=pricing_calc.customer_id,
            items=pricing_calc.items
        )
        return pricing
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ==================== Customer Analytics ====================

@router.get("/customers/{customer_id}/summary")
async def get_customer_summary(
    customer_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive customer summary with analytics"""
    service = WholesaleService(db)
    
    try:
        summary = await service.get_customer_summary(customer_id)
        return summary
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/customers/{customer_id}/refresh-metrics", response_model=WholesaleCustomerResponse)
async def refresh_customer_metrics(
    customer_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Recalculate and update customer performance metrics"""
    service = WholesaleService(db)
    
    customer = await service.update_customer_performance(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    return customer


# ==================== Utility Endpoints ====================

@router.post("/maintenance/cleanup-expired-contracts")
async def cleanup_expired_contracts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate expired contract prices (maintenance operation)"""
    service = WholesaleService(db)
    count = await service.cleanup_expired_contracts()
    return {"deactivated_count": count}
