-- Schema reporting: business KPIs written by the business performance pipeline
-- (data/pipelines/pipeline.py) from public.telemetry_events. Design in
-- data/pipelines/PIPELINE_DESIGN.md (sections 2.6, 3.2 and 3.3).
--
-- The schema is not exposed by the Data API ([api].schemas in config.toml
-- stays public, graphql_public) and the pipeline never writes to
-- public.telemetry_events.

create schema reporting;
revoke all on schema reporting from public, anon, authenticated, service_role;

-- Group roles without login. Login roles are created per environment, outside
-- version control: the pipeline's login role is granted telemetry_reader and
-- reporting_writer; the API's login role for /reporting is granted
-- reporting_reader.
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'reporting_writer') then
    create role reporting_writer nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'reporting_reader') then
    create role reporting_reader nologin;
  end if;
end;
$$;

-- Execution log: one row per run. run_id is the Prefect flow run id.
create table reporting.pipeline_runs (
  run_id               uuid        primary key,
  flow_name            text        not null,
  trigger              text        not null check (trigger in ('schedule', 'manual', 'backfill')),
  requested_by         text        check (requested_by ~ '^usr_[0-9a-f]{32}$'),
  window_start         date        not null,
  window_end           date        not null,
  started_at           timestamptz not null default now(),
  finished_at          timestamptz,
  status               text        not null
                                   check (status in ('running', 'completed', 'failed', 'crashed', 'cancelled', 'skipped')),
  failed_stage         text        check (failed_stage in ('extract', 'transform', 'quality', 'load')),
  last_completed_date  date,
  events_extracted     integer     not null default 0,
  events_deduplicated  integer     not null default 0,
  events_invalid       integer     not null default 0,
  rows_inserted        integer     not null default 0,
  rows_updated         integer     not null default 0,
  rows_unchanged       integer     not null default 0,
  rows_deleted         integer     not null default 0,
  late_days_detected   integer     not null default 0,
  source_max_timestamp timestamptz,
  pipeline_version     text        not null,
  error_class          text,
  error_message        text,
  check (window_start < window_end),
  check (finished_at is null or finished_at >= started_at)
);

create index pipeline_runs_started_at_idx on reporting.pipeline_runs (started_at desc);
create index pipeline_runs_status_idx on reporting.pipeline_runs (status);

-- Checkpoint and quality per run and day. A 'loaded' row is written in the
-- same transaction as that day's KPIs.
create table reporting.pipeline_run_days (
  run_id              uuid        not null references reporting.pipeline_runs (run_id),
  metric_date         date        not null,
  status              text        not null check (status in ('loaded', 'failed')),
  events_extracted    integer     not null,
  events_after_dedupe integer     not null,
  rows_written        integer     not null,
  source_checksum     text        not null,
  quality             jsonb       not null default '{}' check (jsonb_typeof(quality) = 'object'),
  finished_at         timestamptz not null default now(),
  primary key (run_id, metric_date)
);

create index pipeline_run_days_metric_date_idx on reporting.pipeline_run_days (metric_date, finished_at desc);

-- Destination table. Provisional name until the data pipelines BRIEFING sets
-- the one from its "Destination table" section.
create table reporting.executive_kpis_daily (
  kpi                text        not null check (kpi in (
                                   'shipments_total', 'on_time_delivery_rate', 'shipping_cost_total',
                                   'shipping_cost_per_kg', 'return_rate', 'customer_satisfaction_avg')),
  metric_date        date        not null,
  country            text        not null check (country ~ '^[A-Z]{2}$' or country = 'unknown'),
  carrier            text        not null default 'n/a' check (carrier ~ '^[a-z0-9_]{2,32}$' or carrier = 'n/a'),
  currency           text        not null default 'n/a' check (currency in ('USD', 'EUR', 'n/a')),
  numerator          numeric     not null,
  denominator        numeric,
  value              numeric,
  unit               text        not null,
  status             text        not null check (status in ('ok', 'no_activity', 'capture_gap', 'not_instrumented')),
  source_event_count integer     not null check (source_event_count >= 0),
  source_checksum    text        not null,
  revision           integer     not null default 1 check (revision >= 1),
  pipeline_version   text        not null,
  run_id             uuid        not null references reporting.pipeline_runs (run_id),
  computed_at        timestamptz not null,
  primary key (kpi, metric_date, country, carrier, currency)
);

create index executive_kpis_daily_metric_date_idx on reporting.executive_kpis_daily (metric_date);

comment on table reporting.executive_kpis_daily is
  'Daily business KPIs (UTC day x country x carrier x currency) as numerator/denominator. Provisional name.';

