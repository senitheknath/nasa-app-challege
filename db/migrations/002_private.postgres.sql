-- Private records remain closed until an identity adapter explicitly grants a role.
CREATE TABLE farm_profiles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL, profile jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(), UNIQUE (id,owner_id)
);
CREATE INDEX farm_profiles_owner ON farm_profiles(owner_id);
CREATE TABLE saved_analyses (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL, farm_id uuid NOT NULL,
  report jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY(farm_id,owner_id) REFERENCES farm_profiles(id,owner_id) ON DELETE CASCADE
);
CREATE INDEX saved_analyses_owner ON saved_analyses(owner_id,farm_id);
ALTER TABLE farm_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE farm_profiles FORCE ROW LEVEL SECURITY;
ALTER TABLE saved_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_analyses FORCE ROW LEVEL SECURITY;
REVOKE ALL ON farm_profiles,saved_analyses FROM PUBLIC;
