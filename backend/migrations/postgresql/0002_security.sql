-- Supabase-only security revision. Apply as a migration owner, not the API role.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fraudshield_api') THEN
    CREATE ROLE fraudshield_api NOLOGIN NOSUPERUSER NOBYPASSRLS;
  END IF;
END
$$;

-- statement-breakpoint

GRANT USAGE ON SCHEMA public, auth TO fraudshield_api;

-- statement-breakpoint

GRANT EXECUTE ON FUNCTION auth.uid() TO fraudshield_api;

-- statement-breakpoint

ALTER TABLE public.users ADD CONSTRAINT fk_users_supabase_auth FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- statement-breakpoint

CREATE FUNCTION public.fraudshield_touch_updated_at() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END
$$;

-- statement-breakpoint

REVOKE ALL ON FUNCTION public.fraudshield_touch_updated_at() FROM PUBLIC;

-- statement-breakpoint

GRANT EXECUTE ON FUNCTION public.fraudshield_touch_updated_at() TO fraudshield_api;

-- statement-breakpoint

REVOKE ALL ON TABLE public.users FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.users FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY users_maintenance ON public.users FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.users'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.users'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.users TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY users_api ON public.users FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = id) WITH CHECK ((SELECT auth.uid()) = id);

-- statement-breakpoint

CREATE TRIGGER users_touch_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.user_profiles FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.user_profiles FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY user_profiles_maintenance ON public.user_profiles FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.user_profiles'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.user_profiles'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.user_profiles TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY user_profiles_api ON public.user_profiles FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER user_profiles_touch_updated_at BEFORE UPDATE ON public.user_profiles FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.devices FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.devices ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.devices FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY devices_maintenance ON public.devices FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.devices'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.devices'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.devices TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY devices_api ON public.devices FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER devices_touch_updated_at BEFORE UPDATE ON public.devices FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.user_consents FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.user_consents ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.user_consents FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY user_consents_maintenance ON public.user_consents FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.user_consents'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.user_consents'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.user_consents TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY user_consents_api ON public.user_consents FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER user_consents_touch_updated_at BEFORE UPDATE ON public.user_consents FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.investigations FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.investigations ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.investigations FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY investigations_maintenance ON public.investigations FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.investigations'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.investigations'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.investigations TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY investigations_api ON public.investigations FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER investigations_touch_updated_at BEFORE UPDATE ON public.investigations FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.investigation_events FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.investigation_events ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.investigation_events FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY investigation_events_maintenance ON public.investigation_events FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.investigation_events'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.investigation_events'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.investigation_events TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY investigation_events_api ON public.investigation_events FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER investigation_events_touch_updated_at BEFORE UPDATE ON public.investigation_events FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.evidence_sources FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.evidence_sources ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.evidence_sources FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY evidence_sources_maintenance ON public.evidence_sources FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.evidence_sources'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.evidence_sources'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.evidence_sources TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY evidence_sources_api ON public.evidence_sources FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER evidence_sources_touch_updated_at BEFORE UPDATE ON public.evidence_sources FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.evidence FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.evidence ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.evidence FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY evidence_maintenance ON public.evidence FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.evidence'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.evidence'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.evidence TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY evidence_api ON public.evidence FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER evidence_touch_updated_at BEFORE UPDATE ON public.evidence FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.domains FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.domains ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.domains FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY domains_maintenance ON public.domains FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.domains'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.domains'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.domains TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY domains_api ON public.domains FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER domains_touch_updated_at BEFORE UPDATE ON public.domains FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.urls FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.urls ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.urls FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY urls_maintenance ON public.urls FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.urls'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.urls'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.urls TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY urls_api ON public.urls FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER urls_touch_updated_at BEFORE UPDATE ON public.urls FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.applications FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.applications ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.applications FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY applications_maintenance ON public.applications FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.applications'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.applications'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.applications TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY applications_api ON public.applications FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER applications_touch_updated_at BEFORE UPDATE ON public.applications FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.apk_analysis FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.apk_analysis ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.apk_analysis FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY apk_analysis_maintenance ON public.apk_analysis FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.apk_analysis'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.apk_analysis'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.apk_analysis TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY apk_analysis_api ON public.apk_analysis FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER apk_analysis_touch_updated_at BEFORE UPDATE ON public.apk_analysis FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.phone_indicators FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.phone_indicators ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.phone_indicators FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY phone_indicators_maintenance ON public.phone_indicators FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.phone_indicators'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.phone_indicators'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.phone_indicators TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY phone_indicators_api ON public.phone_indicators FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER phone_indicators_touch_updated_at BEFORE UPDATE ON public.phone_indicators FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.qr_analyses FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.qr_analyses ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.qr_analyses FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY qr_analyses_maintenance ON public.qr_analyses FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.qr_analyses'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.qr_analyses'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.qr_analyses TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY qr_analyses_api ON public.qr_analyses FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER qr_analyses_touch_updated_at BEFORE UPDATE ON public.qr_analyses FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.model_predictions FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.model_predictions ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.model_predictions FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY model_predictions_maintenance ON public.model_predictions FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.model_predictions'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.model_predictions'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.model_predictions TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY model_predictions_api ON public.model_predictions FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER model_predictions_touch_updated_at BEFORE UPDATE ON public.model_predictions FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.threat_intelligence_results FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.threat_intelligence_results ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.threat_intelligence_results FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY threat_intelligence_results_maintenance ON public.threat_intelligence_results FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.threat_intelligence_results'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.threat_intelligence_results'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.threat_intelligence_results TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY threat_intelligence_results_api ON public.threat_intelligence_results FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER threat_intelligence_results_touch_updated_at BEFORE UPDATE ON public.threat_intelligence_results FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.risk_assessments FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.risk_assessments ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.risk_assessments FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY risk_assessments_maintenance ON public.risk_assessments FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.risk_assessments'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.risk_assessments'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.risk_assessments TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY risk_assessments_api ON public.risk_assessments FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER risk_assessments_touch_updated_at BEFORE UPDATE ON public.risk_assessments FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.graph_nodes FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.graph_nodes ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.graph_nodes FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY graph_nodes_maintenance ON public.graph_nodes FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.graph_nodes'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.graph_nodes'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.graph_nodes TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY graph_nodes_api ON public.graph_nodes FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER graph_nodes_touch_updated_at BEFORE UPDATE ON public.graph_nodes FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.graph_edges FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.graph_edges ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.graph_edges FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY graph_edges_maintenance ON public.graph_edges FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.graph_edges'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.graph_edges'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.graph_edges TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY graph_edges_api ON public.graph_edges FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER graph_edges_touch_updated_at BEFORE UPDATE ON public.graph_edges FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.community_reports FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.community_reports ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.community_reports FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY community_reports_maintenance ON public.community_reports FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.community_reports'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.community_reports'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.community_reports TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY community_reports_api ON public.community_reports FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER community_reports_touch_updated_at BEFORE UPDATE ON public.community_reports FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.watchlists FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.watchlists ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.watchlists FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY watchlists_maintenance ON public.watchlists FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.watchlists'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.watchlists'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.watchlists TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY watchlists_api ON public.watchlists FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER watchlists_touch_updated_at BEFORE UPDATE ON public.watchlists FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.security_alerts FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.security_alerts ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.security_alerts FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY security_alerts_maintenance ON public.security_alerts FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.security_alerts'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.security_alerts'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.security_alerts TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY security_alerts_api ON public.security_alerts FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER security_alerts_touch_updated_at BEFORE UPDATE ON public.security_alerts FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.audit_logs FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.audit_logs FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY audit_logs_maintenance ON public.audit_logs FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.audit_logs'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.audit_logs'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.audit_logs TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY audit_logs_api ON public.audit_logs FOR ALL TO fraudshield_api USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);

