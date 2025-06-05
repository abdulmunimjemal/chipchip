-- File: data/create_tables_poc.sql
-- These are PoC-specific tables derived and augmented from the provided schema by Tesfa
-- to directly support the marketing queries in the task.

CREATE DATABASE IF NOT EXISTS chipchip_db;

USE chipchip_db;

-- Users Table (PoC specific augmentations)
CREATE TABLE IF NOT EXISTS users_poc (
    user_id UUID DEFAULT generateUUIDv4(),
    name String,
    email Nullable(String),
    registration_date DateTime64(6), -- From users.created_at
    user_status String,               -- From users.user_status
    is_group_leader Boolean DEFAULT false, -- PoC specific
    registration_channel String,          -- PoC specific
    customer_segment String,              -- PoC specific
    PRIMARY KEY (user_id)
) ENGINE = MergeTree()
ORDER BY (user_id);

-- Categories Table
CREATE TABLE IF NOT EXISTS categories_poc (
    category_id UUID DEFAULT generateUUIDv4(),
    category_name String,
    PRIMARY KEY (category_id)
) ENGINE = MergeTree()
ORDER BY (category_id);

-- Product Names Table (if keeping separate product names, otherwise denormalize into products_poc)
-- For PoC simplicity, product_name will be denormalized into products_poc.
-- If you need it:
-- CREATE TABLE IF NOT EXISTS product_names_poc (
--     product_name_id UUID DEFAULT generateUUIDv4(),
--     name String,
--     category_id UUID, -- FK to categories_poc.category_id
--     PRIMARY KEY (product_name_id)
-- ) ENGINE = MergeTree();

-- Products Table (PoC specific, denormalized for simplicity)
CREATE TABLE IF NOT EXISTS products_poc (
    product_id UUID DEFAULT generateUUIDv4(),
    product_name String,        -- Denormalized
    category_name String,       -- Denormalized
    status String,              -- From products.status
    original_price Decimal(8,2), -- Conceptual base price
    PRIMARY KEY (product_id)
) ENGINE = MergeTree()
ORDER BY (product_id);

-- Orders Table (PoC specific augmentations)
CREATE TABLE IF NOT EXISTS orders_poc (
    order_id UUID DEFAULT generateUUIDv4(),
    user_id UUID,                       -- FK to users_poc.user_id
    status String,                      -- From orders.status
    total_amount Decimal(8,2),          -- From orders.total_amount
    order_date DateTime64(6),           -- From orders.created_at
    payment_method String,              -- From orders.payment_method
    acquisition_channel String,         -- PoC specific
    PRIMARY KEY (order_id)
) ENGINE = MergeTree()
ORDER BY (order_id);

-- Order Items Table (Essential for PoC)
CREATE TABLE IF NOT EXISTS order_items_poc (
    order_item_id UUID DEFAULT generateUUIDv4(),
    order_id UUID,          -- FK to orders_poc.order_id
    product_id UUID,        -- FK to products_poc.product_id
    quantity Int32,
    price_per_unit Decimal(8,2),
    PRIMARY KEY (order_item_id, order_id)
) ENGINE = MergeTree()
ORDER BY (order_item_id, order_id);

-- Group Deals Table (Simplified for PoC)
CREATE TABLE IF NOT EXISTS group_deals_poc (
    group_deal_id UUID DEFAULT generateUUIDv4(),
    product_id UUID,        -- FK to products_poc.product_id
    group_price Decimal(8,2),
    max_group_member Int32,
    effective_from DateTime64(6),
    effective_to Nullable(DateTime64(6)),
    status String DEFAULT 'active', -- PoC: 'active', 'expired'
    PRIMARY KEY (group_deal_id)
) ENGINE = MergeTree()
ORDER BY (group_deal_id);

-- Groups Table (Represents an initiated group buy instance)
CREATE TABLE IF NOT EXISTS groups_poc (
    group_id UUID DEFAULT generateUUIDv4(),
    group_deal_id UUID,     -- FK to group_deals_poc.group_deal_id
    group_leader_id UUID,   -- FK to users_poc.user_id where is_group_leader=true
    status String,          -- PoC: 'active', 'completed', 'failed'
    created_at DateTime64(6),
    PRIMARY KEY (group_id)
) ENGINE = MergeTree()
ORDER BY (group_id);

-- Group Members Table (Users participating in a group)
CREATE TABLE IF NOT EXISTS group_members_poc (
    group_member_id UUID DEFAULT generateUUIDv4(),
    group_id UUID,          -- FK to groups_poc.group_id
    user_id UUID,           -- FK to users_poc.user_id
    joined_at DateTime64(6),
    linked_order_id Nullable(UUID), -- FK to orders_poc.order_id if their participation resulted in an order
    PRIMARY KEY (group_member_id, group_id, user_id)
) ENGINE = MergeTree()
ORDER BY (group_member_id, group_id, user_id);