-- Enable graph for all containers and set default to TRUE

ALTER TABLE containers
    ALTER COLUMN graph_enabled SET DEFAULT TRUE;

UPDATE containers
SET graph_enabled = TRUE
WHERE graph_enabled IS DISTINCT FROM TRUE;

