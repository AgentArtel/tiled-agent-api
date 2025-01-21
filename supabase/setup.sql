-- Drop existing objects
drop policy if exists "Allow public read access" on tiled_docs;
drop function if exists match_tiled_docs(json);
drop index if exists tiled_docs_embedding_idx;
drop table if exists tiled_docs;

-- Enable the pgvector extension to work with embedding vectors
create extension if not exists vector;

-- Create a table for storing documentation chunks
create table if not exists tiled_docs (
  id bigint primary key generated always as identity,
  url text not null,
  chunk_number integer not null,
  title text not null,
  summary text not null,
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  embedding vector(1536) not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  unique(url, chunk_number)
);

-- Create a function to match similar documentation chunks
create or replace function match_tiled_docs (
  params json
)
returns table (
  id bigint,
  url text,
  chunk_number integer,
  title text,
  summary text,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
declare
  query_embedding vector(1536);
  match_count int;
  match_threshold float;
begin
  query_embedding := (params->>'query_embedding')::vector(1536);
  match_count := coalesce((params->>'match_count')::int, 5);
  match_threshold := coalesce((params->>'match_threshold')::float, 0.78);

  return query
  select
    tiled_docs.id,
    tiled_docs.url,
    tiled_docs.chunk_number,
    tiled_docs.title,
    tiled_docs.summary,
    tiled_docs.content,
    tiled_docs.metadata,
    1 - (tiled_docs.embedding <=> query_embedding) as similarity
  from tiled_docs
  where 1 - (tiled_docs.embedding <=> query_embedding) > match_threshold
  order by similarity desc
  limit match_count;
end;
$$;

-- Create an index for faster similarity searches
create index if not exists tiled_docs_embedding_idx on tiled_docs using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

-- Enable Row Level Security (RLS)
alter table tiled_docs enable row level security;

-- Create a policy that allows public read access
create policy "Allow public read access"
  on tiled_docs for select
  to public
  using (true);

-- Grant necessary permissions
grant usage on schema public to anon;
grant select on table tiled_docs to anon;
grant execute on function match_tiled_docs(json) to anon;
