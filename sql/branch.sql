ALTER TABLE emails ADD COLUMN participant_id bigint DEFAULT NULL
	REFERENCES participants(id) ON UPDATE RESTRICT ON DELETE RESTRICT;

ALTER TABLE emails ADD UNIQUE (participant_id, address);