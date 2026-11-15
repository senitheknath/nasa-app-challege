CREATE VIEW ag_global_trait_named AS
 SELECT t.*, s.title AS source_title FROM ag_global_trait t JOIN ag_source s ON t.source_id=s.id;
