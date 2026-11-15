-- Provision agroshift_reader as a separate, non-superuser login before applying this grant.
GRANT USAGE ON SCHEMA agroshift TO agroshift_reader;
GRANT SELECT ON agroshift.ag_catalogue_cited,agroshift.ag_global_trait_named,agroshift.ag_name_token,agroshift.ag_crop_name,agroshift.ag_pack,agroshift.ag_growth_stage_reviewed,agroshift.ag_pest_context_reviewed,agroshift.ag_cultivar_trait_reviewed,agroshift.ag_soil_observation,agroshift.ag_validation_observation,agroshift.ag_refresh_policy TO agroshift_reader;
