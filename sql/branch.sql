CREATE TABLE countries -- http://www.iso.org/iso/country_codes
( id    bigserial   primary key
, code  text        NOT NULL UNIQUE
 );

\i sql/countries.sql
