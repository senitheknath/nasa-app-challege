-- Optional, run after the portable migrations on Supabase with an administrator.
BEGIN;
GRANT USAGE ON SCHEMA agroshift TO authenticated;
GRANT SELECT,INSERT,UPDATE,DELETE ON agroshift.farm_profiles,agroshift.saved_analyses TO authenticated;
DROP POLICY IF EXISTS own_farms ON agroshift.farm_profiles;
CREATE POLICY own_farms ON agroshift.farm_profiles TO authenticated
 USING (owner_id=(SELECT auth.uid())) WITH CHECK (owner_id=(SELECT auth.uid()));
DROP POLICY IF EXISTS own_analyses ON agroshift.saved_analyses;
CREATE POLICY own_analyses ON agroshift.saved_analyses TO authenticated
 USING (owner_id=(SELECT auth.uid())) WITH CHECK (owner_id=(SELECT auth.uid()));
COMMIT;
