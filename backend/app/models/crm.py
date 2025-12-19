"""
CRM Models - B2B Lead Management, Opportunities, and Customer Communications

Models for comprehensive B2B customer relationship management including:
- Lead management and qualification
- Sales opportunity tracking (pipeline)
- Customer communication logs
- Customer segmentation
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4
from enum import Enum as PyEnum
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, String, Text, UUID, Numeric, Integer,
    ForeignKey, Index, Enum, JSON, Date, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.wholesale import WholesaleCustomer


class LeadStatus(str, PyEnum):
    """Lead Status in the sales pipeline"""
    NEW = "new"  # New lead, not contacted yet
    CONTACTED = "contacted"  # Initial contact made
    QUALIFIED = "qualified"  # Qualified as potential customer
    PROPOSAL_SENT = "proposal_sent"  # Proposal/quote sent
    NEGOTIATION = "negotiation"  # In negotiation phase
    CONVERTED = "converted"  # Converted to customer
    LOST = "lost"  # Lead lost
    DISQUALIFIED = "disqualified"  # Not a good fit


class LeadSource(str, PyEnum):
    """Source of the lead"""
    WEBSITE = "website"  # Website inquiry
    REFERRAL = "referral"  # Referred by existing customer
    TRADE_SHOW = "trade_show"  # Met at trade show
    COLD_CALL = "cold_call"  # Cold calling
    EMAIL_CAMPAIGN = "email_campaign"  # Email marketing
    SOCIAL_MEDIA = "social_media"  # Social media
    PARTNER = "partner"  # Business partner referral
    WALK_IN = "walk_in"  # Walk-in customer
    OTHER = "other"  # Other source


class LeadPriority(str, PyEnum):
    """Lead priority level"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class OpportunityStage(str, PyEnum):
    """Sales opportunity stage"""
    PROSPECTING = "prospecting"  # Initial stage
    QUALIFICATION = "qualification"  # Qualifying the opportunity
    NEEDS_ANALYSIS = "needs_analysis"  # Understanding needs
    PROPOSAL = "proposal"  # Proposal/quote sent
    NEGOTIATION = "negotiation"  # Negotiating terms
    CLOSED_WON = "closed_won"  # Deal won
    CLOSED_LOST = "closed_lost"  # Deal lost


class CommunicationType(str, PyEnum):
    """Type of communication"""
    EMAIL = "email"
    PHONE = "phone"
    MEETING = "meeting"
    VIDEO_CALL = "video_call"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    VISIT = "visit"  # In-person visit
    NOTE = "note"  # Internal note
    OTHER = "other"


class CommunicationDirection(str, PyEnum):
    """Direction of communication"""
    INBOUND = "inbound"  # Customer to us
    OUTBOUND = "outbound"  # Us to customer


class Lead(Base):
    """
    Lead Model for B2B lead management
    
    Tracks potential customers from initial contact through qualification
    to conversion.
    """
    __tablename__ = "leads"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Lead Identification
    lead_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Company Information
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    company_size: Mapped[Optional[str]] = mapped_column(String(50))  # Small, Medium, Large
    website: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Contact Information
    contact_person: Mapped[str] = mapped_column(String(255), nullable=False)
    title_position: Mapped[Optional[str]] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    alternate_phone: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(255))
    address_line2: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    state: Mapped[Optional[str]] = mapped_column(String(100))
    postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="India")
    
    # Lead Details
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, native_enum=False, length=50),
        nullable=False,
        default=LeadStatus.NEW,
        index=True
    )
    source: Mapped[LeadSource] = mapped_column(
        Enum(LeadSource, native_enum=False, length=50),
        nullable=False,
        index=True
    )
    priority: Mapped[LeadPriority] = mapped_column(
        Enum(LeadPriority, native_enum=False, length=50),
        nullable=False,
        default=LeadPriority.MEDIUM
    )
    
    # Lead Qualification
    is_qualified: Mapped[bool] = mapped_column(Boolean, default=False)
    qualification_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100
    estimated_deal_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    estimated_close_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Requirements & Notes
    requirements: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[dict]] = mapped_column(JSON)  # Flexible tagging
    
    # Assignment
    assigned_to_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True
    )
    
    # Conversion
    converted_to_customer_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wholesale_customers.id", ondelete="SET NULL"),
        index=True
    )
    converted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Follow-up
    next_follow_up_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_contact_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    created_by_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # Relationships
    assigned_to: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_to_id],
        back_populates="assigned_leads"
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id]
    )
    converted_customer: Mapped[Optional["WholesaleCustomer"]] = relationship(
        "WholesaleCustomer",
        foreign_keys=[converted_to_customer_id]
    )
    communications: Mapped[list["CustomerCommunication"]] = relationship(
        "CustomerCommunication",
        back_populates="lead",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_lead_status_priority", "status", "priority"),
        Index("idx_lead_assigned_status", "assigned_to_id", "status"),
        Index("idx_lead_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Lead {self.lead_number}: {self.company_name} - {self.status}>"


class SalesOpportunity(Base):
    """
    Sales Opportunity Model - Sales Pipeline Management
    
    Tracks specific sales opportunities with customers through the sales pipeline
    from prospecting to close.
    """
    __tablename__ = "sales_opportunities"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Opportunity Identification
    opportunity_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Customer Relation
    customer_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wholesale_customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Or from a Lead (if not yet converted)
    lead_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        index=True
    )
    
    # Opportunity Details
    stage: Mapped[OpportunityStage] = mapped_column(
        Enum(OpportunityStage, native_enum=False, length=50),
        nullable=False,
        default=OpportunityStage.PROSPECTING,
        index=True
    )
    
    # Financial Details
    estimated_value: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    probability: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50
    )  # 0-100% probability of closing
    expected_revenue: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )  # estimated_value * probability
    
    # Timeline
    expected_close_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    actual_close_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Assignment
    owner_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Competition & Risks
    competitors: Mapped[Optional[str]] = mapped_column(Text)  # Competing vendors
    risks: Mapped[Optional[str]] = mapped_column(Text)  # Identified risks
    
    # Products/Services
    products_interested: Mapped[Optional[dict]] = mapped_column(JSON)  # Product categories
    
    # Next Steps
    next_step: Mapped[Optional[str]] = mapped_column(Text)
    next_step_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Loss Reason (if lost)
    loss_reason: Mapped[Optional[str]] = mapped_column(Text)
    
    # Tags & Custom Fields
    tags: Mapped[Optional[dict]] = mapped_column(JSON)
    custom_fields: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    customer: Mapped["WholesaleCustomer"] = relationship(
        "WholesaleCustomer",
        back_populates="opportunities"
    )
    lead: Mapped[Optional["Lead"]] = relationship("Lead")
    owner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[owner_id],
        back_populates="owned_opportunities"
    )
    communications: Mapped[list["CustomerCommunication"]] = relationship(
        "CustomerCommunication",
        back_populates="opportunity",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_opportunity_customer_stage", "customer_id", "stage"),
        Index("idx_opportunity_owner_stage", "owner_id", "stage"),
        Index("idx_opportunity_expected_close", "expected_close_date"),
        CheckConstraint("probability >= 0 AND probability <= 100", name="check_probability_range"),
    )
    
    def __repr__(self) -> str:
        return f"<Opportunity {self.opportunity_number}: {self.name} - {self.stage}>"


