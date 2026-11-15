CREATE TABLE ag_cultivar_trait (
    id TEXT PRIMARY KEY,
    pack_id TEXT NOT NULL REFERENCES ag_pack(id),
    cultivar_id TEXT NOT NULL REFERENCES ag_cultivar(id),
    crop_id TEXT NOT NULL REFERENCES ag_crop(id),
    trait TEXT NOT NULL,
    min_value DOUBLE PRECISION,
    max_value DOUBLE PRECISION,
    value_text TEXT,
    unit TEXT,
    region_id TEXT NOT NULL REFERENCES ag_region(id),
    source_id TEXT NOT NULL REFERENCES ag_source(id),
    source_version TEXT,
    retrieved_on TEXT,
    review_status TEXT NOT NULL CHECK (review_status IN ('reviewed','pending','rejected')),
    note TEXT,
    source_url TEXT NOT NULL,
    CHECK (
        (value_text IS NOT NULL AND min_value IS NULL AND max_value IS NULL) OR
        (value_text IS NULL AND min_value IS NOT NULL AND max_value IS NOT NULL AND min_value <= max_value)
    )
);

CREATE INDEX ag_cultivar_trait_crop_idx ON ag_cultivar_trait(crop_id, review_status);

CREATE TABLE ag_growth_stage (
    id TEXT PRIMARY KEY,
    pack_id TEXT NOT NULL REFERENCES ag_pack(id),
    crop_id TEXT NOT NULL REFERENCES ag_crop(id),
    stage_code TEXT NOT NULL CHECK (stage_code IN ('initial','development','mid_season','late_season')),
    stage_order INTEGER NOT NULL CHECK (stage_order BETWEEN 1 AND 4),
    duration_fraction_min DOUBLE PRECISION NOT NULL CHECK (duration_fraction_min >= 0 AND duration_fraction_min <= 1),
    duration_fraction_max DOUBLE PRECISION NOT NULL CHECK (duration_fraction_max >= duration_fraction_min AND duration_fraction_max <= 1),
    kc_min DOUBLE PRECISION NOT NULL CHECK (kc_min >= 0 AND kc_min <= 2.5),
    kc_max DOUBLE PRECISION NOT NULL CHECK (kc_max >= kc_min AND kc_max <= 2.5),
    depletion_fraction_p DOUBLE PRECISION CHECK (depletion_fraction_p IS NULL OR (depletion_fraction_p > 0 AND depletion_fraction_p < 1)),
    critical_tmin_c DOUBLE PRECISION,
    critical_tmax_c DOUBLE PRECISION,
    ky_yield_response DOUBLE PRECISION CHECK (ky_yield_response IS NULL OR (ky_yield_response >= 0 AND ky_yield_response <= 3.0)),
    waterlogging_sensitive INTEGER NOT NULL DEFAULT 0 CHECK (waterlogging_sensitive IN (0, 1)),
    source_id TEXT NOT NULL REFERENCES ag_source(id),
    source_version TEXT,
    retrieved_on TEXT,
    review_status TEXT NOT NULL CHECK (review_status IN ('reviewed','pending','rejected')),
    note TEXT,
    source_url TEXT NOT NULL,
    UNIQUE (pack_id, crop_id, stage_code, source_id)
);

CREATE INDEX ag_growth_stage_crop_idx ON ag_growth_stage(crop_id, stage_order);

CREATE TABLE ag_soil_observation (
    id TEXT PRIMARY KEY,
    pack_id TEXT NOT NULL REFERENCES ag_pack(id),
    source_id TEXT NOT NULL REFERENCES ag_source(id),
    dataset_code TEXT NOT NULL,
    profile_code TEXT NOT NULL,
    country_code TEXT,
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    upper_depth_cm DOUBLE PRECISION NOT NULL CHECK (upper_depth_cm >= 0),
    lower_depth_cm DOUBLE PRECISION NOT NULL CHECK (lower_depth_cm > upper_depth_cm),
    property TEXT NOT NULL,
    raw_value DOUBLE PRECISION,
    raw_unit TEXT,
    normalized_value DOUBLE PRECISION,
    normalized_unit TEXT NOT NULL,
    uncertainty_low DOUBLE PRECISION,
    uncertainty_high DOUBLE PRECISION,
    observation_kind TEXT NOT NULL CHECK (observation_kind IN ('measured_profile','modelled_grid','regional_survey')),
    observed_date TEXT,
    retrieved_on TEXT NOT NULL
);

CREATE INDEX ag_soil_observation_coord_idx ON ag_soil_observation(country_code, property);

