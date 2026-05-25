"""Minimal ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from .database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, default="general")
    unit_cost = Column(Float, nullable=False, default=0.0)
    base_price = Column(Float, nullable=False, default=0.0)
    shelf_life_days = Column(Integer, nullable=False, default=0)


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    region = Column(String(100), nullable=False)


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    warehouse_type = Column(String(100), nullable=False)


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    reliability_score = Column(Float, nullable=False, default=1.0)


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshots"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, nullable=False)
    location_type = Column(String(50), nullable=False)
    location_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentDecision(Base):
    __tablename__ = "agent_decisions"

    id = Column(Integer, primary_key=True)
    agent_name = Column(String(100), nullable=False)
    action = Column(String(255), nullable=False)
    details = Column(Text, nullable=False, default="")
    success = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ExternalFactor(Base):
    __tablename__ = "external_factors"

    id = Column(Integer, primary_key=True)
    factor_date = Column(DateTime, default=datetime.utcnow)
    name = Column(String(255), nullable=False)
    value = Column(Float, nullable=False, default=0.0)


class SupplierProduct(Base):
    __tablename__ = "supplier_products"

    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)


class KPISnapshot(Base):
    __tablename__ = "kpi_snapshots"

    id = Column(Integer, primary_key=True)
    snapshot_date = Column(DateTime, default=datetime.utcnow)
    total_revenue = Column(Float, nullable=False, default=0.0)
    total_profit = Column(Float, nullable=False, default=0.0)
    fill_rate = Column(Float, nullable=False, default=0.0)
