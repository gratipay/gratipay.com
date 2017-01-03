BEGIN;

    ALTER TABLE statements ADD COLUMN content_scrubbed text NOT NULL DEFAULT '';

    DROP TRIGGER search_vector_update ON statements;
    CREATE TRIGGER search_vector_update
        BEFORE INSERT OR UPDATE ON statements
        FOR EACH ROW EXECUTE PROCEDURE
        tsvector_update_trigger_column(search_vector, search_conf, content_scrubbed);

END;
