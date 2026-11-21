-- Direct identifier lookup, owner scoped; existing table RLS remains enforced.
CREATE INDEX ix_urls_owner_sha256_investigation ON public.urls (owner_id, sha256, investigation_id);
-- statement-breakpoint
CREATE INDEX ix_urls_owner_domain_investigation ON public.urls (owner_id, domain_id, investigation_id);