CREATE TABLE ag_pest_context (
    id TEXT PRIMARY KEY,
    pack_id TEXT NOT NULL REFERENCES ag_pack(id),
    crop_id TEXT NOT NULL REFERENCES ag_crop(id),
    agent_name TEXT NOT NULL,
    scientific_name TEXT,
    category TEXT NOT NULL CHECK (category IN ('fungal_oomycete','bacterial','viral','insect_mite','nematode','weed','abiotic')),
    favorable_condition TEXT NOT NULL,
    susceptible_stage TEXT NOT NULL,
    cultural_notes TEXT NOT NULL,
    region_id TEXT NOT NULL REFERENCES ag_region(id),
    source_id TEXT NOT NULL REFERENCES ag_source(id),
    source_version TEXT,
    retrieved_on TEXT,
    review_status TEXT NOT NULL CHECK (review_status IN ('reviewed','pending','rejected')),
    source_url TEXT NOT NULL
);

CREATE INDEX ag_pest_context_crop_idx ON ag_pest_context(crop_id, review_status);

CREATE TABLE ag_validation_observation (
    id TEXT PRIMARY KEY,
    pack_id TEXT NOT NULL REFERENCES ag_pack(id),
    station_key TEXT NOT NULL,
    country_code TEXT NOT NULL,
    crop_id TEXT NOT NULL REFERENCES ag_crop(id),
    water_regime TEXT NOT NULL CHECK (water_regime IN ('rainfed','irrigated')),
    reference_type TEXT NOT NULL CHECK (reference_type IN ('gaez_v5_suitability','faostat_national_production','regional_extension_pack')),
    reference_value DOUBLE PRECISION,
    reference_code TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES ag_source(id),
    retrieved_on TEXT NOT NULL,
    note TEXT
);

CREATE INDEX ag_validation_obs_station_idx ON ag_validation_observation(station_key, crop_id);

CREATE TABLE ag_refresh_policy (
    dataset_id TEXT PRIMARY KEY,
    pack_id TEXT NOT NULL REFERENCES ag_pack(id),
    provider_name TEXT NOT NULL,
    refresh_cadence_days INTEGER NOT NULL CHECK (refresh_cadence_days > 0),
    expected_format TEXT NOT NULL,
    expected_crs TEXT,
    expected_dimensions TEXT,
    require_sha256 INTEGER NOT NULL DEFAULT 1 CHECK (require_sha256 IN (0, 1)),
    allow_live_farmer_path INTEGER NOT NULL DEFAULT 0 CHECK (allow_live_farmer_path IN (0, 1)),
    fallback_policy TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES ag_source(id),
    updated_on TEXT NOT NULL
);

CREATE VIEW ag_growth_stage_reviewed AS
SELECT
    g.crop_id,
    g.stage_code,
    g.stage_order,
    g.duration_fraction_min,
    g.duration_fraction_max,
    g.kc_min,
    g.kc_max,
    g.depletion_fraction_p,
    g.critical_tmin_c,
    g.critical_tmax_c,
    g.ky_yield_response,
    g.waterlogging_sensitive,
    g.source_id,
    s.title AS source_title,
    g.source_url,
    g.source_version,
    g.retrieved_on,
    g.note,
    g.review_status
FROM ag_growth_stage g
JOIN ag_source s ON s.id = g.source_id
WHERE g.review_status = 'reviewed';

CREATE VIEW ag_pest_context_reviewed AS
SELECT
    p.crop_id,
    p.agent_name,
    p.scientific_name,
    p.category,
    p.favorable_condition,
    p.susceptible_stage,
    p.cultural_notes,
    p.region_id,
    p.source_id,
    s.title AS source_title,
    p.source_url,
    p.source_version,
    p.retrieved_on,
    p.review_status
FROM ag_pest_context p
JOIN ag_source s ON s.id = p.source_id
WHERE p.review_status = 'reviewed';

CREATE VIEW ag_cultivar_trait_reviewed AS
SELECT
    ct.crop_id,
    ct.cultivar_id,
    c.name AS cultivar_name,
    ct.trait,
    ct.min_value AS low,
    ct.max_value AS high,
    ct.value_text,
    ct.unit AS units,
    ct.region_id AS scope,
    ct.source_id,
    s.title AS source_title,
    ct.source_url,
    ct.source_version,
    ct.retrieved_on,
    ct.note,
    ct.review_status
FROM ag_cultivar_trait ct
JOIN ag_cultivar c ON c.id = ct.cultivar_id
JOIN ag_source s ON s.id = ct.source_id
WHERE ct.review_status = 'reviewed';
