create extension if not exists vector;

create table if not exists site_pages (
  id bigserial primary key,
    url varchar not null,
    chunk_number integer not null,
    title varchar not null,
    summary varchar not null,
    content text not null,  -- Added content column
    metadata jsonb not null default '{}'::jsonb,  -- Added metadata column
  embedding vector(384),  -- sentence-transformers/all-MiniLM-L6-v2 embeddings are 384 dimensions
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    
    -- Add a unique constraint to prevent duplicate chunks for the same URL
    unique(url, chunk_number)
);

-- Create indexes
create index if not exists idx_site_pages_embedding on site_pages using ivfflat (embedding vector_cosine_ops);
create index if not exists idx_site_pages_metadata on site_pages using gin (metadata);

-- Vector search function
create or replace function match_site_pages (
  query_embedding vector(384),
  match_count int default 10,
  filter jsonb DEFAULT '{}'::jsonb
) returns table (
  id bigint,
  url varchar,
  chunk_number integer,
  title varchar,
  summary varchar,
  content text,
  metadata jsonb,
  similarity float
) language plpgsql as $$
#variable_conflict use_column
begin
  return query
  select
    id,
    url,
    chunk_number,
    title,
    summary,
    content,
    metadata,
    1 - (site_pages.embedding <=> query_embedding) as similarity
  from site_pages
  where metadata @> filter
  order by site_pages.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- Enable Row Level Security
alter table site_pages enable row level security;

-- Public read policy
drop policy if exists "Allow public read access" on site_pages;
create policy "Allow public read access"
  on site_pages for select to public using (true);