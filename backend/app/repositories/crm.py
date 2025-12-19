"""
CRM Repositories - B2B Lead, Opportunity, Communication, Segment Management

Async repositories for:
- Lead management and qualification
- Sales opportunity tracking
- Customer communication logging
- Customer segmentation
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func, and_, or_, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.crm import (
    Lead,
    SalesOpportunity,
    CustomerCommunication,
    CustomerSegment,
    CustomerSegmentMapping,
    LeadStatus,
    OpportunityStage
)
from app.models.wholesale import WholesaleCustomer
from app.repositories.base import BaseRepository


class LeadRepository(BaseRepository[Lead]):
    """Repository for Lead operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(Lead, db)

    async def get_by_lead_number(self, lead_number: str) -> Optional[Lead]:
        """Get lead by lead number"""
        query = select(Lead).where(Lead.lead_number == lead_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Lead]:
        """Get lead by email"""
        query = select(Lead).where(Lead.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_relationships(self, lead_id: UUID) -> Optional[Lead]:
        """Get lead with related data"""
        query = (
            select(Lead)
            .options(
                selectinload(Lead.assigned_to),
                selectinload(Lead.converted_to_customer),
                selectinload(Lead.communications),
                selectinload(Lead.opportunities)
            )
            .where(Lead.id == lead_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_paginated(
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
        """Get paginated leads with filters"""
        query = select(Lead).options(
            selectinload(Lead.assigned_to),
            selectinload(Lead.converted_to_customer)
        )

        # Apply filters
        conditions = []
        if status:
            conditions.append(Lead.status == status)
        if source:
            conditions.append(Lead.source == source)
        if priority:
            conditions.append(Lead.priority == priority)
        if assigned_to_id:
            conditions.append(Lead.assigned_to_id == assigned_to_id)
        if is_qualified is not None:
            conditions.append(Lead.is_qualified == is_qualified)
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    Lead.company_name.ilike(search_pattern),
                    Lead.contact_person.ilike(search_pattern),
                    Lead.email.ilike(search_pattern),
                    Lead.lead_number.ilike(search_pattern)
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count()).select_from(Lead)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)

        # Apply pagination
        query = query.order_by(desc(Lead.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total or 0

    async def get_leads_due_for_follow_up(
        self, before_date: datetime
    ) -> List[Lead]:
        """Get leads due for follow-up before given date"""
        query = (
            select(Lead)
            .where(
                and_(
                    Lead.next_follow_up_date <= before_date,
                    Lead.status.in_([LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.QUALIFIED])
                )
            )
            .options(selectinload(Lead.assigned_to))
            .order_by(Lead.next_follow_up_date)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_lead_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get lead analytics"""
        conditions = []
        if start_date:
            conditions.append(Lead.created_at >= start_date)
        if end_date:
            conditions.append(Lead.created_at <= end_date)

        base_query = select(Lead)
        if conditions:
            base_query = base_query.where(and_(*conditions))

        # Total leads
        total = await self.db.scalar(
            select(func.count()).select_from(base_query.subquery())
        )

        # By status
        status_query = (
            select(Lead.status, func.count())
            .select_from(base_query.subquery())
            .group_by(Lead.status)
        )
        status_result = await self.db.execute(status_query)
        by_status = {str(status): count for status, count in status_result.all()}

        # By source
        source_query = (
            select(Lead.source, func.count())
            .select_from(base_query.subquery())
            .group_by(Lead.source)
        )
        source_result = await self.db.execute(source_query)
        by_source = {str(source): count for source, count in source_result.all()}

        # Conversion rate
        converted_count = await self.db.scalar(
            select(func.count())
            .select_from(base_query.subquery())
            .where(Lead.status == LeadStatus.CONVERTED)
        )
        conversion_rate = (converted_count / total * 100) if total > 0 else 0.0

        return {
            "total_leads": total or 0,
            "by_status": by_status,
            "by_source": by_source,
            "conversion_rate": round(conversion_rate, 2)
        }


class SalesOpportunityRepository(BaseRepository[SalesOpportunity]):
    """Repository for Sales Opportunity operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(SalesOpportunity, db)

    async def get_by_opportunity_number(
        self, opportunity_number: str
    ) -> Optional[SalesOpportunity]:
        """Get opportunity by opportunity number"""
        query = select(SalesOpportunity).where(
            SalesOpportunity.opportunity_number == opportunity_number
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_relationships(
        self, opportunity_id: UUID
    ) -> Optional[SalesOpportunity]:
        """Get opportunity with related data"""
        query = (
            select(SalesOpportunity)
            .options(
                selectinload(SalesOpportunity.customer),
                selectinload(SalesOpportunity.lead),
                selectinload(SalesOpportunity.owner),
                selectinload(SalesOpportunity.communications)
            )
            .where(SalesOpportunity.id == opportunity_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_paginated(
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
        """Get paginated opportunities with filters"""
        query = select(SalesOpportunity).options(
            selectinload(SalesOpportunity.customer),
            selectinload(SalesOpportunity.owner)
        )

        # Apply filters
        conditions = []
        if stage:
            conditions.append(SalesOpportunity.stage == stage)
        if customer_id:
            conditions.append(SalesOpportunity.customer_id == customer_id)
        if owner_id:
            conditions.append(SalesOpportunity.owner_id == owner_id)
        if min_value is not None:
            conditions.append(SalesOpportunity.estimated_value >= min_value)
        if max_value is not None:
            conditions.append(SalesOpportunity.estimated_value <= max_value)
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    SalesOpportunity.name.ilike(search_pattern),
                    SalesOpportunity.opportunity_number.ilike(search_pattern)
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count()).select_from(SalesOpportunity)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)

        # Apply pagination
        query = query.order_by(desc(SalesOpportunity.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total or 0

    async def get_pipeline_value(
        self,
        stage: Optional[OpportunityStage] = None,
        owner_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get pipeline value statistics"""
        conditions = []
        if stage:
            conditions.append(SalesOpportunity.stage == stage)
        if owner_id:
            conditions.append(SalesOpportunity.owner_id == owner_id)

        # Open opportunities only
        conditions.append(
            SalesOpportunity.stage.not_in([
                OpportunityStage.CLOSED_WON,
                OpportunityStage.CLOSED_LOST
            ])
        )

        query = select(
            func.count(SalesOpportunity.id),
            func.sum(SalesOpportunity.estimated_value),
            func.sum(SalesOpportunity.expected_revenue)
        )
        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        count, total_value, weighted_value = result.one()

        return {
            "count": count or 0,
            "total_value": float(total_value or 0),
            "weighted_value": float(weighted_value or 0)
        }

    async def get_opportunities_by_stage(
        self, owner_id: Optional[UUID] = None
    ) -> Dict[str, int]:
        """Get opportunity count by stage"""
        query = select(
            SalesOpportunity.stage,
            func.count(SalesOpportunity.id)
        ).group_by(SalesOpportunity.stage)

        if owner_id:
            query = query.where(SalesOpportunity.owner_id == owner_id)

        result = await self.db.execute(query)
        return {str(stage): count for stage, count in result.all()}


class CustomerCommunicationRepository(BaseRepository[CustomerCommunication]):
    """Repository for Customer Communication operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(CustomerCommunication, db)

    async def get_with_relationships(
        self, communication_id: UUID
    ) -> Optional[CustomerCommunication]:
        """Get communication with related data"""
        query = (
            select(CustomerCommunication)
            .options(
                selectinload(CustomerCommunication.customer),
                selectinload(CustomerCommunication.lead),
                selectinload(CustomerCommunication.opportunity),
                selectinload(CustomerCommunication.our_representative)
            )
            .where(CustomerCommunication.id == communication_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_customer(
        self,
        customer_id: UUID,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[CustomerCommunication], int]:
        """Get communications for a customer"""
        query = (
            select(CustomerCommunication)
            .where(CustomerCommunication.customer_id == customer_id)
            .options(selectinload(CustomerCommunication.our_representative))
            .order_by(desc(CustomerCommunication.communication_date))
        )

        # Get total count
        count_query = select(func.count()).select_from(CustomerCommunication).where(
            CustomerCommunication.customer_id == customer_id
        )
        total = await self.db.scalar(count_query)

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total or 0

    async def get_by_lead(
        self,
        lead_id: UUID,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[CustomerCommunication], int]:
        """Get communications for a lead"""
        query = (
            select(CustomerCommunication)
            .where(CustomerCommunication.lead_id == lead_id)
            .options(selectinload(CustomerCommunication.our_representative))
            .order_by(desc(CustomerCommunication.communication_date))
        )

        # Get total count
        count_query = select(func.count()).select_from(CustomerCommunication).where(
            CustomerCommunication.lead_id == lead_id
        )
        total = await self.db.scalar(count_query)

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total or 0

    async def get_by_opportunity(
        self,
        opportunity_id: UUID,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[CustomerCommunication], int]:
        """Get communications for an opportunity"""
        query = (
            select(CustomerCommunication)
            .where(CustomerCommunication.opportunity_id == opportunity_id)
            .options(selectinload(CustomerCommunication.our_representative))
            .order_by(desc(CustomerCommunication.communication_date))
        )

        # Get total count
        count_query = select(func.count()).select_from(CustomerCommunication).where(
            CustomerCommunication.opportunity_id == opportunity_id
        )
        total = await self.db.scalar(count_query)

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total or 0

    async def get_pending_follow_ups(
        self,
        representative_id: Optional[UUID] = None,
        before_date: Optional[datetime] = None
    ) -> List[CustomerCommunication]:
        """Get communications with pending follow-ups"""
        conditions = [
            CustomerCommunication.requires_follow_up == True,
            CustomerCommunication.follow_up_completed == False
        ]

        if representative_id:
            conditions.append(
                CustomerCommunication.our_representative_id == representative_id
            )
        if before_date:
            conditions.append(CustomerCommunication.follow_up_date <= before_date)

        query = (
            select(CustomerCommunication)
            .where(and_(*conditions))
            .options(
                selectinload(CustomerCommunication.customer),
                selectinload(CustomerCommunication.lead),
                selectinload(CustomerCommunication.opportunity)
            )
            .order_by(CustomerCommunication.follow_up_date)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())


class CustomerSegmentRepository(BaseRepository[CustomerSegment]):
    """Repository for Customer Segment operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(CustomerSegment, db)

    async def get_by_code(self, code: str) -> Optional[CustomerSegment]:
        """Get segment by code"""
        query = select(CustomerSegment).where(CustomerSegment.code == code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_active_segments(self) -> List[CustomerSegment]:
        """Get all active segments"""
        query = (
            select(CustomerSegment)
            .where(CustomerSegment.is_active == True)
            .order_by(desc(CustomerSegment.priority), CustomerSegment.name)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_all_paginated(
        self,
        page: int = 1,
        page_size: int = 50,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> tuple[List[CustomerSegment], int]:
        """Get paginated segments with filters"""
        query = select(CustomerSegment)

        # Apply filters
        conditions = []
        if is_active is not None:
            conditions.append(CustomerSegment.is_active == is_active)
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    CustomerSegment.name.ilike(search_pattern),
                    CustomerSegment.code.ilike(search_pattern)
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count()).select_from(CustomerSegment)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)

        # Apply pagination and ordering
        query = query.order_by(
            desc(CustomerSegment.priority),
            CustomerSegment.name
        )
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total or 0

    async def assign_customers(
        self,
        segment_id: UUID,
        customer_ids: List[UUID],
        assigned_by_id: UUID
    ) -> int:
        """Assign multiple customers to a segment"""
        from app.models.crm import CustomerSegmentMapping

        mappings = []
        for customer_id in customer_ids:
            # Check if already exists
            existing = await self.db.execute(
                select(CustomerSegmentMapping).where(
                    and_(
                        CustomerSegmentMapping.customer_id == customer_id,
                        CustomerSegmentMapping.segment_id == segment_id
                    )
                )
            )
            if not existing.scalar_one_or_none():
                mappings.append(
                    CustomerSegmentMapping(
                        customer_id=customer_id,
                        segment_id=segment_id,
                        assigned_by_id=assigned_by_id
                    )
                )

        if mappings:
            self.db.add_all(mappings)
            await self.db.flush()

        return len(mappings)

    async def remove_customers(
        self,
        segment_id: UUID,
        customer_ids: List[UUID]
    ) -> int:
        """Remove customers from a segment"""
        from sqlalchemy import delete
        from app.models.crm import CustomerSegmentMapping

        stmt = delete(CustomerSegmentMapping).where(
            and_(
                CustomerSegmentMapping.segment_id == segment_id,
                CustomerSegmentMapping.customer_id.in_(customer_ids)
            )
        )
        result = await self.db.execute(stmt)
        return result.rowcount

    async def get_segment_customers(
        self,
        segment_id: UUID,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[WholesaleCustomer], int]:
        """Get customers in a segment"""
        from app.models.crm import CustomerSegmentMapping

        # Get total count
        count_query = (
            select(func.count())
            .select_from(CustomerSegmentMapping)
            .where(CustomerSegmentMapping.segment_id == segment_id)
        )
        total = await self.db.scalar(count_query)

        # Get customers
        query = (
            select(WholesaleCustomer)
            .join(
                CustomerSegmentMapping,
                CustomerSegmentMapping.customer_id == WholesaleCustomer.id
            )
            .where(CustomerSegmentMapping.segment_id == segment_id)
            .order_by(WholesaleCustomer.company_name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total or 0