-- Previous versions of every KPI row that was updated or deleted.
create table reporting.executive_kpis_daily_history (
  history_id         bigint      generated always as identity primary key,
  operation          text        not null check (operation in ('UPDATE', 'DELETE')),
  replaced_by_run_id uuid,
  changed_at         timestamptz not null default now(),
  kpi                text        not null,
  metric_date        date        not null,
  country            text        not null,
  carrier            text        not null,
  currency           text        not null,
  numerator          numeric     not null,
  denominator        numeric,
  value              numeric,
  unit               text        not null,
  status             text        not null,
  source_event_count integer     not null,
  source_checksum    text        not null,
  revision           integer     not null,
  pipeline_version   text        not null,
  run_id             uuid        not null,
  computed_at        timestamptz not null
);

create index executive_kpis_daily_history_key_idx
  on reporting.executive_kpis_daily_history (kpi, metric_date, country, carrier, currency);

-- Copy the old version on UPDATE and DELETE. On DELETE the replacing run is
-- read from the transaction setting reporting.run_id, set by the pipeline.
create function reporting.executive_kpis_daily_keep_history()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  insert into reporting.executive_kpis_daily_history (
    operation, replaced_by_run_id, kpi, metric_date, country, carrier, currency, numerator,
    denominator, value, unit, status, source_event_count, source_checksum, revision,
    pipeline_version, run_id, computed_at
  ) values (
    tg_op,
    case when tg_op = 'UPDATE' then new.run_id
         else nullif(current_setting('reporting.run_id', true), '')::uuid end,
    old.kpi, old.metric_date, old.country, old.carrier, old.currency, old.numerator,
    old.denominator, old.value, old.unit, old.status, old.source_event_count, old.source_checksum,
    old.revision, old.pipeline_version, old.run_id, old.computed_at
  );
  return null;
end;
$$;

create trigger executive_kpis_daily_keep_history
  after update or delete on reporting.executive_kpis_daily
  for each row execute function reporting.executive_kpis_daily_keep_history();

-- The history is append-only, like public.telemetry_events.
create function reporting.reject_change()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  raise exception '% is append-only (% rejected)', tg_table_name, tg_op
    using errcode = 'insufficient_privilege';
end;
$$;

create trigger executive_kpis_daily_history_no_update_delete
  before update or delete on reporting.executive_kpis_daily_history
  for each row execute function reporting.reject_change();

create trigger executive_kpis_daily_history_no_truncate
  before truncate on reporting.executive_kpis_daily_history
  for each statement execute function reporting.reject_change();

revoke all on function reporting.executive_kpis_daily_keep_history() from public, anon, authenticated, service_role;
revoke all on function reporting.reject_change() from public, anon, authenticated, service_role;

-- Minimal permissions with RLS forced, same pattern as telemetry_events.
alter table reporting.pipeline_runs enable row level security;
alter table reporting.pipeline_runs force row level security;
alter table reporting.pipeline_run_days enable row level security;
alter table reporting.pipeline_run_days force row level security;
alter table reporting.executive_kpis_daily enable row level security;
alter table reporting.executive_kpis_daily force row level security;
alter table reporting.executive_kpis_daily_history enable row level security;
alter table reporting.executive_kpis_daily_history force row level security;

revoke all on all tables in schema reporting from public, anon, authenticated, service_role;
revoke all on all sequences in schema reporting from public, anon, authenticated, service_role;

grant usage on schema reporting to reporting_writer, reporting_reader;

grant select, insert, update, delete
  on reporting.pipeline_runs, reporting.pipeline_run_days, reporting.executive_kpis_daily
  to reporting_writer;
grant select, insert on reporting.executive_kpis_daily_history to reporting_writer;

grant select
  on reporting.pipeline_runs, reporting.pipeline_run_days, reporting.executive_kpis_daily,
     reporting.executive_kpis_daily_history
  to reporting_reader;

create policy reporting_writer_all on reporting.pipeline_runs
  for all to reporting_writer using (true) with check (true);
create policy reporting_writer_all on reporting.pipeline_run_days
  for all to reporting_writer using (true) with check (true);
create policy reporting_writer_all on reporting.executive_kpis_daily
  for all to reporting_writer using (true) with check (true);
create policy reporting_writer_all on reporting.executive_kpis_daily_history
  for all to reporting_writer using (true) with check (true);

create policy reporting_reader_select on reporting.pipeline_runs
  for select to reporting_reader using (true);
create policy reporting_reader_select on reporting.pipeline_run_days
  for select to reporting_reader using (true);
create policy reporting_reader_select on reporting.executive_kpis_daily
  for select to reporting_reader using (true);
create policy reporting_reader_select on reporting.executive_kpis_daily_history
  for select to reporting_reader using (true);
