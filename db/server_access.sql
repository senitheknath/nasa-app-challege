-- Trusted server only: never grant agroshift_app to browser/PostgREST roles.
-- Provision a non-superuser, non-BYPASSRLS agroshift_app LOGIN first.
GRANT USAGE ON SCHEMA agroshift TO agroshift_app;
GRANT SELECT,INSERT,UPDATE ON agroshift.farm_profiles,agroshift.farmer_accounts TO agroshift_app;
GRANT SELECT,INSERT ON agroshift.saved_analyses TO agroshift_app;
DROP POLICY IF EXISTS server_farm_owner ON agroshift.farm_profiles;
CREATE POLICY server_farm_owner ON agroshift.farm_profiles TO agroshift_app
 USING (owner_id = nullif(current_setting('agroshift.owner_id',true),'')::uuid)
 WITH CHECK (owner_id = nullif(current_setting('agroshift.owner_id',true),'')::uuid);
DROP POLICY IF EXISTS server_analysis_owner ON agroshift.saved_analyses;
CREATE POLICY server_analysis_owner ON agroshift.saved_analyses TO agroshift_app
 USING (owner_id = nullif(current_setting('agroshift.owner_id',true),'')::uuid)
 WITH CHECK (owner_id = nullif(current_setting('agroshift.owner_id',true),'')::uuid);
DROP POLICY IF EXISTS server_account_owner ON agroshift.farmer_accounts;
CREATE POLICY server_account_owner ON agroshift.farmer_accounts TO agroshift_app
 USING (owner_id = nullif(current_setting('agroshift.owner_id',true),'')::uuid)
 WITH CHECK (owner_id = nullif(current_setting('agroshift.owner_id',true),'')::uuid);
