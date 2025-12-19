"""
Comprehensive Tests for B2B CRM Module

Test coverage:
- Lead management (CRUD, qualification, conversion)
- Sales opportunity tracking (CRUD, pipeline, closing)
- Customer communications (CRUD, follow-ups)
- Customer segmentation (CRUD, assignments)
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from httpx import AsyncClient

from app.models.crm import (
    LeadStatus,
    LeadSource,
    LeadPriority,
    OpportunityStage,
    CommunicationType,
    CommunicationDirection
)


# ===== Test Lead Management =====

@pytest.mark.asyncio
async def test_create_lead(client: AsyncClient, auth_headers: dict):
    """Test creating a new lead"""
    lead_data = {
        "company_name": "Test Company Ltd",
        "industry": "Retail",
        "company_size": "50-100",
        "website": "https://testcompany.com",
        "contact_person": "John Doe",
        "title_position": "Purchasing Manager",
        "email": "john.doe@testcompany.com",
        "phone": "+911234567890",
        "city": "Mumbai",
        "state": "Maharashtra",
        "country": "India",
        "source": LeadSource.WEBSITE.value,
        "priority": LeadPriority.HIGH.value,
        "estimated_deal_value": 50000.00,
        "requirements": "Looking for wholesale garments for retail chain"
    }

    response = await client.post("/api/v1/crm/leads", json=lead_data, headers=auth_headers)
    assert response.status_code == 201

    data = response.json()
    assert data["company_name"] == lead_data["company_name"]
    assert data["email"] == lead_data["email"]
    assert data["status"] == LeadStatus.NEW.value
    assert "lead_number" in data
    assert data["lead_number"].startswith("LEAD-")
    assert data["is_qualified"] == False


@pytest.mark.asyncio
async def test_create_duplicate_lead(client: AsyncClient, auth_headers: dict):
    """Test creating lead with duplicate email"""
    lead_data = {
        "company_name": "Test Company",
        "contact_person": "Jane Smith",
        "email": "duplicate@example.com",
        "phone": "+911234567890",
        "source": LeadSource.REFERRAL.value
    }

    # Create first lead
    response1 = await client.post("/api/v1/crm/leads", json=lead_data, headers=auth_headers)
    assert response1.status_code == 201

    # Try to create duplicate
    response2 = await client.post("/api/v1/crm/leads", json=lead_data, headers=auth_headers)
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_get_lead(client: AsyncClient, auth_headers: dict, test_lead):
    """Test retrieving a lead"""
    response = await client.get(f"/api/v1/crm/leads/{test_lead.id}", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == str(test_lead.id)
    assert data["company_name"] == test_lead.company_name


@pytest.mark.asyncio
async def test_get_lead_by_number(client: AsyncClient, auth_headers: dict, test_lead):
    """Test retrieving lead by lead number"""
    response = await client.get(
        f"/api/v1/crm/leads/number/{test_lead.lead_number}",
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["lead_number"] == test_lead.lead_number


@pytest.mark.asyncio
async def test_list_leads(client: AsyncClient, auth_headers: dict, test_lead):
    """Test listing leads with pagination"""
    response = await client.get("/api/v1/crm/leads?page=1&page_size=10", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert len(data["items"]) > 0


@pytest.mark.asyncio
async def test_list_leads_with_filters(client: AsyncClient, auth_headers: dict, test_lead):
    """Test listing leads with filters"""
    response = await client.get(
        f"/api/v1/crm/leads?status={LeadStatus.NEW.value}&search=Test",
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    # Verify all returned leads match the filter
    for lead in data["items"]:
        assert lead["status"] == LeadStatus.NEW.value


@pytest.mark.asyncio
async def test_update_lead(client: AsyncClient, auth_headers: dict, test_lead):
    """Test updating a lead"""
    update_data = {
        "priority": LeadPriority.URGENT.value,
        "estimated_deal_value": 75000.00,
        "notes": "Updated requirements - needs urgent attention"
    }

    response = await client.put(
        f"/api/v1/crm/leads/{test_lead.id}",
        json=update_data,
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["priority"] == LeadPriority.URGENT.value
    assert float(data["estimated_deal_value"]) == 75000.00


@pytest.mark.asyncio
async def test_qualify_lead(client: AsyncClient, auth_headers: dict, test_lead):
    """Test qualifying a lead"""
    qualify_data = {
        "qualification_score": 85,
        "is_qualified": True,
        "notes": "Strong prospect - ready for sales team"
    }

    response = await client.post(
        f"/api/v1/crm/leads/{test_lead.id}/qualify",
        json=qualify_data,
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["is_qualified"] == True
    assert data["qualification_score"] == 85
    assert data["status"] == LeadStatus.QUALIFIED.value


@pytest.mark.asyncio
async def test_convert_lead(
    client: AsyncClient,
    auth_headers: dict,
    test_lead,
    test_wholesale_customer
):
    """Test converting lead to customer"""
    # First qualify the lead
    await client.post(
        f"/api/v1/crm/leads/{test_lead.id}/qualify",
        json={"qualification_score": 90, "is_qualified": True},
        headers=auth_headers
    )

    # Convert to customer
    convert_data = {
        "customer_id": str(test_wholesale_customer.id),
        "notes": "Converted successfully - initial order placed"
    }

    response = await client.post(
        f"/api/v1/crm/leads/{test_lead.id}/convert",
        json=convert_data,
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == LeadStatus.CONVERTED.value
    assert data["converted_to_customer_id"] == str(test_wholesale_customer.id)
    assert data["converted_at"] is not None


@pytest.mark.asyncio
async def test_delete_lead(client: AsyncClient, auth_headers: dict, test_lead):
    """Test deleting a lead"""
    response = await client.delete(f"/api/v1/crm/leads/{test_lead.id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify deletion
    get_response = await client.get(f"/api/v1/crm/leads/{test_lead.id}", headers=auth_headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_get_leads_for_follow_up(client: AsyncClient, auth_headers: dict, db_session):
    """Test getting leads due for follow-up"""
    from app.models.crm import Lead

    # Create lead with follow-up date today
    lead = Lead(
        lead_number="LEAD-TEST-001",
        company_name="Follow-up Test Co",
        contact_person="Test Contact",
        email="followup@test.com",
        phone="+911234567890",
        source=LeadSource.PHONE,
        status=LeadStatus.CONTACTED,
        next_follow_up_date=datetime.utcnow()
    )
    db_session.add(lead)
    await db_session.commit()

    response = await client.get("/api/v1/crm/leads/follow-ups/today", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    # Should include our test lead
    lead_ids = [item["id"] for item in data]
    assert str(lead.id) in lead_ids


@pytest.mark.asyncio
async def test_get_lead_analytics(client: AsyncClient, auth_headers: dict, test_lead):
    """Test getting lead analytics"""
    response = await client.get("/api/v1/crm/leads/analytics/summary", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "total_leads" in data
    assert "by_status" in data
    assert "by_source" in data
    assert "conversion_rate" in data


# ===== Test Opportunity Management =====

@pytest.mark.asyncio
async def test_create_opportunity(
    client: AsyncClient,
    auth_headers: dict,
    test_wholesale_customer,
    test_user
):
    """Test creating a sales opportunity"""
    opp_data = {
        "name": "Q4 Bulk Order - Winter Collection",
        "description": "Potential order for winter garments",
        "customer_id": str(test_wholesale_customer.id),
        "owner_id": str(test_user.id),
        "estimated_value": 150000.00,
        "probability": 70,
        "expected_close_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "stage": OpportunityStage.PROPOSAL.value,
        "products_interested": {
            "categories": ["Jackets", "Sweaters", "Hoodies"],
            "estimated_quantity": 500
        }
    }

    response = await client.post("/api/v1/crm/opportunities", json=opp_data, headers=auth_headers)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == opp_data["name"]
    assert float(data["estimated_value"]) == 150000.00
    assert data["probability"] == 70
    assert "opportunity_number" in data
    assert data["opportunity_number"].startswith("OPP-")
    # Expected revenue should be calculated
    assert float(data["expected_revenue"]) == 150000.00 * 0.70


@pytest.mark.asyncio
async def test_get_opportunity(client: AsyncClient, auth_headers: dict, test_opportunity):
    """Test retrieving an opportunity"""
    response = await client.get(
        f"/api/v1/crm/opportunities/{test_opportunity.id}",
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == str(test_opportunity.id)
    assert data["name"] == test_opportunity.name


@pytest.mark.asyncio
async def test_list_opportunities(client: AsyncClient, auth_headers: dict, test_opportunity):
    """Test listing opportunities with pagination"""
    response = await client.get(
        "/api/v1/crm/opportunities?page=1&page_size=10",
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) > 0


@pytest.mark.asyncio
async def test_list_opportunities_with_filters(
    client: AsyncClient,
    auth_headers: dict,
    test_opportunity
):
    """Test listing opportunities with filters"""
    response = await client.get(
        f"/api/v1/crm/opportunities?stage={OpportunityStage.PROSPECTING.value}",
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_update_opportunity(client: AsyncClient, auth_headers: dict, test_opportunity):
    """Test updating an opportunity"""
    update_data = {
        "stage": OpportunityStage.NEGOTIATION.value,
        "probability": 80,
        "next_step": "Send revised proposal with pricing",
        "next_step_date": (datetime.utcnow() + timedelta(days=3)).isoformat()
    }

    response = await client.put(
        f"/api/v1/crm/opportunities/{test_opportunity.id}",
        json=update_data,
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["stage"] == OpportunityStage.NEGOTIATION.value
    assert data["probability"] == 80
    # Expected revenue should be recalculated
    expected_revenue = float(test_opportunity.estimated_value) * 0.80
    assert abs(float(data["expected_revenue"]) - expected_revenue) < 0.01


@pytest.mark.asyncio
async def test_close_opportunity_won(client: AsyncClient, auth_headers: dict, test_opportunity):
    """Test closing opportunity as won"""
    close_data = {
        "stage": OpportunityStage.CLOSED_WON.value,
        "actual_close_date": datetime.utcnow().isoformat(),
        "notes": "Deal closed successfully - PO received"
    }

    response = await client.post(
        f"/api/v1/crm/opportunities/{test_opportunity.id}/close",
        json=close_data,
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["stage"] == OpportunityStage.CLOSED_WON.value
    assert data["actual_close_date"] is not None


@pytest.mark.asyncio
async def test_close_opportunity_lost(client: AsyncClient, auth_headers: dict, db_session, test_wholesale_customer, test_user):
    """Test closing opportunity as lost"""
    from app.models.crm import SalesOpportunity

    # Create new opportunity for this test
    opp = SalesOpportunity(
        opportunity_number="OPP-TEST-LOST",
        name="Lost Deal Test",
        customer_id=test_wholesale_customer.id,
        owner_id=test_user.id,
        stage=OpportunityStage.NEGOTIATION,
        estimated_value=Decimal("50000.00"),
        probability=60,
        expected_revenue=Decimal("30000.00")
    )
    db_session.add(opp)
    await db_session.commit()
    await db_session.refresh(opp)

    close_data = {
        "stage": OpportunityStage.CLOSED_LOST.value,
        "actual_close_date": datetime.utcnow().isoformat(),
        "loss_reason": "Customer chose competitor with lower pricing",
        "notes": "Lost to competitor - pricing was main issue"
    }

    response = await client.post(
        f"/api/v1/crm/opportunities/{opp.id}/close",
        json=close_data,
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["stage"] == OpportunityStage.CLOSED_LOST.value
    assert data["loss_reason"] is not None


@pytest.mark.asyncio
async def test_get_pipeline_stats(client: AsyncClient, auth_headers: dict, test_opportunity):
    """Test getting pipeline statistics"""
    response = await client.get("/api/v1/crm/opportunities/pipeline/stats", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "total_opportunities" in data
    assert "total_value" in data
    assert "weighted_value" in data
    assert "by_stage" in data


@pytest.mark.asyncio
async def test_delete_opportunity(client: AsyncClient, auth_headers: dict, test_opportunity):
    """Test deleting an opportunity"""
    response = await client.delete(
        f"/api/v1/crm/opportunities/{test_opportunity.id}",
        headers=auth_headers
    )
    assert response.status_code == 204

    # Verify deletion
    get_response = await client.get(
        f"/api/v1/crm/opportunities/{test_opportunity.id}",
        headers=auth_headers
    )
    assert get_response.status_code == 404


# ===== Test Communication Management =====

@pytest.mark.asyncio
async def test_create_communication(
    client: AsyncClient,
    auth_headers: dict,
    test_wholesale_customer,
    test_user
):
    """Test creating a customer communication"""
    comm_data = {
        "customer_id": str(test_wholesale_customer.id),
        "our_representative_id": str(test_user.id),
        "type": CommunicationType.PHONE.value,
        "direction": CommunicationDirection.OUTBOUND.value,
        "subject": "Follow-up call regarding bulk order inquiry",
        "content": "Discussed winter collection requirements. Customer interested in 500 units.",
        "contact_person": "John Doe",
        "duration_minutes": 15,
        "requires_follow_up": True,
        "follow_up_date": (datetime.utcnow() + timedelta(days=7)).isoformat()
    }

    response = await client.post(
        "/api/v1/crm/communications",
        json=comm_data,
        headers=auth_headers
    )
    assert response.status_code == 201

    data = response.json()
    assert data["subject"] == comm_data["subject"]
    assert data["type"] == CommunicationType.PHONE.value
    assert data["requires_follow_up"] == True
    assert data["follow_up_completed"] == False


@pytest.mark.asyncio
async def test_create_communication_for_lead(
    client: AsyncClient,
    auth_headers: dict,
    test_lead,
    test_user
):
    """Test creating communication for a lead"""
    comm_data = {
        "lead_id": str(test_lead.id),
        "our_representative_id": str(test_user.id),
        "type": CommunicationType.EMAIL.value,
        "direction": CommunicationDirection.OUTBOUND.value,
        "subject": "Introduction and product catalog",
        "content": "Sent product catalog and pricing information as requested.",
        "requires_follow_up": True,
        "follow_up_date": (datetime.utcnow() + timedelta(days=3)).isoformat()
    }

    response = await client.post(
        "/api/v1/crm/communications",
        json=comm_data,
        headers=auth_headers
    )
    assert response.status_code == 201

    data = response.json()
    assert data["lead_id"] == str(test_lead.id)


@pytest.mark.asyncio
async def test_get_communication(client: AsyncClient, auth_headers: dict, test_communication):
    """Test retrieving a communication"""
    response = await client.get(
        f"/api/v1/crm/communications/{test_communication.id}",
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == str(test_communication.id)


@pytest.mark.asyncio
async def test_list_communications_by_customer(
    client: AsyncClient,
    auth_headers: dict,
    test_communication
):
    """Test listing communications for a customer"""
    response = await client.get(
        f"/api/v1/crm/communications/customer/{test_communication.customer_id}?page=1&page_size=10",
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0


@pytest.mark.asyncio
async def test_update_communication(client: AsyncClient, auth_headers: dict, test_communication):
    """Test updating a communication"""
    update_data = {
        "content": "Updated: Customer confirmed interest and requested detailed quotation",
        "duration_minutes": 20
    }

    response = await client.put(
        f"/api/v1/crm/communications/{test_communication.id}",
        json=update_data,
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert "Updated:" in data["content"]
    assert data["duration_minutes"] == 20


@pytest.mark.asyncio
async def test_mark_follow_up_completed(
    client: AsyncClient,
    auth_headers: dict,
    test_communication
):
    """Test marking follow-up as completed"""
    response = await client.post(
        f"/api/v1/crm/communications/{test_communication.id}/complete-follow-up",
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["follow_up_completed"] == True


@pytest.mark.asyncio
async def test_get_pending_follow_ups(client: AsyncClient, auth_headers: dict, db_session, test_wholesale_customer, test_user):
    """Test getting pending follow-ups"""
    from app.models.crm import CustomerCommunication

    # Create communication with pending follow-up
    comm = CustomerCommunication(
        customer_id=test_wholesale_customer.id,
        our_representative_id=test_user.id,
        type=CommunicationType.PHONE,
        direction=CommunicationDirection.OUTBOUND,
        subject="Pending follow-up test",
        content="Test communication",
        requires_follow_up=True,
        follow_up_date=datetime.utcnow(),
        follow_up_completed=False
    )
    db_session.add(comm)
    await db_session.commit()

    response = await client.get(
        "/api/v1/crm/communications/follow-ups/pending",
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    comm_ids = [item["id"] for item in data]
    assert str(comm.id) in comm_ids


@pytest.mark.asyncio
async def test_delete_communication(client: AsyncClient, auth_headers: dict, test_communication):
    """Test deleting a communication"""
    response = await client.delete(
        f"/api/v1/crm/communications/{test_communication.id}",
        headers=auth_headers
    )
    assert response.status_code == 204


# ===== Test Segment Management =====

@pytest.mark.asyncio
async def test_create_segment(client: AsyncClient, auth_headers: dict):
    """Test creating a customer segment"""
    segment_data = {
        "name": "High Value Customers",
        "description": "Customers with annual spend > 500K",
        "code": "HVC",
        "criteria": {
            "min_annual_spend": 500000,
            "order_frequency": "monthly"
        },
        "is_active": True,
        "priority": 1,
        "benefits": {
            "discount_tier": "Platinum",
            "payment_terms": "Net 60"
        }
    }

    response = await client.post("/api/v1/crm/segments", json=segment_data, headers=auth_headers)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == segment_data["name"]
    assert data["code"] == segment_data["code"]
    assert data["customer_count"] == 0


@pytest.mark.asyncio
async def test_create_duplicate_segment(client: AsyncClient, auth_headers: dict):
    """Test creating segment with duplicate code"""
    segment_data = {
        "name": "Test Segment",
        "code": "DUP",
        "description": "Duplicate test"
    }

    # Create first segment
    response1 = await client.post("/api/v1/crm/segments", json=segment_data, headers=auth_headers)
    assert response1.status_code == 201

    # Try to create duplicate
    response2 = await client.post("/api/v1/crm/segments", json=segment_data, headers=auth_headers)
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_get_segment(client: AsyncClient, auth_headers: dict, test_segment):
    """Test retrieving a segment"""
    response = await client.get(f"/api/v1/crm/segments/{test_segment.id}", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == str(test_segment.id)
    assert data["name"] == test_segment.name


@pytest.mark.asyncio
async def test_list_segments(client: AsyncClient, auth_headers: dict, test_segment):
    """Test listing segments"""
    response = await client.get("/api/v1/crm/segments?page=1&page_size=10", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0


@pytest.mark.asyncio
async def test_update_segment(client: AsyncClient, auth_headers: dict, test_segment):
    """Test updating a segment"""
    update_data = {
        "description": "Updated description - refined criteria",
        "priority": 2
    }

    response = await client.put(
        f"/api/v1/crm/segments/{test_segment.id}",
        json=update_data,
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert "Updated description" in data["description"]
    assert data["priority"] == 2


@pytest.mark.asyncio
async def test_assign_customers_to_segment(
    client: AsyncClient,
    auth_headers: dict,
    test_segment,
    test_wholesale_customer
):
    """Test assigning customers to segment"""
    assign_data = {
        "customer_ids": [str(test_wholesale_customer.id)],
        "segment_id": str(test_segment.id)
    }

    response = await client.post(
        f"/api/v1/crm/segments/{test_segment.id}/assign-customers",
        json=assign_data,
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["count"] > 0


@pytest.mark.asyncio
async def test_remove_customers_from_segment(
    client: AsyncClient,
    auth_headers: dict,
    test_segment,
    test_wholesale_customer,
    db_session
):
    """Test removing customers from segment"""
    from app.models.crm import CustomerSegmentMapping

    # First assign customer
    mapping = CustomerSegmentMapping(
        customer_id=test_wholesale_customer.id,
        segment_id=test_segment.id
    )
    db_session.add(mapping)
    await db_session.commit()

    # Now remove
    response = await client.post(
        f"/api/v1/crm/segments/{test_segment.id}/remove-customers",
        json=[str(test_wholesale_customer.id)],
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["count"] > 0


@pytest.mark.asyncio
async def test_delete_segment(client: AsyncClient, auth_headers: dict, test_segment):
    """Test deleting a segment"""
    response = await client.delete(f"/api/v1/crm/segments/{test_segment.id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify deletion
    get_response = await client.get(f"/api/v1/crm/segments/{test_segment.id}", headers=auth_headers)
    assert get_response.status_code == 404
