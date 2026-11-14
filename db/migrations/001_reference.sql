-- Shared SQL for PostgreSQL and the SQLite reference cache.
CREATE TABLE ag_pack (
  id TEXT PRIMARY KEY,
  version TEXT NOT NULL,
  digest TEXT NOT NULL
);
CREATE TABLE ag_import_history (
  id TEXT PRIMARY KEY,
  pack_id TEXT NOT NULL,
  version TEXT,
  digest TEXT NOT NULL,
  finished_at TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('imported','failed')),
  detail TEXT NOT NULL
);
CREATE INDEX ag_import_pack ON ag_import_history(pack_id, finished_at);
CREATE TABLE ag_region (id TEXT PRIMARY KEY, name TEXT NOT NULL, country_code TEXT);
CREATE TABLE ag_source (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, url TEXT NOT NULL, license TEXT, source_version TEXT
);
CREATE TABLE ag_family (name TEXT PRIMARY KEY);
CREATE TABLE ag_crop (id TEXT PRIMARY KEY);
CREATE TABLE ag_crop_record (
  pack_id TEXT NOT NULL REFERENCES ag_pack(id), crop_id TEXT NOT NULL REFERENCES ag_crop(id),
  name TEXT NOT NULL, scientific_name TEXT, group_name TEXT, family TEXT REFERENCES ag_family(name),
  life_cycle TEXT, concept_uri TEXT,
  PRIMARY KEY (pack_id,crop_id)
);
CREATE TABLE ag_crop_name (
  pack_id TEXT NOT NULL REFERENCES ag_pack(id), crop_id TEXT NOT NULL REFERENCES ag_crop(id),
  language TEXT NOT NULL, name TEXT NOT NULL, search_key TEXT NOT NULL,
  source_id TEXT REFERENCES ag_source(id),
  PRIMARY KEY (pack_id,crop_id,language,name)
);
CREATE INDEX ag_name_lookup ON ag_crop_name(search_key, crop_id);
CREATE TABLE ag_cultivar (
  id TEXT PRIMARY KEY, crop_id TEXT NOT NULL REFERENCES ag_crop(id), name TEXT NOT NULL,
  UNIQUE(crop_id,name), UNIQUE(crop_id,id)
);
CREATE TABLE ag_evidence (
  id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES ag_pack(id), crop_id TEXT NOT NULL REFERENCES ag_crop(id),
  trait TEXT NOT NULL, low DOUBLE PRECISION, high DOUBLE PRECISION, value_text TEXT, units TEXT,
  region_id TEXT NOT NULL REFERENCES ag_region(id), cultivar_id TEXT, farming_system TEXT,
  source_id TEXT NOT NULL REFERENCES ag_source(id), source_version TEXT, retrieved_on TEXT,
  evidence_type TEXT NOT NULL, review_status TEXT NOT NULL CHECK (review_status IN ('reviewed','pending','rejected')),
  note TEXT, source_url TEXT NOT NULL,
  FOREIGN KEY(crop_id,cultivar_id) REFERENCES ag_cultivar(crop_id,id),
  CHECK ((low IS NOT NULL AND high IS NOT NULL AND low <= high AND units IS NOT NULL AND value_text IS NULL)
    OR (low IS NULL AND high IS NULL AND value_text IS NOT NULL))
);
CREATE INDEX ag_trait_lookup ON ag_evidence(region_id, review_status, crop_id, trait);
CREATE TABLE ag_growing_calendar (
  id TEXT PRIMARY KEY, crop_id TEXT NOT NULL REFERENCES ag_crop(id), region_id TEXT NOT NULL REFERENCES ag_region(id),
  cultivar_id TEXT, farming_system TEXT, planting_start TEXT, planting_end TEXT,
  harvest_start TEXT, harvest_end TEXT, evidence_id TEXT NOT NULL REFERENCES ag_evidence(id),
  FOREIGN KEY(crop_id,cultivar_id) REFERENCES ag_cultivar(crop_id,id)
);
CREATE TABLE ag_rotation_constraint (
  id TEXT PRIMARY KEY, first_crop TEXT REFERENCES ag_crop(id), second_crop TEXT REFERENCES ag_crop(id),
  region_id TEXT NOT NULL REFERENCES ag_region(id), rule_text TEXT NOT NULL,
  evidence_id TEXT NOT NULL REFERENCES ag_evidence(id)
);
CREATE TABLE ag_provider_status (
  provider TEXT PRIMARY KEY, last_check TEXT NOT NULL, outcome TEXT NOT NULL, detail TEXT NOT NULL
);
CREATE TABLE ag_nasa_cache (
  id TEXT PRIMARY KEY, latitude DOUBLE PRECISION NOT NULL, longitude DOUBLE PRECISION NOT NULL,
  period_start TEXT NOT NULL, period_end TEXT NOT NULL, object_ref TEXT NOT NULL,
  payload_digest TEXT NOT NULL, retrieved_at TEXT NOT NULL, source_kind TEXT NOT NULL
);
CREATE TABLE ag_regional_crop (
  pack_id TEXT NOT NULL REFERENCES ag_pack(id), crop_id TEXT NOT NULL REFERENCES ag_crop(id),
  region_id TEXT NOT NULL REFERENCES ag_region(id), PRIMARY KEY(pack_id,crop_id,region_id)
);
-- Different published values within the same applicability are retained for curation.
CREATE VIEW ag_conflicts AS
 SELECT DISTINCT a.id AS evidence_id FROM ag_evidence a JOIN ag_evidence b
 ON a.id <> b.id AND a.crop_id=b.crop_id AND a.trait=b.trait AND a.region_id=b.region_id
 AND COALESCE(a.cultivar_id,'')=COALESCE(b.cultivar_id,'') AND COALESCE(a.farming_system,'')=COALESCE(b.farming_system,'')
 WHERE a.review_status='reviewed' AND b.review_status='reviewed'
 AND (a.low IS DISTINCT FROM b.low OR a.high IS DISTINCT FROM b.high OR a.value_text IS DISTINCT FROM b.value_text OR a.units IS DISTINCT FROM b.units);
