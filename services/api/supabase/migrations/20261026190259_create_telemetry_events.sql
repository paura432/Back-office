-- Append-only store for telemetry events accepted by POST /telemetry/events.
-- Column mapping from the envelope in docs/telemetry/event-schemas.json:
--   eventId -> event_id (primary key, idempotency), event_type, timestamp,
--   sessionId -> session_id, userId -> user_id, requestId -> request_id,
--   properties + schemaVersion -> tags. service is derived by the API.

create table public.telemetry_events (
  event_id    uuid        primary key,
  event_type  text        not null check (event_type ~ '^[a-z]+(_[a-z]+)+$'),
  "timestamp" timestamptz not null,
  service     text        not null check (service <> ''),
  session_id  uuid,
  user_id     text        check (user_id ~ '^usr_[0-9a-f]{32}$'),
  request_id  uuid,
  tags        jsonb       not null check (jsonb_typeof(tags) = 'object')
);

comment on table public.telemetry_events is
  'Immutable telemetry events. Written only by the backend through telemetry_writer.';
comment on column public.telemetry_events.tags is
  'Event properties (business dimensions) plus the schemaVersion key.';

create index telemetry_events_timestamp_idx on public.telemetry_events ("timestamp");
create index telemetry_events_event_type_idx on public.telemetry_events (event_type);
create index telemetry_events_tags_idx on public.telemetry_events using gin (tags);

-- Events are immutable: block UPDATE, DELETE and TRUNCATE for every role,
-- including the table owner.
create function public.telemetry_events_reject_change()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  raise exception 'telemetry_events is append-only (% rejected)', tg_op
    using errcode = 'insufficient_privilege';
end;
$$;

revoke all on function public.telemetry_events_reject_change() from public, anon, authenticated, service_role;

create trigger telemetry_events_no_update_delete
  before update or delete on public.telemetry_events
  for each row execute function public.telemetry_events_reject_change();

create trigger telemetry_events_no_truncate
  before truncate on public.telemetry_events
  for each statement execute function public.telemetry_events_reject_change();

-- Minimal permissions. public is exposed by the Data API, so RLS stays on and
-- the API roles get nothing: browsers cannot read or write this table.
alter table public.telemetry_events enable row level security;
alter table public.telemetry_events force row level security;

revoke all on table public.telemetry_events from public, anon, authenticated, service_role;

-- Group role for the backend. It has no login; the backend's login role is
-- created per environment, outside version control, and granted this role.
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'telemetry_writer') then
    create role telemetry_writer nologin;
  end if;
end;
$$;

grant usage on schema public to telemetry_writer;
grant insert on table public.telemetry_events to telemetry_writer;

create policy telemetry_writer_insert on public.telemetry_events
  for insert to telemetry_writer
  with check (true);