class CustomerCommunication(Base):
    """
    Customer Communication Log
    
    Tracks all interactions with customers and leads including emails, calls,
    meetings, and other communication types.
    """
    __tablename__ = "customer_communications"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Related Entity (Customer, Lead, or Opportunity)
    customer_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wholesale_customers.id", ondelete="CASCADE"),
        index=True
    )
    lead_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        index=True
    )
    opportunity_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_opportunities.id", ondelete="CASCADE"),
        index=True
    )
    
    # Communication Details
    type: Mapped[CommunicationType] = mapped_column(
        Enum(CommunicationType, native_enum=False, length=50),
        nullable=False,
        index=True
    )
    direction: Mapped[CommunicationDirection] = mapped_column(
        Enum(CommunicationDirection, native_enum=False, length=50),
        nullable=False
    )
    
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Participants
    contact_person: Mapped[Optional[str]] = mapped_column(String(255))
    our_representative_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Timing
    communication_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)  # For calls/meetings
    
    # Follow-up
    requires_follow_up: Mapped[bool] = mapped_column(Boolean, default=False)
    follow_up_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    follow_up_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Attachments & References
    attachments: Mapped[Optional[dict]] = mapped_column(JSON)  # File references
    related_order_id: Mapped[Optional[uuid4]] = mapped_column(UUID(as_uuid=True))
    
    # Tags
    tags: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    customer: Mapped[Optional["WholesaleCustomer"]] = relationship(
        "WholesaleCustomer",
        back_populates="communications"
    )
    lead: Mapped[Optional["Lead"]] = relationship(
        "Lead",
        back_populates="communications"
    )
    opportunity: Mapped[Optional["SalesOpportunity"]] = relationship(
        "SalesOpportunity",
        back_populates="communications"
    )
    our_representative: Mapped["User"] = relationship(
        "User",
        foreign_keys=[our_representative_id]
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_comm_customer_date", "customer_id", "communication_date"),
        Index("idx_comm_lead_date", "lead_id", "communication_date"),
        Index("idx_comm_opportunity_date", "opportunity_id", "communication_date"),
        Index("idx_comm_rep_date", "our_representative_id", "communication_date"),
        Index("idx_comm_follow_up", "requires_follow_up", "follow_up_date"),
        CheckConstraint(
            "(customer_id IS NOT NULL) OR (lead_id IS NOT NULL) OR (opportunity_id IS NOT NULL)",
            name="check_related_entity_exists"
        ),
    )
    
    def __repr__(self) -> str:
        return f"<Communication {self.type}: {self.subject}>"


class CustomerSegment(Base):
    """
    Customer Segmentation Model
    
    Allows grouping customers into segments for targeted marketing,
    pricing strategies, and analytics.
    """
    __tablename__ = "customer_segments"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Segment Details
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    
    # Segment Criteria (stored as JSON for flexibility)
    criteria: Mapped[Optional[dict]] = mapped_column(JSON)
    # Example: {"min_total_spent": 100000, "min_orders": 10, "customer_type": ["retailer"]}
    
    # Segment Attributes
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)  # For ordering
    
    # Benefits/Actions for this segment
    benefits: Mapped[Optional[dict]] = mapped_column(JSON)
    # Example: {"discount": 15, "payment_terms": "net_60", "free_shipping": true}
    
    # Statistics
    customer_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    customers: Mapped[list["WholesaleCustomer"]] = relationship(
        "WholesaleCustomer",
        secondary="customer_segment_mapping",
        back_populates="segments"
    )
    
    def __repr__(self) -> str:
        return f"<CustomerSegment {self.code}: {self.name}>"


class CustomerSegmentMapping(Base):
    """
    Many-to-Many mapping between customers and segments
    """
    __tablename__ = "customer_segment_mapping"
    
    customer_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wholesale_customers.id", ondelete="CASCADE"),
        primary_key=True
    )
    segment_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_segments.id", ondelete="CASCADE"),
        primary_key=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    assigned_by_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_segment_mapping_customer", "customer_id"),
        Index("idx_segment_mapping_segment", "segment_id"),
    )
