"""
CRM API Endpoints - B2B Lead Management, Opportunities, Communications

RESTful API endpoints for:
- Lead management (CRUD, qualification, conversion)
- Sales opportunity tracking (CRUD, pipeline, closing)
- Customer communications (CRUD, follow-ups)
- Customer segmentation (CRUD, assignments)
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.crm import LeadStatus, LeadSource, LeadPriority, OpportunityStage, CommunicationType
from app.services.crm import CRMService
from app.schemas.crm import (
    LeadCreate,
    LeadUpdate,
    LeadQualify,
    LeadConvert,
    LeadResponse,
    LeadListResponse,
    LeadAnalytics,
    OpportunityCreate,
    OpportunityUpdate,
    OpportunityClose,
    OpportunityResponse,
    OpportunityListResponse,
    OpportunityStats,
    CommunicationCreate,
    CommunicationUpdate,
    CommunicationResponse,
    CommunicationListResponse,
    SegmentCreate,
    SegmentUpdate,
    SegmentResponse,
    SegmentListResponse,
    SegmentAssignment,
    SalesPipelineReport
)

router = APIRouter(prefix="/crm", tags=["B2B CRM"])


# ===== Lead Endpoints =====

@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    data: LeadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new lead"""
    service = CRMService(db)
    try:
        lead = await service.create_lead(data, created_by_id=current_user.id)
        await db.commit()
        return lead
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create lead: {str(e)}"
        )


@router.get("/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get lead by ID"""
    service = CRMService(db)
    lead = await service.get_lead(lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} not found"
        )
    return lead


@router.get("/leads/number/{lead_number}", response_model=LeadResponse)
async def get_lead_by_number(
    lead_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get lead by lead number"""
    service = CRMService(db)
    lead = await service.get_lead_by_number(lead_number)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_number} not found"
        )
    return lead


@router.get("/leads", response_model=LeadListResponse)
async def list_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[LeadStatus] = None,
    source: Optional[LeadSource] = None,
    priority: Optional[LeadPriority] = None,
    assigned_to_id: Optional[UUID] = None,
    search: Optional[str] = None,
    is_qualified: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List leads with pagination and filters"""
    service = CRMService(db)
    items, total = await service.list_leads(
        page=page,
        page_size=page_size,
        status=status,
        source=source,
        priority=priority,
        assigned_to_id=assigned_to_id,
        search=search,
        is_qualified=is_qualified
    )

    total_pages = (total + page_size - 1) // page_size
    return LeadListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.put("/leads/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: UUID,
    data: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a lead"""
    service = CRMService(db)
    try:
        lead = await service.update_lead(lead_id, data)
        await db.commit()
        return lead
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update lead: {str(e)}"
        )


@router.post("/leads/{lead_id}/qualify", response_model=LeadResponse)
async def qualify_lead(
    lead_id: UUID,
    data: LeadQualify,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Qualify a lead"""
    service = CRMService(db)
    try:
        lead = await service.qualify_lead(lead_id, data)
        await db.commit()
        return lead
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to qualify lead: {str(e)}"
        )


@router.post("/leads/{lead_id}/convert", response_model=LeadResponse)
async def convert_lead(
    lead_id: UUID,
    data: LeadConvert,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Convert lead to customer"""
    service = CRMService(db)
    try:
        lead, customer = await service.convert_lead(lead_id, data)
        await db.commit()
        return lead
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to convert lead: {str(e)}"
        )


@router.delete("/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a lead"""
    service = CRMService(db)
    try:
        lead = await service.lead_repo.get_by_id(lead_id)
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead {lead_id} not found"
            )
        await service.lead_repo.delete(lead_id)
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete lead: {str(e)}"
        )


@router.get("/leads/follow-ups/today", response_model=List[LeadResponse])
async def get_today_follow_ups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get leads due for follow-up today"""
    service = CRMService(db)
    leads = await service.get_leads_for_follow_up()
    return leads


@router.get("/leads/analytics/summary", response_model=LeadAnalytics)
async def get_lead_analytics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get lead analytics"""
    service = CRMService(db)
    analytics = await service.get_lead_analytics(start_date, end_date)
    return LeadAnalytics(**analytics, average_time_to_convert_days=None)


# ===== Opportunity Endpoints =====

