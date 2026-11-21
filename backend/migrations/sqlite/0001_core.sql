-- Frozen initial schema. Do not edit after deployment.
CREATE TABLE api_rate_limit_buckets (
	key_sha256 VARCHAR(64) NOT NULL, 
	window_start INTEGER NOT NULL, 
	request_count INTEGER NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_api_rate_limit_buckets PRIMARY KEY (key_sha256), 
	CONSTRAINT ck_api_rate_limit_buckets_positive_count CHECK (request_count >= 1)
);

-- statement-breakpoint

CREATE INDEX ix_api_rate_limit_buckets_window_start ON api_rate_limit_buckets (window_start);

-- statement-breakpoint

CREATE TABLE model_versions (
	id CHAR(32) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	version VARCHAR(100) NOT NULL, 
	task VARCHAR(80) NOT NULL, 
	artifact_sha256 VARCHAR(64) NOT NULL, 
	dataset_sha256 VARCHAR(64) NOT NULL, 
	provenance JSON NOT NULL, 
	evaluation JSON NOT NULL, 
	trained_at DATETIME NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_model_versions PRIMARY KEY (id), 
	CONSTRAINT uq_model_versions_name UNIQUE (name, version)
);

-- statement-breakpoint

CREATE TABLE provider_status (
	provider VARCHAR(80) NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	last_success_at DATETIME, 
	last_error_at DATETIME, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_provider_status PRIMARY KEY (provider)
);

-- statement-breakpoint

CREATE TABLE users (
	id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_users PRIMARY KEY (id)
);

-- statement-breakpoint

