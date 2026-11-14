ALTER TABLE farm_profiles ADD COLUMN revision integer NOT NULL DEFAULT 1 CHECK (revision > 0);
ALTER TABLE farm_profiles ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE saved_analyses ADD COLUMN fingerprint text;
CREATE UNIQUE INDEX saved_analysis_fingerprint ON saved_analyses(owner_id,farm_id,fingerprint);
CREATE INDEX saved_analysis_history ON saved_analyses(owner_id,farm_id,created_at DESC);
CREATE TABLE farmer_accounts (
 owner_id uuid PRIMARY KEY, display_name text NOT NULL DEFAULT '',
 updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE farmer_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE farmer_accounts FORCE ROW LEVEL SECURITY;
REVOKE ALL ON farmer_accounts FROM PUBLIC;
