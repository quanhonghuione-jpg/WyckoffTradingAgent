-- Recommendation tracking price integrity guardrails.
-- Run in Supabase SQL Editor before/with the Tickflow reprice deployment.

-- 1) Inspect duplicates first. This should return 0 rows.
select
  code,
  recommend_date,
  count(*) as duplicate_count
from public.recommendation_tracking
group by code, recommend_date
having count(*) > 1
order by duplicate_count desc, recommend_date desc, code;

-- 2) If the inspection above returned rows, keep the newest row per stock/date.
with ranked as (
  select
    id,
    row_number() over (
      partition by code, recommend_date
      order by updated_at desc nulls last, created_at desc nulls last, id desc
    ) as rn
  from public.recommendation_tracking
)
delete from public.recommendation_tracking t
using ranked r
where t.id = r.id
  and r.rn > 1;

-- 3) Enforce the business key used by application upserts.
alter table public.recommendation_tracking
  alter column code set not null,
  alter column recommend_date set not null;

do $$
begin
  if not exists (
    select 1
    from pg_indexes
    where schemaname = 'public'
      and tablename = 'recommendation_tracking'
      and indexdef ilike '%unique%'
      and indexdef ilike '%code%'
      and indexdef ilike '%recommend_date%'
  ) then
    create unique index recommendation_tracking_code_recommend_date_uidx
      on public.recommendation_tracking (code, recommend_date);
  end if;
end $$;

-- 4) Speed up the Streamlit/CF Pages tracking windows and maintenance jobs.
create index if not exists recommendation_tracking_recommend_date_desc_idx
  on public.recommendation_tracking (recommend_date desc);

create index if not exists recommendation_tracking_code_idx
  on public.recommendation_tracking (code);

create index if not exists recommendation_tracking_updated_at_desc_idx
  on public.recommendation_tracking (updated_at desc);

-- 5) Portfolio table guardrail: one active row per portfolio/stock.
-- If this fails, inspect duplicates with:
-- select portfolio_id, code, count(*) from public.portfolio_positions group by portfolio_id, code having count(*) > 1;
create unique index if not exists portfolio_positions_portfolio_id_code_uidx
  on public.portfolio_positions (portfolio_id, code);
