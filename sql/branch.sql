BEGIN;
    CREATE TABLE worker_coordination (npm_last_seq bigint not null default -1);
    INSERT INTO worker_coordination DEFAULT VALUES;
END;
