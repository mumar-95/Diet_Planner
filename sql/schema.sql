-- AI Food & Nutrition Assistant — Supabase schema
-- Run this once in the Supabase SQL Editor (Dashboard → SQL → New query).

create extension if not exists vector with schema extensions;
create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- Nutrition knowledge base documents
-- ---------------------------------------------------------------------------

create table if not exists public.nutrition_documents (
  id uuid primary key default gen_random_uuid(),
  file_name text not null,
  file_type text not null default 'txt',
  source text not null default 'upload'
    check (source in ('upload', 'seed')),
  raw_text text not null default '',
  chunk_count integer not null default 0,
  content_sha256 text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists nutrition_documents_file_name_source_uidx
  on public.nutrition_documents (file_name, source);

create index if not exists nutrition_documents_created_at_idx
  on public.nutrition_documents (created_at desc);

-- Local fastembed MiniLM => 384 dimensions
create table if not exists public.nutrition_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.nutrition_documents (id) on delete cascade,
  chunk_index integer not null,
  content text not null,
  embedding extensions.vector(384),
  created_at timestamptz not null default now(),
  unique (document_id, chunk_index)
);

create index if not exists nutrition_chunks_document_id_idx
  on public.nutrition_chunks (document_id);

-- Optional after you have data (HNSW):
-- create index nutrition_chunks_embedding_idx
--   on public.nutrition_chunks
--   using hnsw (embedding extensions.vector_cosine_ops);

-- ---------------------------------------------------------------------------
-- Chat persistence
-- ---------------------------------------------------------------------------

create table if not exists public.chat_sessions (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.chat_sessions (id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  source text,
  created_at timestamptz not null default now()
);

create index if not exists chat_messages_session_id_idx
  on public.chat_messages (session_id, created_at);

create or replace function public.set_chat_session_updated_at()
returns trigger
language plpgsql
as $$
begin
  update public.chat_sessions
  set updated_at = now()
  where id = new.session_id;
  return new;
end;
$$;

drop trigger if exists chat_messages_touch_session on public.chat_messages;
create trigger chat_messages_touch_session
after insert on public.chat_messages
for each row
execute function public.set_chat_session_updated_at();

-- ---------------------------------------------------------------------------
-- Structured food query results
-- ---------------------------------------------------------------------------

create table if not exists public.food_queries (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references public.chat_sessions (id) on delete set null,
  query_text text not null,
  food_name text,
  input_type text not null default 'text'
    check (input_type in ('text', 'image', 'document')),
  nutritional_info text,
  macros jsonb not null default '{}'::jsonb,
  alternatives text,
  meal_plan text,
  raw_crew_result text,
  is_in_scope boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists food_queries_created_at_idx
  on public.food_queries (created_at desc);

create index if not exists food_queries_session_id_idx
  on public.food_queries (session_id);

-- ---------------------------------------------------------------------------
-- Vector similarity RPC
-- ---------------------------------------------------------------------------

create or replace function public.match_nutrition_chunks(
  query_embedding extensions.vector(384),
  match_count integer default 8,
  filter_document_id uuid default null
)
returns table (
  id uuid,
  content text,
  document_id uuid,
  chunk_index integer,
  similarity float
)
language sql
stable
as $$
  select
    nc.id,
    nc.content,
    nc.document_id,
    nc.chunk_index,
    1 - (nc.embedding <=> query_embedding) as similarity
  from public.nutrition_chunks nc
  where
    nc.embedding is not null
    and (filter_document_id is null or nc.document_id = filter_document_id)
  order by nc.embedding <=> query_embedding
  limit greatest(match_count, 1);
$$;

grant execute on function public.match_nutrition_chunks(
  extensions.vector(384), integer, uuid
) to anon, authenticated, service_role;

-- ---------------------------------------------------------------------------
-- Demo RLS: open policies for local portfolio demo only.
-- ---------------------------------------------------------------------------

alter table public.nutrition_documents enable row level security;
alter table public.nutrition_chunks enable row level security;
alter table public.chat_sessions enable row level security;
alter table public.chat_messages enable row level security;
alter table public.food_queries enable row level security;

drop policy if exists "demo_all_nutrition_documents" on public.nutrition_documents;
create policy "demo_all_nutrition_documents" on public.nutrition_documents
  for all using (true) with check (true);

drop policy if exists "demo_all_nutrition_chunks" on public.nutrition_chunks;
create policy "demo_all_nutrition_chunks" on public.nutrition_chunks
  for all using (true) with check (true);

drop policy if exists "demo_all_chat_sessions" on public.chat_sessions;
create policy "demo_all_chat_sessions" on public.chat_sessions
  for all using (true) with check (true);

drop policy if exists "demo_all_chat_messages" on public.chat_messages;
create policy "demo_all_chat_messages" on public.chat_messages
  for all using (true) with check (true);

drop policy if exists "demo_all_food_queries" on public.food_queries;
create policy "demo_all_food_queries" on public.food_queries
  for all using (true) with check (true);
