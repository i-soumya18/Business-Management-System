"""
CRM Service - Business Logic for B2B CRM Operations

Services for:
- Lead management and qualification
- Sales opportunity tracking and pipeline management
- Customer communication tracking
- Customer segmentation and analytics
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import (
    Lead,
    SalesOpportunity,
    CustomerCommunication,
    CustomerSegment,
    LeadStatus,
    LeadSource,
    LeadPriority,
    OpportunityStage,
    CommunicationType,
    CommunicationDirection
)
from app.models.wholesale import WholesaleCustomer
from app.repositories.crm import (
    LeadRepository,
    SalesOpportunityRepository,
    CustomerCommunicationRepository,
    CustomerSegmentRepository
)
from app.schemas.crm import (
    LeadCreate,
    LeadUpdate,
    LeadQualify,
    LeadConvert,
    OpportunityCreate,
    OpportunityUpdate,
    OpportunityClose,
    CommunicationCreate,
    CommunicationUpdate,
    SegmentCreate,
    SegmentUpdate,
    SegmentAssignment
)


class CRMService:
    """Service for CRM operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.lead_repo = LeadRepository(db)
        self.opportunity_repo = SalesOpportunityRepository(db)
        self.communication_repo = CustomerCommunicationRepository(db)
        self.segment_repo = CustomerSegmentRepository(db)

    # ===== Lead Management =====

    async def create_lead(
        self,
        data: LeadCreate,
        created_by_id: UUID
    ) -> Lead:
        """Create a new lead"""
        # Check for duplicate email
        existing = await self.lead_repo.get_by_email(data.email)
        if existing:
            raise ValueError(f"Lead with email {data.email} already exists")

        # Generate lead number
        lead_number = await self._generate_lead_number()

        # Create lead
        lead_data = data.model_dump()
        lead = Lead(
            lead_number=lead_number,
            created_by_id=created_by_id,
            **lead_data
        )

        self.db.add(lead)
        await self.db.flush()
        await self.db.refresh(lead)

        return lead

    async def update_lead(
        self,
        lead_id: UUID,
        data: LeadUpdate
    ) -> Lead:
        """Update a lead"""
        lead = await self.lead_repo.get_by_id(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        # Check email uniqueness if changed
        if data.email and data.email != lead.email:
            existing = await self.lead_repo.get_by_email(data.email)
            if existing:
                raise ValueError(f"Lead with email {data.email} already exists")

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(lead, key, value)

        await self.db.flush()
        await self.db.refresh(lead)

        return lead

    async def qualify_lead(
        self,
        lead_id: UUID,
        data: LeadQualify
    ) -> Lead:
        """Qualify a lead"""
        lead = await self.lead_repo.get_by_id(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        if lead.status == LeadStatus.CONVERTED:
            raise ValueError("Cannot qualify a converted lead")

        # Update qualification
        lead.qualification_score = data.qualification_score
        lead.is_qualified = data.is_qualified
        lead.status = LeadStatus.QUALIFIED if data.is_qualified else LeadStatus.CONTACTED

        if data.notes:
            if lead.notes:
                lead.notes += f"\n\n[Qualification {datetime.utcnow().isoformat()}]\n{data.notes}"
            else:
                lead.notes = f"[Qualification {datetime.utcnow().isoformat()}]\n{data.notes}"

        await self.db.flush()
        await self.db.refresh(lead)

        return lead

    async def convert_lead(
        self,
        lead_id: UUID,
        data: LeadConvert
    ) -> tuple[Lead, WholesaleCustomer]:
        """Convert a lead to a customer"""
        lead = await self.lead_repo.get_by_id(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        if lead.status == LeadStatus.CONVERTED:
            raise ValueError("Lead is already converted")

        # Verify customer exists
        customer = await self.db.get(WholesaleCustomer, data.customer_id)
        if not customer:
            raise ValueError(f"Customer {data.customer_id} not found")

        # Update lead
        lead.status = LeadStatus.CONVERTED
        lead.converted_to_customer_id = data.customer_id
        lead.converted_at = datetime.utcnow()

        if data.notes:
            if lead.notes:
                lead.notes += f"\n\n[Conversion {datetime.utcnow().isoformat()}]\n{data.notes}"
            else:
                lead.notes = f"[Conversion {datetime.utcnow().isoformat()}]\n{data.notes}"

        await self.db.flush()
        await self.db.refresh(lead)

        return lead, customer

    async def get_lead(self, lead_id: UUID) -> Optional[Lead]:
        """Get lead with relationships"""
        return await self.lead_repo.get_with_relationships(lead_id)

    async def get_lead_by_number(self, lead_number: str) -> Optional[Lead]:
        """Get lead by lead number"""
        return await self.lead_repo.get_by_lead_number(lead_number)

    async def list_leads(
        self,
        page: int = 1,
        page_size: int = 50,
        status: Optional[LeadStatus] = None,
        source: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to_id: Optional[UUID] = None,
        search: Optional[str] = None,
        is_qualified: Optional[bool] = None
    ) -> tuple[List[Lead], int]:
        """List leads with pagination and filters"""
        return await self.lead_repo.get_all_paginated(
            page=page,
            page_size=page_size,
            status=status,
            source=source,
            priority=priority,
            assigned_to_id=assigned_to_id,
            search=search,
            is_qualified=is_qualified
        )

    async def get_leads_for_follow_up(self) -> List[Lead]:
        """Get leads due for follow-up today"""
        today_end = datetime.utcnow().replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
        return await self.lead_repo.get_leads_due_for_follow_up(today_end)

    async def get_lead_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get lead analytics"""
        return await self.lead_repo.get_lead_analytics(start_date, end_date)

    # ===== Opportunity Management =====

    async def create_opportunity(
        self,
        data: OpportunityCreate
    ) -> SalesOpportunity:
        """Create a new sales opportunity"""
        # Verify customer exists
        customer = await self.db.get(WholesaleCustomer, data.customer_id)
        if not customer:
            raise ValueError(f"Customer {data.customer_id} not found")

        # Verify lead if provided
        if data.lead_id:
            lead = await self.lead_repo.get_by_id(data.lead_id)
            if not lead:
                raise ValueError(f"Lead {data.lead_id} not found")

        # Generate opportunity number
        opp_number = await self._generate_opportunity_number()

        # Calculate expected revenue
        expected_revenue = data.estimated_value * (Decimal(data.probability) / 100)

        # Create opportunity
        opp_data = data.model_dump()
        opportunity = SalesOpportunity(
            opportunity_number=opp_number,
            expected_revenue=expected_revenue,
            **opp_data
        )

        self.db.add(opportunity)
        await self.db.flush()
        await self.db.refresh(opportunity)

        return opportunity

    async def update_opportunity(
        self,
        opportunity_id: UUID,
        data: OpportunityUpdate
    ) -> SalesOpportunity:
        """Update an opportunity"""
        opportunity = await self.opportunity_repo.get_by_id(opportunity_id)
        if not opportunity:
            raise ValueError(f"Opportunity {opportunity_id} not found")

        if opportunity.stage in [OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST]:
            raise ValueError("Cannot update a closed opportunity")

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(opportunity, key, value)

        # Recalculate expected revenue if value or probability changed
        if 'estimated_value' in update_data or 'probability' in update_data:
            opportunity.expected_revenue = (
                opportunity.estimated_value * (Decimal(opportunity.probability) / 100)
            )

        await self.db.flush()
        await self.db.refresh(opportunity)

        return opportunity

    async def close_opportunity(
        self,
        opportunity_id: UUID,
        data: OpportunityClose
    ) -> SalesOpportunity:
        """Close an opportunity (won or lost)"""
        opportunity = await self.opportunity_repo.get_by_id(opportunity_id)
        if not opportunity:
            raise ValueError(f"Opportunity {opportunity_id} not found")

        if opportunity.stage in [OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST]:
            raise ValueError("Opportunity is already closed")

        # Update stage and close details
        opportunity.stage = data.stage
        opportunity.actual_close_date = data.actual_close_date

        if data.stage == OpportunityStage.CLOSED_LOST:
            opportunity.loss_reason = data.loss_reason

        if data.notes:
            if opportunity.description:
                opportunity.description += f"\n\n[Closed {data.actual_close_date.isoformat()}]\n{data.notes}"
            else:
                opportunity.description = f"[Closed {data.actual_close_date.isoformat()}]\n{data.notes}"

        await self.db.flush()
        await self.db.refresh(opportunity)

        return opportunity

    async def get_opportunity(self, opportunity_id: UUID) -> Optional[SalesOpportunity]:
        """Get opportunity with relationships"""
        return await self.opportunity_repo.get_with_relationships(opportunity_id)

    async def get_opportunity_by_number(
        self, opportunity_number: str
    ) -> Optional[SalesOpportunity]:
        """Get opportunity by opportunity number"""
        return await self.opportunity_repo.get_by_opportunity_number(opportunity_number)

    async def list_opportunities(
        self,
        page: int = 1,
        page_size: int = 50,
        stage: Optional[OpportunityStage] = None,
        customer_id: Optional[UUID] = None,
        owner_id: Optional[UUID] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        search: Optional[str] = None
    ) -> tuple[List[SalesOpportunity], int]:
        """List opportunities with pagination and filters"""
        return await self.opportunity_repo.get_all_paginated(
            page=page,
            page_size=page_size,
            stage=stage,
            customer_id=customer_id,
            owner_id=owner_id,
            min_value=min_value,
            max_value=max_value,
            search=search
        )

    async def get_pipeline_stats(
        self,
        owner_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get sales pipeline statistics"""
        # Get pipeline value
        pipeline = await self.opportunity_repo.get_pipeline_value(owner_id=owner_id)

        # Get by stage
        by_stage = await self.opportunity_repo.get_opportunities_by_stage(owner_id=owner_id)

        return {
            "total_opportunities": pipeline["count"],
            "total_value": pipeline["total_value"],
            "weighted_value": pipeline["weighted_value"],
            "by_stage": by_stage
        }

    # ===== Communication Management =====

    async def create_communication(
        self,
        data: CommunicationCreate
    ) -> CustomerCommunication:
        """Create a customer communication record"""
        # Verify related entities exist
        if data.customer_id:
            customer = await self.db.get(WholesaleCustomer, data.customer_id)
            if not customer:
                raise ValueError(f"Customer {data.customer_id} not found")

        if data.lead_id:
            lead = await self.lead_repo.get_by_id(data.lead_id)
            if not lead:
                raise ValueError(f"Lead {data.lead_id} not found")

            # Update lead's last contact date
            lead.last_contact_date = data.communication_date
            if data.requires_follow_up and data.follow_up_date:
                lead.next_follow_up_date = data.follow_up_date

        if data.opportunity_id:
            opportunity = await self.opportunity_repo.get_by_id(data.opportunity_id)
            if not opportunity:
                raise ValueError(f"Opportunity {data.opportunity_id} not found")

        # Create communication
        comm_data = data.model_dump()
        communication = CustomerCommunication(**comm_data)

        self.db.add(communication)
        await self.db.flush()
        await self.db.refresh(communication)

        return communication

    async def update_communication(
        self,
        communication_id: UUID,
        data: CommunicationUpdate
    ) -> CustomerCommunication:
        """Update a communication record"""
        communication = await self.communication_repo.get_by_id(communication_id)
        if not communication:
            raise ValueError(f"Communication {communication_id} not found")

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(communication, key, value)

        await self.db.flush()
        await self.db.refresh(communication)

        return communication

    async def mark_follow_up_completed(
        self,
        communication_id: UUID
    ) -> CustomerCommunication:
        """Mark a follow-up as completed"""
        communication = await self.communication_repo.get_by_id(communication_id)
        if not communication:
            raise ValueError(f"Communication {communication_id} not found")

        communication.follow_up_completed = True
        await self.db.flush()
        await self.db.refresh(communication)

        return communication

    async def get_communication(
        self, communication_id: UUID
    ) -> Optional[CustomerCommunication]:
        """Get communication with relationships"""
        return await self.communication_repo.get_with_relationships(communication_id)

    async def list_communications_by_customer(
        self,
        customer_id: UUID,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[CustomerCommunication], int]:
        """List communications for a customer"""
        return await self.communication_repo.get_by_customer(
            customer_id, page, page_size
        )

    async def list_communications_by_lead(
        self,
        lead_id: UUID,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[CustomerCommunication], int]:
        """List communications for a lead"""
        return await self.communication_repo.get_by_lead(lead_id, page, page_size)

    async def list_communications_by_opportunity(
        self,
        opportunity_id: UUID,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[CustomerCommunication], int]:
        """List communications for an opportunity"""
        return await self.communication_repo.get_by_opportunity(
            opportunity_id, page, page_size
        )

    async def get_pending_follow_ups(
        self,
        representative_id: Optional[UUID] = None
    ) -> List[CustomerCommunication]:
        """Get pending follow-ups"""
        today_end = datetime.utcnow().replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
        return await self.communication_repo.get_pending_follow_ups(
            representative_id=representative_id,
            before_date=today_end
        )

    # ===== Segment Management =====

    async def create_segment(self, data: SegmentCreate) -> CustomerSegment:
        """Create a customer segment"""
        # Check for duplicate code
        existing = await self.segment_repo.get_by_code(data.code)
        if existing:
            raise ValueError(f"Segment with code {data.code} already exists")

        # Create segment
        segment_data = data.model_dump()
        segment = CustomerSegment(customer_count=0, **segment_data)

        self.db.add(segment)
        await self.db.flush()
        await self.db.refresh(segment)

        return segment

    async def update_segment(
        self,
        segment_id: UUID,
        data: SegmentUpdate
    ) -> CustomerSegment:
        """Update a segment"""
        segment = await self.segment_repo.get_by_id(segment_id)
        if not segment:
            raise ValueError(f"Segment {segment_id} not found")

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(segment, key, value)

        await self.db.flush()
        await self.db.refresh(segment)

        return segment

    async def get_segment(self, segment_id: UUID) -> Optional[CustomerSegment]:
        """Get segment by ID"""
        return await self.segment_repo.get_by_id(segment_id)

    async def get_segment_by_code(self, code: str) -> Optional[CustomerSegment]:
        """Get segment by code"""
        return await self.segment_repo.get_by_code(code)

    async def list_segments(
        self,
        page: int = 1,
        page_size: int = 50,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> tuple[List[CustomerSegment], int]:
        """List segments with pagination and filters"""
        return await self.segment_repo.get_all_paginated(
            page=page,
            page_size=page_size,
            is_active=is_active,
            search=search
        )

    async def assign_customers_to_segment(
        self,
        data: SegmentAssignment,
        assigned_by_id: UUID
    ) -> int:
        """Assign customers to a segment"""
        segment = await self.segment_repo.get_by_id(data.segment_id)
        if not segment:
            raise ValueError(f"Segment {data.segment_id} not found")

        # Assign customers
        count = await self.segment_repo.assign_customers(
            segment_id=data.segment_id,
            customer_ids=data.customer_ids,
            assigned_by_id=assigned_by_id
        )

        # Update customer count
        segment.customer_count += count
        await self.db.flush()

        return count

    async def remove_customers_from_segment(
        self,
        segment_id: UUID,
        customer_ids: List[UUID]
    ) -> int:
        """Remove customers from a segment"""
        segment = await self.segment_repo.get_by_id(segment_id)
        if not segment:
            raise ValueError(f"Segment {segment_id} not found")

        # Remove customers
        count = await self.segment_repo.remove_customers(
            segment_id=segment_id,
            customer_ids=customer_ids
        )

        # Update customer count
        segment.customer_count = max(0, segment.customer_count - count)
        await self.db.flush()

        return count

    async def get_segment_customers(
        self,
        segment_id: UUID,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[WholesaleCustomer], int]:
        """Get customers in a segment"""
        return await self.segment_repo.get_segment_customers(
            segment_id, page, page_size
        )

    # ===== Helper Methods =====

    async def _generate_lead_number(self) -> str:
        """Generate unique lead number"""
        from sqlalchemy import func, select

        # Get count for today
        today = datetime.utcnow().date()
        count_query = select(func.count()).select_from(Lead).where(
            func.date(Lead.created_at) == today
        )
        count = await self.db.scalar(count_query) or 0

        # Format: LEAD-YYYYMMDD-XXXX
        return f"LEAD-{today.strftime('%Y%m%d')}-{count + 1:04d}"

    async def _generate_opportunity_number(self) -> str:
        """Generate unique opportunity number"""
        from sqlalchemy import func, select

        # Get count for today
        today = datetime.utcnow().date()
        count_query = select(func.count()).select_from(SalesOpportunity).where(
            func.date(SalesOpportunity.created_at) == today
        )
        count = await self.db.scalar(count_query) or 0

        # Format: OPP-YYYYMMDD-XXXX
        return f"OPP-{today.strftime('%Y%m%d')}-{count + 1:04d}"
