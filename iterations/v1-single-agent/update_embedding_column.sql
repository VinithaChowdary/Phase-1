-- Update table for 384-dimensional embeddings and clear existing data
-- Run this in your Supabase SQL editor:

-- 1. First truncate the table to remove all existing data
truncate table site_pages;

-- 2. Drop the existing embedding column and recreate it with 384 dimensions
alter table site_pages drop column if exists embedding;
alter table site_pages add column embedding vector(384);

-- 2. (Optional) Recreate the ivfflat index if needed:
-- drop index if exists site_pages_embedding_idx;
-- create index on site_pages using ivfflat (embedding vector_cosine_ops);

-- 3. Run the updated search function from fix_search_function.sql to ensure consistent dimensions.
