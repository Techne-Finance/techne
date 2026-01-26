-- Migration: Add scam fingerprints table with pgvector
-- Run this in Supabase SQL Editor

-- 1. Enable pgvector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create scam fingerprints table
CREATE TABLE IF NOT EXISTS scam_fingerprints (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    contract_address TEXT NOT NULL UNIQUE,
    chain TEXT DEFAULT 'base',
    
    -- Fingerprint data
    source_hash TEXT NOT NULL,  -- SHA256 of cleaned source
    embedding vector(384),       -- Text embedding for similarity search (384 = all-MiniLM-L6-v2)
    
    -- Analysis results
    risk_score INTEGER NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
    risk_level TEXT NOT NULL,
    is_scam BOOLEAN DEFAULT FALSE,
    findings JSONB,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    analyzed_by TEXT DEFAULT 'regex',  -- 'regex', 'ai', 'manual'
    
    -- Source code info
    is_verified BOOLEAN DEFAULT FALSE,
    source_length INTEGER
);

-- 3. Create index for similarity search
CREATE INDEX IF NOT EXISTS idx_scam_fingerprints_embedding 
ON scam_fingerprints 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 4. Create index for address lookup
CREATE INDEX IF NOT EXISTS idx_scam_fingerprints_address 
ON scam_fingerprints (contract_address);

-- 5. Function to find similar contracts
CREATE OR REPLACE FUNCTION find_similar_scams(
    query_embedding vector(384),
    similarity_threshold FLOAT DEFAULT 0.95,
    max_results INT DEFAULT 5
)
RETURNS TABLE (
    contract_address TEXT,
    risk_score INTEGER,
    risk_level TEXT,
    is_scam BOOLEAN,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sf.contract_address,
        sf.risk_score,
        sf.risk_level,
        sf.is_scam,
        1 - (sf.embedding <=> query_embedding) AS similarity
    FROM scam_fingerprints sf
    WHERE sf.embedding IS NOT NULL
      AND 1 - (sf.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY sf.embedding <=> query_embedding
    LIMIT max_results;
END;
$$;

-- 6. Grant access to authenticated users
GRANT SELECT, INSERT ON scam_fingerprints TO authenticated;
GRANT SELECT, INSERT ON scam_fingerprints TO anon;

-- 7. Add RLS policy
ALTER TABLE scam_fingerprints ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read access to all" ON scam_fingerprints
    FOR SELECT USING (true);

CREATE POLICY "Allow insert from service role" ON scam_fingerprints
    FOR INSERT WITH CHECK (true);

-- Done!
-- Now run: SELECT * FROM scam_fingerprints; to verify
