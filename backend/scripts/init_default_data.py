#!/usr/bin/env python3
"""
Initialize default data - roles, permissions, and admin user
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.role import Role, Permission
from sqlalchemy import select


async def init_permissions(session):
    """
    Initialize default permissions
    """
    print("Creating permissions...")
    
    permissions_data = [
        # User Management
        {"name": "users:read", "resource": "users", "action": "read", "description": "View users"},
        {"name": "users:create", "resource": "users", "action": "create", "description": "Create users"},
        {"name": "users:update", "resource": "users", "action": "update", "description": "Update users"},
        {"name": "users:delete", "resource": "users", "action": "delete", "description": "Delete users"},
        
        # Inventory Management
        {"name": "inventory:read", "resource": "inventory", "action": "read", "description": "View inventory"},
        {"name": "inventory:create", "resource": "inventory", "action": "create", "description": "Create inventory"},
        {"name": "inventory:update", "resource": "inventory", "action": "update", "description": "Update inventory"},
        {"name": "inventory:delete", "resource": "inventory", "action": "delete", "description": "Delete inventory"},
        
        # Sales Management
        {"name": "sales:read", "resource": "sales", "action": "read", "description": "View sales"},
        {"name": "sales:create", "resource": "sales", "action": "create", "description": "Create sales"},
        {"name": "sales:update", "resource": "sales", "action": "update", "description": "Update sales"},
        {"name": "sales:delete", "resource": "sales", "action": "delete", "description": "Delete sales"},
        
        # Order Management
        {"name": "orders:read", "resource": "orders", "action": "read", "description": "View orders"},
        {"name": "orders:create", "resource": "orders", "action": "create", "description": "Create orders"},
        {"name": "orders:update", "resource": "orders", "action": "update", "description": "Update orders"},
        {"name": "orders:delete", "resource": "orders", "action": "delete", "description": "Delete orders"},
        
        # CRM
        {"name": "crm:read", "resource": "crm", "action": "read", "description": "View customers"},
        {"name": "crm:create", "resource": "crm", "action": "create", "description": "Create customers"},
        {"name": "crm:update", "resource": "crm", "action": "update", "description": "Update customers"},
        {"name": "crm:delete", "resource": "crm", "action": "delete", "description": "Delete customers"},
        
        # Finance
        {"name": "finance:read", "resource": "finance", "action": "read", "description": "View finance"},
        {"name": "finance:create", "resource": "finance", "action": "create", "description": "Create finance records"},
        {"name": "finance:update", "resource": "finance", "action": "update", "description": "Update finance records"},
        
        # Analytics
        {"name": "analytics:read", "resource": "analytics", "action": "read", "description": "View analytics"},
        
        # Reports
        {"name": "reports:read", "resource": "reports", "action": "read", "description": "View reports"},
        {"name": "reports:export", "resource": "reports", "action": "export", "description": "Export reports"},
    ]
    
    permissions = []
    for perm_data in permissions_data:
        # Check if permission exists
        result = await session.execute(
            select(Permission).where(Permission.name == perm_data["name"])
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            permission = Permission(**perm_data)
            session.add(permission)
            permissions.append(permission)
            print(f"  ✓ Created permission: {perm_data['name']}")
        else:
            permissions.append(existing)
    
    await session.commit()
    return permissions


async def init_roles(session, permissions):
    """
    Initialize default roles
    """
    print("\nCreating roles...")
    
    # Admin role - all permissions
    result = await session.execute(select(Role).where(Role.name == "admin"))
    admin_role = result.scalar_one_or_none()
    
    if not admin_role:
        admin_role = Role(
            name="admin",
            description="Administrator with full access"
        )
        admin_role.permissions = permissions
        session.add(admin_role)
        print("  ✓ Created role: admin")
    
    # Manager role - most permissions except user management
    result = await session.execute(select(Role).where(Role.name == "manager"))
    manager_role = result.scalar_one_or_none()
    
    if not manager_role:
        manager_permissions = [p for p in permissions if p.resource != "users"]
        manager_role = Role(
            name="manager",
            description="Manager with access to business operations"
        )
        manager_role.permissions = manager_permissions
        session.add(manager_role)
        print("  ✓ Created role: manager")
    
    # Sales role
    result = await session.execute(select(Role).where(Role.name == "sales"))
    sales_role = result.scalar_one_or_none()
    
    if not sales_role:
        sales_permissions = [p for p in permissions if p.resource in ["sales", "orders", "crm", "inventory"] and p.action in ["read", "create", "update"]]
        sales_role = Role(
            name="sales",
            description="Sales team member"
        )
        sales_role.permissions = sales_permissions
        session.add(sales_role)
        print("  ✓ Created role: sales")
    
    # Inventory role
    result = await session.execute(select(Role).where(Role.name == "inventory"))
    inventory_role = result.scalar_one_or_none()
    
    if not inventory_role:
        inventory_permissions = [p for p in permissions if p.resource in ["inventory", "orders"] and p.action in ["read", "create", "update"]]
        inventory_role = Role(
            name="inventory",
            description="Inventory management team"
        )
        inventory_role.permissions = inventory_permissions
        session.add(inventory_role)
        print("  ✓ Created role: inventory")
    
    # User role - basic read access
    result = await session.execute(select(Role).where(Role.name == "user"))
    user_role = result.scalar_one_or_none()
    
    if not user_role:
        user_permissions = [p for p in permissions if p.action == "read"]
        user_role = Role(
            name="user",
            description="Basic user with read access"
        )
        user_role.permissions = user_permissions
        session.add(user_role)
        print("  ✓ Created role: user")
    
    await session.commit()
    return admin_role, manager_role, sales_role, inventory_role, user_role


async def init_admin_user(session, admin_role):
    """
    Create default admin user
    """
    print("\nCreating admin user...")
    
    admin_email = "admin@example.com"
    
    # Check if admin exists
    result = await session.execute(select(User).where(User.email == admin_email))
    existing_admin = result.scalar_one_or_none()
    
    if not existing_admin:
        admin_user = User(
            email=admin_email,
            hashed_password=hash_password("Admin123!"),
            first_name="Admin",
            last_name="User",
            is_active=True,
            is_verified=True,
            is_superuser=True
        )
        admin_user.roles = [admin_role]
        session.add(admin_user)
        await session.commit()
        
        print(f"  ✓ Created admin user: {admin_email}")
        print(f"  ✓ Password: Admin123!")
        print("")
        print("⚠️  IMPORTANT: Change the admin password immediately after first login!")
    else:
        print(f"  ℹ️  Admin user already exists: {admin_email}")


async def main():
    """
    Main initialization function
    """
    print("=" * 60)
    print("Business Management System - Data Initialization")
    print("=" * 60)
    print("")
    
    async with AsyncSessionLocal() as session:
        try:
            # Initialize permissions
            permissions = await init_permissions(session)
            
            # Initialize roles
            roles = await init_roles(session, permissions)
            admin_role = roles[0]
            
            # Initialize admin user
            await init_admin_user(session, admin_role)
            
            print("")
            print("=" * 60)
            print("✅ Initialization completed successfully!")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ Error during initialization: {str(e)}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
