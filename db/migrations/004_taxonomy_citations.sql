CREATE VIEW ag_catalogue_cited AS
 WITH citations AS (
   SELECT e.crop_id,e.value_text,e.source_id,e.source_url,
          row_number() OVER (PARTITION BY e.crop_id,e.value_text ORDER BY
            CASE WHEN e.pack_id='global' THEN 0 ELSE 1 END,e.source_id,e.id) AS n
   FROM ag_evidence e WHERE e.trait='family' AND e.review_status='reviewed'
 )
 SELECT c.*,q.source_id AS family_source_id,q.source_url AS family_reference
 FROM ag_catalogue c LEFT JOIN citations q
 ON q.crop_id=c.id AND q.value_text=c.family AND q.n=1;
