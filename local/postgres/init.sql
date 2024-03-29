-- TODO this needs to be manually kept up to date with the sqlalchemy schemas
\connect document_store;

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS api_keys (
  id UUID PRIMARY KEY,
  api_key VARCHAR(255) UNIQUE NOT NULL,
  contact_name VARCHAR(255) NOT NULL,
  contact_email VARCHAR(255) NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  write_enabled BOOLEAN NOT NULL DEFAULT FALSE
);

INSERT INTO api_keys VALUES
(gen_random_uuid(), 'sample-api-key', 'sample user', 'sample@example.com', TRUE, TRUE);

COMMIT;
