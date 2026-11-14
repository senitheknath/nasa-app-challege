CREATE TABLE ag_name_token (
    pack_id TEXT NOT NULL REFERENCES ag_pack(id),
    crop_id TEXT NOT NULL REFERENCES ag_crop(id),
    token TEXT NOT NULL,
    PRIMARY KEY (pack_id, crop_id, token)
);
CREATE INDEX ag_token_search ON ag_name_token(token, crop_id);