CREATE TABLE applications (
	package_name VARCHAR(255) NOT NULL, 
	app_name VARCHAR(255), 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_applications PRIMARY KEY (id), 
	CONSTRAINT uq_applications_owner_id UNIQUE (owner_id, package_name), 
	CONSTRAINT uq_applications_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_applications_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_applications_owner_id ON applications (owner_id);

-- statement-breakpoint

CREATE TABLE audit_logs (
	action VARCHAR(80) NOT NULL, 
	resource_id CHAR(32), 
	request_id CHAR(32) NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_audit_logs PRIMARY KEY (id), 
	CONSTRAINT uq_audit_logs_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_audit_logs_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_audit_logs_owner_id ON audit_logs (owner_id);

-- statement-breakpoint

CREATE TABLE community_reports (
	subject_type VARCHAR(32) NOT NULL, 
	redacted_subject TEXT NOT NULL, 
	redacted_description TEXT NOT NULL, 
	moderation_status VARCHAR(32) NOT NULL, 
	verified_at DATETIME, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_community_reports PRIMARY KEY (id), 
	CONSTRAINT ck_community_reports_moderation_status CHECK (moderation_status IN ('unreviewed','approved','rejected')), 
	CONSTRAINT uq_community_reports_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_community_reports_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_community_reports_owner_id ON community_reports (owner_id);

-- statement-breakpoint

CREATE TABLE devices (
	platform VARCHAR(16) NOT NULL, 
	last_seen_at DATETIME, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_devices PRIMARY KEY (id), 
	CONSTRAINT ck_devices_platform CHECK (platform IN ('android','web')), 
	CONSTRAINT uq_devices_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_devices_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_devices_owner_id ON devices (owner_id);

-- statement-breakpoint

CREATE TABLE domains (
	hostname VARCHAR(253) NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_domains PRIMARY KEY (id), 
	CONSTRAINT uq_domains_owner_id UNIQUE (owner_id, hostname), 
	CONSTRAINT uq_domains_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_domains_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_domains_owner_id ON domains (owner_id);

-- statement-breakpoint

CREATE TABLE graph_nodes (
	node_type VARCHAR(32) NOT NULL, 
	redacted_value TEXT NOT NULL, 
	value_sha256 VARCHAR(64) NOT NULL, 
	attributes JSON NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_graph_nodes PRIMARY KEY (id), 
	CONSTRAINT uq_graph_nodes_owner_id UNIQUE (owner_id, node_type, value_sha256), 
	CONSTRAINT uq_graph_nodes_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_graph_nodes_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_graph_nodes_owner_id ON graph_nodes (owner_id);

-- statement-breakpoint

CREATE TABLE phone_indicators (
	e164 VARCHAR(16) NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_phone_indicators PRIMARY KEY (id), 
	CONSTRAINT uq_phone_indicators_owner_id UNIQUE (owner_id, e164), 
	CONSTRAINT uq_phone_indicators_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_phone_indicators_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_phone_indicators_owner_id ON phone_indicators (owner_id);

-- statement-breakpoint

CREATE TABLE user_consents (
	purpose VARCHAR(80) NOT NULL, 
	granted BOOLEAN NOT NULL, 
	policy_version VARCHAR(80) NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_user_consents PRIMARY KEY (id), 
	CONSTRAINT uq_user_consents_owner_id UNIQUE (owner_id, purpose), 
	CONSTRAINT uq_user_consents_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_user_consents_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_user_consents_owner_id ON user_consents (owner_id);

-- statement-breakpoint

CREATE TABLE user_profiles (
	locale VARCHAR(32), 
	alert_preferences JSON NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_user_profiles PRIMARY KEY (id), 
	CONSTRAINT uq_user_profiles_owner_id UNIQUE (owner_id), 
	CONSTRAINT uq_user_profiles_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_user_profiles_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_user_profiles_owner_id ON user_profiles (owner_id);

-- statement-breakpoint

CREATE TABLE watchlists (
	indicator_type VARCHAR(32) NOT NULL, 
	redacted_value TEXT NOT NULL, 
	value_sha256 VARCHAR(64) NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_watchlists PRIMARY KEY (id), 
	CONSTRAINT uq_watchlists_owner_id UNIQUE (owner_id, indicator_type, value_sha256), 
	CONSTRAINT uq_watchlists_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_watchlists_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_watchlists_owner_id ON watchlists (owner_id);

-- statement-breakpoint

CREATE TABLE investigations (
	subject_type VARCHAR(16) NOT NULL, 
	subject_value TEXT NOT NULL, 
	source VARCHAR(32) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	device_id CHAR(32), 
	result JSON NOT NULL, 
	expires_at DATETIME NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_investigations PRIMARY KEY (id), 
	CONSTRAINT ck_investigations_subject_type CHECK (subject_type IN ('sms','url','apk','qr','caller')), 
	CONSTRAINT ck_investigations_status CHECK (status IN ('queued','running','completed','partial','failed')), 
	CONSTRAINT fk_investigations_device_id_devices FOREIGN KEY(device_id, owner_id) REFERENCES devices (id, owner_id), 
	CONSTRAINT uq_investigations_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_investigations_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_investigations_expires_at ON investigations (expires_at);

-- statement-breakpoint

CREATE INDEX ix_investigations_owner_created ON investigations (owner_id, created_at, id);

-- statement-breakpoint

CREATE INDEX ix_investigations_owner_id ON investigations (owner_id);

-- statement-breakpoint

CREATE TABLE apk_analysis (
	application_id CHAR(32), 
	sha256 VARCHAR(64) NOT NULL, 
	static_metadata JSON NOT NULL, 
	investigation_id CHAR(32) NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_apk_analysis PRIMARY KEY (id), 
	CONSTRAINT fk_apk_analysis_application_id_applications FOREIGN KEY(application_id, owner_id) REFERENCES applications (id, owner_id), 
	CONSTRAINT fk_apk_analysis_investigation_id_investigations FOREIGN KEY(investigation_id, owner_id) REFERENCES investigations (id, owner_id) ON DELETE CASCADE, 
	CONSTRAINT uq_apk_analysis_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_apk_analysis_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_apk_analysis_investigation_id ON apk_analysis (investigation_id);

-- statement-breakpoint

CREATE INDEX ix_apk_analysis_owner_id ON apk_analysis (owner_id);

-- statement-breakpoint

CREATE INDEX ix_apk_analysis_sha256 ON apk_analysis (sha256);

-- statement-breakpoint

CREATE TABLE evidence_sources (
	name VARCHAR(100) NOT NULL, 
	kind VARCHAR(32) NOT NULL, 
	reference TEXT, 
	status VARCHAR(40) NOT NULL, 
	observed_at DATETIME NOT NULL, 
	investigation_id CHAR(32) NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_evidence_sources PRIMARY KEY (id), 
	CONSTRAINT fk_evidence_sources_investigation_id_investigations FOREIGN KEY(investigation_id, owner_id) REFERENCES investigations (id, owner_id) ON DELETE CASCADE, 
	CONSTRAINT uq_evidence_sources_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_evidence_sources_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_evidence_sources_investigation_id ON evidence_sources (investigation_id);

-- statement-breakpoint

CREATE INDEX ix_evidence_sources_owner_id ON evidence_sources (owner_id);

-- statement-breakpoint

CREATE TABLE investigation_events (
	event_type VARCHAR(80) NOT NULL, 
	details JSON NOT NULL, 
	investigation_id CHAR(32) NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_investigation_events PRIMARY KEY (id), 
	CONSTRAINT fk_investigation_events_investigation_id_investigations FOREIGN KEY(investigation_id, owner_id) REFERENCES investigations (id, owner_id) ON DELETE CASCADE, 
	CONSTRAINT uq_investigation_events_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_investigation_events_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_investigation_events_investigation_id ON investigation_events (investigation_id);

-- statement-breakpoint

CREATE INDEX ix_investigation_events_owner_id ON investigation_events (owner_id);

-- statement-breakpoint

CREATE TABLE model_predictions (
	model_version_id CHAR(32) NOT NULL, 
	label VARCHAR(32) NOT NULL, 
	decision_score FLOAT, 
	score_type VARCHAR(64), 
	inferred_at DATETIME NOT NULL, 
	investigation_id CHAR(32) NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_model_predictions PRIMARY KEY (id), 
	CONSTRAINT fk_model_predictions_investigation_id_investigations FOREIGN KEY(investigation_id, owner_id) REFERENCES investigations (id, owner_id) ON DELETE CASCADE, 
	CONSTRAINT uq_model_predictions_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_model_predictions_model_version_id_model_versions FOREIGN KEY(model_version_id) REFERENCES model_versions (id), 
	CONSTRAINT fk_model_predictions_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_model_predictions_investigation_id ON model_predictions (investigation_id);

-- statement-breakpoint

CREATE INDEX ix_model_predictions_model_version_id ON model_predictions (model_version_id);

-- statement-breakpoint

CREATE INDEX ix_model_predictions_owner_id ON model_predictions (owner_id);

-- statement-breakpoint

CREATE TABLE qr_analyses (
	content_type VARCHAR(32) NOT NULL, 
	redacted_content TEXT NOT NULL, 
	decoded_attributes JSON NOT NULL, 
	investigation_id CHAR(32) NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_qr_analyses PRIMARY KEY (id), 
	CONSTRAINT fk_qr_analyses_investigation_id_investigations FOREIGN KEY(investigation_id, owner_id) REFERENCES investigations (id, owner_id) ON DELETE CASCADE, 
	CONSTRAINT uq_qr_analyses_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_qr_analyses_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_qr_analyses_investigation_id ON qr_analyses (investigation_id);

-- statement-breakpoint

CREATE INDEX ix_qr_analyses_owner_id ON qr_analyses (owner_id);

-- statement-breakpoint

CREATE TABLE security_alerts (
	severity VARCHAR(16) NOT NULL, 
	message TEXT NOT NULL, 
	read_at DATETIME, 
	investigation_id CHAR(32) NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_security_alerts PRIMARY KEY (id), 
	CONSTRAINT ck_security_alerts_severity CHECK (severity IN ('info','caution','high')), 
	CONSTRAINT fk_security_alerts_investigation_id_investigations FOREIGN KEY(investigation_id, owner_id) REFERENCES investigations (id, owner_id) ON DELETE CASCADE, 
	CONSTRAINT uq_security_alerts_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_security_alerts_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_security_alerts_investigation_id ON security_alerts (investigation_id);

-- statement-breakpoint

CREATE INDEX ix_security_alerts_owner_id ON security_alerts (owner_id);

-- statement-breakpoint

CREATE TABLE urls (
	domain_id CHAR(32) NOT NULL, 
	redacted_value TEXT NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	investigation_id CHAR(32) NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_urls PRIMARY KEY (id), 
	CONSTRAINT uq_urls_investigation_id UNIQUE (investigation_id, sha256), 
	CONSTRAINT fk_urls_domain_id_domains FOREIGN KEY(domain_id, owner_id) REFERENCES domains (id, owner_id), 
	CONSTRAINT fk_urls_investigation_id_investigations FOREIGN KEY(investigation_id, owner_id) REFERENCES investigations (id, owner_id) ON DELETE CASCADE, 
	CONSTRAINT uq_urls_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_urls_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_urls_investigation_id ON urls (investigation_id);

-- statement-breakpoint

CREATE INDEX ix_urls_owner_id ON urls (owner_id);

-- statement-breakpoint

CREATE TABLE evidence (
	source_id CHAR(32) NOT NULL, 
	code VARCHAR(100) NOT NULL, 
	description TEXT NOT NULL, 
	severity VARCHAR(16) NOT NULL, 
	verification_status VARCHAR(40) NOT NULL, 
	attributes JSON NOT NULL, 
	observed_at DATETIME NOT NULL, 
	investigation_id CHAR(32) NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_evidence PRIMARY KEY (id), 
	CONSTRAINT fk_evidence_source_id_evidence_sources FOREIGN KEY(source_id, owner_id) REFERENCES evidence_sources (id, owner_id), 
	CONSTRAINT ck_evidence_severity CHECK (severity IN ('info','caution','high')), 
	CONSTRAINT fk_evidence_investigation_id_investigations FOREIGN KEY(investigation_id, owner_id) REFERENCES investigations (id, owner_id) ON DELETE CASCADE, 
	CONSTRAINT uq_evidence_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_evidence_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_evidence_investigation_id ON evidence (investigation_id);

-- statement-breakpoint

CREATE INDEX ix_evidence_owner_id ON evidence (owner_id);

-- statement-breakpoint

CREATE TABLE threat_intelligence_results (
	source_id CHAR(32) NOT NULL, 
	provider VARCHAR(80) NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	verdict VARCHAR(32), 
	details JSON NOT NULL, 
	observed_at DATETIME NOT NULL, 
	investigation_id CHAR(32) NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_threat_intelligence_results PRIMARY KEY (id), 
	CONSTRAINT fk_threat_intelligence_results_source_id_evidence_sources FOREIGN KEY(source_id, owner_id) REFERENCES evidence_sources (id, owner_id), 
	CONSTRAINT fk_threat_intelligence_results_investigation_id_investigations FOREIGN KEY(investigation_id, owner_id) REFERENCES investigations (id, owner_id) ON DELETE CASCADE, 
	CONSTRAINT uq_threat_intelligence_results_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_threat_intelligence_results_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_threat_intelligence_results_investigation_id ON threat_intelligence_results (investigation_id);

-- statement-breakpoint

CREATE INDEX ix_threat_intelligence_results_owner_id ON threat_intelligence_results (owner_id);

-- statement-breakpoint

CREATE TABLE graph_edges (
	from_node_id CHAR(32) NOT NULL, 
	to_node_id CHAR(32) NOT NULL, 
	evidence_id CHAR(32) NOT NULL, 
	relationship_type VARCHAR(64) NOT NULL, 
	investigation_id CHAR(32) NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_graph_edges PRIMARY KEY (id), 
	CONSTRAINT fk_graph_edges_from_node_id_graph_nodes FOREIGN KEY(from_node_id, owner_id) REFERENCES graph_nodes (id, owner_id) ON DELETE CASCADE, 
	CONSTRAINT fk_graph_edges_to_node_id_graph_nodes FOREIGN KEY(to_node_id, owner_id) REFERENCES graph_nodes (id, owner_id) ON DELETE CASCADE, 
	CONSTRAINT fk_graph_edges_evidence_id_evidence FOREIGN KEY(evidence_id, owner_id) REFERENCES evidence (id, owner_id) ON DELETE CASCADE, 
	CONSTRAINT uq_graph_edges_investigation_id UNIQUE (investigation_id, from_node_id, to_node_id, relationship_type, evidence_id), 
	CONSTRAINT ck_graph_edges_no_self_edge CHECK (from_node_id <> to_node_id), 
	CONSTRAINT fk_graph_edges_investigation_id_investigations FOREIGN KEY(investigation_id, owner_id) REFERENCES investigations (id, owner_id) ON DELETE CASCADE, 
	CONSTRAINT uq_graph_edges_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_graph_edges_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_graph_edges_investigation_id ON graph_edges (investigation_id);

-- statement-breakpoint

CREATE INDEX ix_graph_edges_owner_id ON graph_edges (owner_id);

-- statement-breakpoint

CREATE TABLE risk_assessments (
	classification VARCHAR(32) NOT NULL, 
	risk_score FLOAT, 
	score_type VARCHAR(64), 
	explanation TEXT NOT NULL, 
	methodology_version VARCHAR(80) NOT NULL, 
	missing_information JSON NOT NULL, 
	human_reviewed_at DATETIME, 
	authoritative_evidence_id CHAR(32), 
	investigation_id CHAR(32) NOT NULL, 
	id CHAR(32) NOT NULL, 
	owner_id CHAR(32) NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT pk_risk_assessments PRIMARY KEY (id), 
	CONSTRAINT uq_risk_assessments_investigation_id UNIQUE (investigation_id), 
	CONSTRAINT ck_risk_assessments_classification CHECK (classification IN ('SAFE_INDICATORS','EXERCISE_CAUTION','HIGH_RISK','CONFIRMED_FRAUD')), 
	CONSTRAINT ck_risk_assessments_score_range CHECK (risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 100)), 
	CONSTRAINT ck_risk_assessments_score_type CHECK ((risk_score IS NULL AND score_type IS NULL) OR (risk_score IS NOT NULL AND score_type IS NOT NULL)), 
	CONSTRAINT ck_risk_assessments_confirmed_review CHECK (classification <> 'CONFIRMED_FRAUD' OR (human_reviewed_at IS NOT NULL AND authoritative_evidence_id IS NOT NULL)), 
	CONSTRAINT fk_risk_assessments_authoritative_evidence_id_evidence FOREIGN KEY(authoritative_evidence_id, owner_id) REFERENCES evidence (id, owner_id), 
	CONSTRAINT fk_risk_assessments_investigation_id_investigations FOREIGN KEY(investigation_id, owner_id) REFERENCES investigations (id, owner_id) ON DELETE CASCADE, 
	CONSTRAINT uq_risk_assessments_id UNIQUE (id, owner_id), 
	CONSTRAINT fk_risk_assessments_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- statement-breakpoint

CREATE INDEX ix_risk_assessments_investigation_id ON risk_assessments (investigation_id);

-- statement-breakpoint

CREATE INDEX ix_risk_assessments_owner_id ON risk_assessments (owner_id);