@router.post("/opportunities", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    data: OpportunityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new sales opportunity"""
    service = CRMService(db)
    try:
        opportunity = await service.create_opportunity(data)
        await db.commit()
        return opportunity
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create opportunity: {str(e)}"
        )


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opportunity_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get opportunity by ID"""
    service = CRMService(db)
    opportunity = await service.get_opportunity(opportunity_id)
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity {opportunity_id} not found"
        )
    return opportunity


@router.get("/opportunities/number/{opportunity_number}", response_model=OpportunityResponse)
async def get_opportunity_by_number(
    opportunity_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get opportunity by opportunity number"""
    service = CRMService(db)
    opportunity = await service.get_opportunity_by_number(opportunity_number)
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity {opportunity_number} not found"
        )
    return opportunity


@router.get("/opportunities", response_model=OpportunityListResponse)
async def list_opportunities(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    stage: Optional[OpportunityStage] = None,
    customer_id: Optional[UUID] = None,
    owner_id: Optional[UUID] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List opportunities with pagination and filters"""
    service = CRMService(db)
    items, total = await service.list_opportunities(
        page=page,
        page_size=page_size,
        stage=stage,
        customer_id=customer_id,
        owner_id=owner_id,
        min_value=min_value,
        max_value=max_value,
        search=search
    )

    total_pages = (total + page_size - 1) // page_size
    return OpportunityListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.put("/opportunities/{opportunity_id}", response_model=OpportunityResponse)
async def update_opportunity(
    opportunity_id: UUID,
    data: OpportunityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an opportunity"""
    service = CRMService(db)
    try:
        opportunity = await service.update_opportunity(opportunity_id, data)
        await db.commit()
        return opportunity
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update opportunity: {str(e)}"
        )


@router.post("/opportunities/{opportunity_id}/close", response_model=OpportunityResponse)
async def close_opportunity(
    opportunity_id: UUID,
    data: OpportunityClose,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Close an opportunity (won or lost)"""
    service = CRMService(db)
    try:
        opportunity = await service.close_opportunity(opportunity_id, data)
        await db.commit()
        return opportunity
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to close opportunity: {str(e)}"
        )


@router.delete("/opportunities/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_opportunity(
    opportunity_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an opportunity"""
    service = CRMService(db)
    try:
        opportunity = await service.opportunity_repo.get_by_id(opportunity_id)
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Opportunity {opportunity_id} not found"
            )
        await service.opportunity_repo.delete(opportunity_id)
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete opportunity: {str(e)}"
        )


@router.get("/opportunities/pipeline/stats", response_model=OpportunityStats)
async def get_pipeline_stats(
    owner_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get sales pipeline statistics"""
    service = CRMService(db)
    stats = await service.get_pipeline_stats(owner_id=owner_id)
    return OpportunityStats(
        total_opportunities=stats["total_opportunities"],
        total_value=stats["total_value"],
        weighted_value=stats["weighted_value"],
        by_stage=stats["by_stage"],
        win_rate=0.0  # TODO: Calculate win rate
    )


# ===== Communication Endpoints =====

@router.post("/communications", response_model=CommunicationResponse, status_code=status.HTTP_201_CREATED)
async def create_communication(
    data: CommunicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a customer communication record"""
    service = CRMService(db)
    try:
        communication = await service.create_communication(data)
        await db.commit()
        return communication
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create communication: {str(e)}"
        )


@router.get("/communications/{communication_id}", response_model=CommunicationResponse)
async def get_communication(
    communication_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get communication by ID"""
    service = CRMService(db)
    communication = await service.get_communication(communication_id)
    if not communication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Communication {communication_id} not found"
        )
    return communication


@router.get("/communications/customer/{customer_id}", response_model=CommunicationListResponse)
async def list_customer_communications(
    customer_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List communications for a customer"""
    service = CRMService(db)
    items, total = await service.list_communications_by_customer(
        customer_id, page, page_size
    )

    total_pages = (total + page_size - 1) // page_size
    return CommunicationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/communications/lead/{lead_id}", response_model=CommunicationListResponse)
async def list_lead_communications(
    lead_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List communications for a lead"""
    service = CRMService(db)
    items, total = await service.list_communications_by_lead(lead_id, page, page_size)

    total_pages = (total + page_size - 1) // page_size
    return CommunicationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/communications/opportunity/{opportunity_id}", response_model=CommunicationListResponse)
async def list_opportunity_communications(
    opportunity_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List communications for an opportunity"""
    service = CRMService(db)
    items, total = await service.list_communications_by_opportunity(
        opportunity_id, page, page_size
    )

    total_pages = (total + page_size - 1) // page_size
    return CommunicationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.put("/communications/{communication_id}", response_model=CommunicationResponse)
async def update_communication(
    communication_id: UUID,
    data: CommunicationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a communication record"""
    service = CRMService(db)
    try:
        communication = await service.update_communication(communication_id, data)
        await db.commit()
        return communication
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update communication: {str(e)}"
        )


@router.post("/communications/{communication_id}/complete-follow-up", response_model=CommunicationResponse)
async def mark_follow_up_completed(
    communication_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a follow-up as completed"""
    service = CRMService(db)
    try:
        communication = await service.mark_follow_up_completed(communication_id)
        await db.commit()
        return communication
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete follow-up: {str(e)}"
        )


@router.delete("/communications/{communication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_communication(
    communication_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a communication record"""
    service = CRMService(db)
    try:
        communication = await service.communication_repo.get_by_id(communication_id)
        if not communication:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Communication {communication_id} not found"
            )
        await service.communication_repo.delete(communication_id)
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete communication: {str(e)}"
        )


@router.get("/communications/follow-ups/pending", response_model=List[CommunicationResponse])
async def get_pending_follow_ups(
    representative_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pending follow-ups"""
    service = CRMService(db)
    communications = await service.get_pending_follow_ups(representative_id)
    return communications


# ===== Segment Endpoints =====

@router.post("/segments", response_model=SegmentResponse, status_code=status.HTTP_201_CREATED)
async def create_segment(
    data: SegmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a customer segment"""
    service = CRMService(db)
    try:
        segment = await service.create_segment(data)
        await db.commit()
        return segment
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create segment: {str(e)}"
        )


@router.get("/segments/{segment_id}", response_model=SegmentResponse)
async def get_segment(
    segment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get segment by ID"""
    service = CRMService(db)
    segment = await service.get_segment(segment_id)
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Segment {segment_id} not found"
        )
    return segment


@router.get("/segments/code/{code}", response_model=SegmentResponse)
async def get_segment_by_code(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get segment by code"""
    service = CRMService(db)
    segment = await service.get_segment_by_code(code)
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Segment {code} not found"
        )
    return segment


@router.get("/segments", response_model=SegmentListResponse)
async def list_segments(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List segments with pagination and filters"""
    service = CRMService(db)
    items, total = await service.list_segments(
        page=page,
        page_size=page_size,
        is_active=is_active,
        search=search
    )

    total_pages = (total + page_size - 1) // page_size
    return SegmentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.put("/segments/{segment_id}", response_model=SegmentResponse)
async def update_segment(
    segment_id: UUID,
    data: SegmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a segment"""
    service = CRMService(db)
    try:
        segment = await service.update_segment(segment_id, data)
        await db.commit()
        return segment
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update segment: {str(e)}"
        )


@router.delete("/segments/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_segment(
    segment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a segment"""
    service = CRMService(db)
    try:
        segment = await service.segment_repo.get_by_id(segment_id)
        if not segment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Segment {segment_id} not found"
            )
        await service.segment_repo.delete(segment_id)
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete segment: {str(e)}"
        )


@router.post("/segments/{segment_id}/assign-customers", status_code=status.HTTP_200_OK)
async def assign_customers_to_segment(
    segment_id: UUID,
    data: SegmentAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign customers to a segment"""
    service = CRMService(db)
    try:
        # Override segment_id from path
        data.segment_id = segment_id
        count = await service.assign_customers_to_segment(data, current_user.id)
        await db.commit()
        return {"message": f"Assigned {count} customers to segment", "count": count}
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign customers: {str(e)}"
        )


@router.post("/segments/{segment_id}/remove-customers", status_code=status.HTTP_200_OK)
async def remove_customers_from_segment(
    segment_id: UUID,
    customer_ids: List[UUID],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove customers from a segment"""
    service = CRMService(db)
    try:
        count = await service.remove_customers_from_segment(segment_id, customer_ids)
        await db.commit()
        return {"message": f"Removed {count} customers from segment", "count": count}
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove customers: {str(e)}"
        )
