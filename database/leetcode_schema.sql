CREATE TABLE leetcode_contests (
  id INTEGER UNSIGNED PRIMARY KEY,
  name VARCHAR(32),
  slug VARCHAR(32),
  start_time INTEGER UNSIGNED,
  duration MEDIUMINT UNSIGNED
);

CREATE TABLE leetcode_user (
  handle VARCHAR(24) PRIMARY KEY,
  country VARCHAR(32),
  city VARCHAR(32),
  max_rating SMALLINT UNSIGNED,
  registered INTEGER UNSIGNED
);