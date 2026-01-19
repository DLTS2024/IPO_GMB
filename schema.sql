-- Supabase SQL Schema for IPO Tracker
-- Run this in Supabase SQL Editor

-- Table: ipos
CREATE TABLE IF NOT EXISTS ipos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    price TEXT,
    start_date DATE,
    end_date DATE NOT NULL,
    subscription TEXT,
    status TEXT DEFAULT 'tracking' CHECK (status IN ('tracking', 'alerted', 'expired')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name, end_date)
);

-- Table: gmp_history
CREATE TABLE IF NOT EXISTS gmp_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ipo_id UUID REFERENCES ipos(id) ON DELETE CASCADE,
    gmp FLOAT NOT NULL,
    recorded_at DATE DEFAULT CURRENT_DATE,
    UNIQUE(ipo_id, recorded_at)
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_ipos_end_date ON ipos(end_date);
CREATE INDEX IF NOT EXISTS idx_ipos_status ON ipos(status);
CREATE INDEX IF NOT EXISTS idx_gmp_history_ipo_id ON gmp_history(ipo_id);

-- Enable Row Level Security (optional, for public access)
ALTER TABLE ipos ENABLE ROW LEVEL SECURITY;
ALTER TABLE gmp_history ENABLE ROW LEVEL SECURITY;

-- Allow all operations for now (you can restrict later)
CREATE POLICY "Allow all for ipos" ON ipos FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for gmp_history" ON gmp_history FOR ALL USING (true) WITH CHECK (true);