CREATE VIEW ag_global_trait AS
 SELECT e.crop_id,e.trait,e.low,e.high,e.units,e.source_id,e.source_url,e.evidence_type,e.region_id AS scope,
        e.note,e.source_version AS version,e.retrieved_on,e.farming_system AS system,c.name AS cultivar,e.review_status
 FROM ag_evidence e LEFT JOIN ag_cultivar c ON e.cultivar_id=c.id
 WHERE e.region_id='global' AND e.review_status='reviewed' AND e.low IS NOT NULL
 AND NOT EXISTS(SELECT 1 FROM ag_conflicts x WHERE x.evidence_id=e.id);
CREATE VIEW ag_catalogue AS
 SELECT c.id, COALESCE(g.name,r.name) AS name, COALESCE(g.scientific_name,r.scientific_name) AS scientific_name,
 COALESCE(g.family,r.family) AS family, g.group_name, g.life_cycle, g.concept_uri,
 CASE WHEN EXISTS(SELECT 1 FROM ag_regional_crop p WHERE p.crop_id=c.id) THEN 'regional'
 WHEN EXISTS(SELECT 1 FROM ag_global_trait t WHERE t.crop_id=c.id AND t.cultivar IS NULL AND t.system IS NULL) THEN 'general' ELSE 'catalogue' END AS support_level
 FROM ag_crop c LEFT JOIN ag_crop_record g ON g.crop_id=c.id AND g.pack_id='global'
 LEFT JOIN ag_crop_record r ON r.crop_id=c.id AND r.pack_id='lk'
 WHERE g.crop_id IS NOT NULL OR r.crop_id IS NOT NULL;
