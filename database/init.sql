-- ============================================================================
-- Database Initialization & Seed Script for Distributed Booking Platform
-- Mounted to: /docker-entrypoint-initdb.d/init.sql
-- ============================================================================

-- 1. Create Schema
CREATE TABLE IF NOT EXISTS guests (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS units (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    capacity INTEGER NOT NULL DEFAULT 2,
    is_available BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS reservations (
    id SERIAL PRIMARY KEY,
    guest_id INTEGER REFERENCES guests(id) ON DELETE CASCADE,
    unit_id INTEGER REFERENCES units(id) ON DELETE CASCADE,
    check_in_date DATE NOT NULL,
    check_out_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at DATE NOT NULL DEFAULT CURRENT_DATE
);

-- 2. Indexes for Performance and Queries
CREATE INDEX IF NOT EXISTS idx_units_availability ON units(is_available);
CREATE INDEX IF NOT EXISTS idx_reservations_unit_dates ON reservations(unit_id, check_in_date, check_out_date);
CREATE INDEX IF NOT EXISTS idx_guests_email ON guests(email);

-- 3. Seed Initial Inventory (5 Units)
INSERT INTO units (name, description, capacity, is_available) VALUES
    ('Deluxe Suite 101', 'King bed, city view, high-speed WiFi', 2, TRUE),
    ('Executive Suite 102', 'King bed with dedicated workspace and balcony', 2, TRUE),
    ('Ocean View 103', 'Panoramic ocean view with master suite', 4, TRUE),
    ('Presidential Suite 104', 'Luxury penthouse suite with private lounge', 6, TRUE),
    ('Standard Room 105', 'Queen bed, compact and quiet', 2, TRUE)
ON CONFLICT (name) DO NOTHING;

-- 4. Seed Test Guests
INSERT INTO guests (name, email, phone) VALUES
    ('Deepak Thakur', 'deepak@example.com', '+91-9876543210'),
    ('System Test User', 'testuser@example.com', '+91-9123456780')
ON CONFLICT (email) DO NOTHING;
