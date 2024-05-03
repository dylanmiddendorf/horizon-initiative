CREATE TABLE codeforces_contest (
  id INTEGER UNSIGNED PRIMARY KEY,
  name VARCHAR(128),
  start_time INTEGER UNSIGNED,
  duration MEDIUMINT UNSIGNED
);

CREATE TABLE codeforces_user (
  handle VARCHAR(24) PRIMARY KEY,
  country VARCHAR(64),
  city VARCHAR(32),
  max_rating SMALLINT UNSIGNED,
  registered INTEGER UNSIGNED
);

CREATE TABLE codeforces_submission (
  id INTEGER UNSIGNED PRIMARY KEY,
  contest_id INTEGER UNSIGNED,
  creation_time INTEGER UNSIGNED,
  problem VARCHAR(8),
  author_handle VARCHAR(24),
  programming_language VARCHAR(32),
  verdict VARCHAR(32),
  FOREIGN KEY (contest_id) REFERENCES codeforces_contest (id),
  FOREIGN KEY (author_handle) REFERENCES codeforces_user (handle)
);