-- statement-breakpoint

CREATE TRIGGER audit_logs_touch_updated_at BEFORE UPDATE ON public.audit_logs FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.model_versions FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.model_versions ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.model_versions FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY model_versions_maintenance ON public.model_versions FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.model_versions'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.model_versions'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.model_versions TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY model_versions_api ON public.model_versions FOR ALL TO fraudshield_api USING (true) WITH CHECK (true);

-- statement-breakpoint

CREATE TRIGGER model_versions_touch_updated_at BEFORE UPDATE ON public.model_versions FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.provider_status FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.provider_status ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.provider_status FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY provider_status_maintenance ON public.provider_status FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.provider_status'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.provider_status'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.provider_status TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY provider_status_api ON public.provider_status FOR ALL TO fraudshield_api USING (true) WITH CHECK (true);

-- statement-breakpoint

CREATE TRIGGER provider_status_touch_updated_at BEFORE UPDATE ON public.provider_status FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.api_rate_limit_buckets FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.api_rate_limit_buckets ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.api_rate_limit_buckets FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY api_rate_limit_buckets_maintenance ON public.api_rate_limit_buckets FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.api_rate_limit_buckets'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.api_rate_limit_buckets'::regclass)));

-- statement-breakpoint

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.api_rate_limit_buckets TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY api_rate_limit_buckets_api ON public.api_rate_limit_buckets FOR ALL TO fraudshield_api USING (true) WITH CHECK (true);

-- statement-breakpoint

CREATE TRIGGER api_rate_limit_buckets_touch_updated_at BEFORE UPDATE ON public.api_rate_limit_buckets FOR EACH ROW EXECUTE FUNCTION public.fraudshield_touch_updated_at();

-- statement-breakpoint

REVOKE ALL ON TABLE public.schema_migrations FROM anon, authenticated, PUBLIC;

-- statement-breakpoint

ALTER TABLE public.schema_migrations ENABLE ROW LEVEL SECURITY;

-- statement-breakpoint

ALTER TABLE public.schema_migrations FORCE ROW LEVEL SECURITY;

-- statement-breakpoint

CREATE POLICY schema_migrations_maintenance ON public.schema_migrations FOR ALL USING (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.schema_migrations'::regclass))) WITH CHECK (current_user = pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.schema_migrations'::regclass)));

-- statement-breakpoint

GRANT SELECT ON TABLE public.schema_migrations TO fraudshield_api;

-- statement-breakpoint

CREATE POLICY schema_migrations_api_read ON public.schema_migrations FOR SELECT TO fraudshield_api USING (true);
