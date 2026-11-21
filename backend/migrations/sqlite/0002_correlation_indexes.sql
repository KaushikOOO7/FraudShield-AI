-- Direct identifier lookup, owner scoped; no changes to applied migrations.
CREATE INDEX ix_urls_owner_sha256_investigation ON urls (owner_id, sha256, investigation_id);
-- statement-breakpoint
CREATE INDEX ix_urls_owner_domain_investigation ON urls (owner_id, domain_id, investigation_id);
