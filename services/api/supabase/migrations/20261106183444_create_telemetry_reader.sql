-- Read-only access to public.telemetry_events for GET /telemetry/report.
-- telemetry_writer keeps INSERT only; reading goes through this separate group
-- role so the ingestion path still cannot read what it writes.

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'telemetry_reader') then
    create role telemetry_reader nologin;
  end if;
end;
$$;

grant usage on schema public to telemetry_reader;
grant select on table public.telemetry_events to telemetry_reader;

-- RLS is forced on the table, so SELECT also needs a policy.
create policy telemetry_reader_select on public.telemetry_events
  for select to telemetry_reader
  using (true);
