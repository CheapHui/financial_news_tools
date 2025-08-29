-- Will be executed on first container start
CREATE EXTENSION IF NOT EXISTS vector;
-- Example: a tiny table to prove pgvector works
-- DROP TABLE IF EXISTS demo_vectors;
CREATE TABLE IF NOT EXISTS demo_vectors (
  id SERIAL PRIMARY KEY,
  title TEXT,
  embedding VECTOR(3)
);

INSERT INTO demo_vectors (title, embedding)
VALUES ('hello', '[1,0,0]'),
       ('world', '[0,1,0]')
ON CONFLICT DO NOTHING;