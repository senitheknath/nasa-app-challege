-- Prefix ranges use byte ordering consistently across server locales.
CREATE INDEX ag_token_search_binary ON ag_name_token(token COLLATE "C",crop_id);
