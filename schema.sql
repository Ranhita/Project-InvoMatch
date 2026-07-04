-- InvoMatch Database Schema

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'finance',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Invoices Table
CREATE TABLE IF NOT EXISTS invoices (
    id VARCHAR(100) PRIMARY KEY,
    file_path VARCHAR(500) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size INTEGER NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'uploaded',
    uploaded_by INTEGER REFERENCES users(id),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    md5_hash VARCHAR(32) UNIQUE NOT NULL,
    invoice_number VARCHAR(100),
    vendor_name VARCHAR(255),
    invoice_date DATE,
    total_amount DOUBLE PRECISION
);

-- Purchase Orders Table
CREATE TABLE IF NOT EXISTS purchase_orders (
    id VARCHAR(100) PRIMARY KEY,
    file_path VARCHAR(500) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size INTEGER NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'uploaded',
    uploaded_by INTEGER REFERENCES users(id),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    md5_hash VARCHAR(32) UNIQUE NOT NULL,
    po_number VARCHAR(100),
    vendor_name VARCHAR(255),
    po_date DATE,
    total_amount DOUBLE PRECISION
);

-- Invoice Lines Table
CREATE TABLE IF NOT EXISTS invoice_lines (
    id SERIAL PRIMARY KEY,
    invoice_id VARCHAR(100) REFERENCES invoices(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    description TEXT,
    quantity DOUBLE PRECISION NOT NULL,
    unit_price DOUBLE PRECISION NOT NULL,
    total_price DOUBLE PRECISION NOT NULL,
    sku VARCHAR(100)
);

-- PO Lines Table
CREATE TABLE IF NOT EXISTS po_lines (
    id SERIAL PRIMARY KEY,
    po_id VARCHAR(100) REFERENCES purchase_orders(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    description TEXT,
    quantity DOUBLE PRECISION NOT NULL,
    unit_price DOUBLE PRECISION NOT NULL,
    total_price DOUBLE PRECISION NOT NULL,
    sku VARCHAR(100)
);

-- Matches Table
CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    invoice_id VARCHAR(100) REFERENCES invoices(id) ON DELETE CASCADE,
    po_id VARCHAR(100) REFERENCES purchase_orders(id) ON DELETE CASCADE,
    match_score DOUBLE PRECISION NOT NULL,
    matched_by VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Flags (Anomaly Detections & Explainable AI)
CREATE TABLE IF NOT EXISTS flags (
    id SERIAL PRIMARY KEY,
    invoice_id VARCHAR(100) REFERENCES invoices(id) ON DELETE CASCADE,
    flag_type VARCHAR(50) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    explained_by_ai TEXT,
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
