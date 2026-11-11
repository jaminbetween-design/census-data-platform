-- Schema for the census_data PostgreSQL database (structure only, no data).
-- Generated with: pg_dump --schema-only --no-owner --no-privileges --no-comments census_data
-- Load into an empty database with: psql "$DATABASE_URL" -f sql/schema.sql

--
-- PostgreSQL database dump
--


-- Dumped from database version 16.11 (Homebrew)
-- Dumped by pg_dump version 16.11 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: abs_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.abs_data (
    id integer NOT NULL,
    vintage integer NOT NULL,
    geo_level character varying(50) NOT NULL,
    state_fips character varying(2),
    geo_name character varying(255),
    naics_code character varying(10),
    establishments integer,
    employees integer,
    annual_payroll bigint,
    receipts bigint,
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: abs_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.abs_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: abs_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.abs_data_id_seq OWNED BY public.abs_data.id;


--
-- Name: acs1_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.acs1_data (
    id integer NOT NULL,
    vintage integer NOT NULL,
    geo_level character varying(50) NOT NULL,
    state_fips character varying(2),
    geo_name character varying(255),
    total_population integer,
    median_household_income integer,
    median_age numeric(5,2),
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: acs1_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.acs1_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: acs1_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.acs1_data_id_seq OWNED BY public.acs1_data.id;


--
-- Name: acs_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.acs_data (
    id integer NOT NULL,
    vintage integer NOT NULL,
    geo_level character varying(50) NOT NULL,
    state_fips character varying(2),
    county_fips character varying(3),
    geo_name character varying(255),
    total_population integer,
    median_age numeric(5,2),
    median_household_income integer,
    per_capita_income integer,
    median_home_value integer,
    median_gross_rent integer,
    total_housing_units integer,
    occupied_housing_units integer,
    owner_occupied integer,
    renter_occupied integer,
    labor_force integer,
    unemployed integer,
    bachelors_degree integer,
    masters_degree integer,
    doctorate_degree integer,
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: acs_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.acs_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: acs_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.acs_data_id_seq OWNED BY public.acs_data.id;


--
-- Name: bds_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bds_data (
    id integer NOT NULL,
    vintage integer NOT NULL,
    geo_level character varying(50) NOT NULL,
    state_fips character varying(2),
    county_fips character varying(5),
    cbsa_code character varying(5),
    geo_name character varying(255),
    firms integer,
    establishments integer,
    employees integer,
    job_creation integer,
    job_destruction integer,
    net_job_creation integer,
    job_creation_rate numeric(8,4),
    job_destruction_rate numeric(8,4),
    firm_deaths integer,
    estab_entries integer,
    estab_exits integer,
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: bds_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bds_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bds_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bds_data_id_seq OWNED BY public.bds_data.id;


--
-- Name: cbp_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cbp_data (
    id integer NOT NULL,
    vintage integer NOT NULL,
    geo_level character varying(50) NOT NULL,
    state_fips character varying(2),
    county_fips character varying(3),
    geo_name character varying(255),
    naics_code character varying(10),
    establishments integer,
    employees integer,
    annual_payroll bigint,
    quarterly_payroll_q1 bigint,
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: cbp_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.cbp_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cbp_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.cbp_data_id_seq OWNED BY public.cbp_data.id;


--
-- Name: cps_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cps_data (
    id integer NOT NULL,
    year integer NOT NULL,
    month character varying(3) NOT NULL,
    state_fips character varying(2),
    geo_name character varying(255),
    labor_force_status character varying(10),
    weight numeric(15,2),
    record_count integer DEFAULT 1,
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: cps_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.cps_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cps_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.cps_data_id_seq OWNED BY public.cps_data.id;


--
-- Name: dataset_metadata; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dataset_metadata (
    id integer NOT NULL,
    dataset_name character varying(100) NOT NULL,
    vintage integer NOT NULL,
    api_endpoint character varying(255) NOT NULL,
    description text,
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    row_count integer
);


--
-- Name: dataset_metadata_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.dataset_metadata_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: dataset_metadata_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.dataset_metadata_id_seq OWNED BY public.dataset_metadata.id;


--
-- Name: decennial_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.decennial_data (
    id integer NOT NULL,
    vintage integer NOT NULL,
    geo_level character varying(50) NOT NULL,
    state_fips character varying(2),
    county_fips character varying(3),
    tract character varying(10),
    geo_name character varying(255),
    total_population bigint,
    housing_units integer,
    occupied_housing integer,
    vacant_housing integer,
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: decennial_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.decennial_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: decennial_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.decennial_data_id_seq OWNED BY public.decennial_data.id;


--
-- Name: ec_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ec_data (
    id integer NOT NULL,
    vintage integer NOT NULL,
    geo_level character varying(50) NOT NULL,
    state_fips character varying(2),
    county_fips character varying(3),
    geo_name character varying(255),
    naics_code character varying(10),
    establishments integer,
    employees integer,
    annual_payroll bigint,
    receipts bigint,
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: ec_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ec_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ec_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ec_data_id_seq OWNED BY public.ec_data.id;


--
-- Name: econ_indicators_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.econ_indicators_data (
    id integer NOT NULL,
    indicator_code character varying(20) NOT NULL,
    indicator_name character varying(100),
    time_period character varying(30),
    time_slot_id character varying(20),
    cell_value numeric(20,4),
    data_type_code character varying(50),
    category_code character varying(100),
    seasonally_adj character varying(10),
    error_data character varying(50),
    geo_level_code character varying(20),
    state_fips character varying(2),
    program_code character varying(20),
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: econ_indicators_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.econ_indicators_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: econ_indicators_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.econ_indicators_data_id_seq OWNED BY public.econ_indicators_data.id;


--
-- Name: geography_ref; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geography_ref (
    geo_id character varying(20) NOT NULL,
    geo_level character varying(50) NOT NULL,
    name character varying(255),
    state_fips character varying(2),
    county_fips character varying(3),
    full_fips character varying(11)
);


--
-- Name: hhpulse_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.hhpulse_data (
    id integer NOT NULL,
    survey_year integer,
    cycle character varying(5),
    phase character varying(10),
    geo_level character varying(20),
    geo_name character varying(255),
    state_fips character varying(2),
    cbsa_code character varying(10),
    measure_name character varying(50),
    measure_label character varying(255),
    measure_description text,
    total_count bigint,
    rate numeric(10,4),
    units_total bigint,
    universe bigint,
    col_start_date character varying(50),
    col_end_date character varying(50),
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: hhpulse_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.hhpulse_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: hhpulse_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.hhpulse_data_id_seq OWNED BY public.hhpulse_data.id;


--
-- Name: hps_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.hps_data (
    id integer NOT NULL,
    survey_year integer,
    week character varying(5),
    yr_week_num character varying(10),
    geo_level character varying(20),
    geo_name character varying(255),
    state_fips character varying(2),
    cbsa_code character varying(10),
    indicator_name character varying(50),
    total_count bigint,
    rate numeric(10,4),
    universe bigint,
    units_total bigint,
    col_start_date character varying(50),
    col_end_date character varying(50),
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: hps_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.hps_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: hps_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.hps_data_id_seq OWNED BY public.hps_data.id;


--
-- Name: intltrade_country_ref; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intltrade_country_ref (
    cty_code character varying(4) NOT NULL,
    cty_name character varying(100),
    is_country_group boolean DEFAULT false,
    region character varying(50)
);


--
-- Name: intltrade_exports_hs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intltrade_exports_hs (
    id integer NOT NULL,
    time_period character varying(7) NOT NULL,
    year integer NOT NULL,
    month integer NOT NULL,
    hs_code character varying(10) NOT NULL,
    comm_lvl character varying(4),
    hs_desc_short character varying(100),
    hs_desc_long character varying(255),
    cty_code character varying(4),
    cty_name character varying(100),
    district character varying(2),
    district_name character varying(100),
    df character varying(1),
    summary_lvl character varying(10),
    summary_lvl2 character varying(20),
    all_val_mo bigint,
    all_val_yr bigint,
    air_val_mo bigint,
    air_val_yr bigint,
    ves_val_mo bigint,
    ves_val_yr bigint,
    cnt_val_mo bigint,
    cnt_val_yr bigint,
    air_wgt_mo bigint,
    air_wgt_yr bigint,
    ves_wgt_mo bigint,
    ves_wgt_yr bigint,
    cnt_wgt_mo bigint,
    cnt_wgt_yr bigint,
    unit_qy1 character varying(5),
    unit_qy2 character varying(5),
    qty_1_mo bigint,
    qty_1_yr bigint,
    qty_2_mo bigint,
    qty_2_yr bigint,
    qty_1_mo_flag character varying(1),
    qty_2_mo_flag character varying(1),
    qty_1_yr_flag character varying(1),
    qty_2_yr_flag character varying(1),
    cc_mo integer,
    cc_yr integer,
    last_update date,
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: intltrade_exports_hs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intltrade_exports_hs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intltrade_exports_hs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intltrade_exports_hs_id_seq OWNED BY public.intltrade_exports_hs.id;


--
-- Name: intltrade_imports_hs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intltrade_imports_hs (
    id integer NOT NULL,
    time_period character varying(7) NOT NULL,
    year integer NOT NULL,
    month integer NOT NULL,
    hs_code character varying(10) NOT NULL,
    comm_lvl character varying(4),
    hs_desc_short character varying(100),
    hs_desc_long character varying(255),
    cty_code character varying(4),
    cty_name character varying(100),
    cty_subcode character varying(2),
    district character varying(2),
    district_name character varying(100),
    rp character varying(2),
    summary_lvl character varying(10),
    summary_lvl2 character varying(20),
    gen_val_mo bigint,
    gen_val_yr bigint,
    con_val_mo bigint,
    con_val_yr bigint,
    gen_cif_mo bigint,
    gen_cif_yr bigint,
    con_cif_mo bigint,
    con_cif_yr bigint,
    gen_cha_mo bigint,
    gen_cha_yr bigint,
    con_cha_mo bigint,
    con_cha_yr bigint,
    cal_dut_mo bigint,
    cal_dut_yr bigint,
    dut_val_mo bigint,
    dut_val_yr bigint,
    air_val_mo bigint,
    air_val_yr bigint,
    ves_val_mo bigint,
    ves_val_yr bigint,
    cnt_val_mo bigint,
    cnt_val_yr bigint,
    air_wgt_mo bigint,
    air_wgt_yr bigint,
    ves_wgt_mo bigint,
    ves_wgt_yr bigint,
    cnt_wgt_mo bigint,
    cnt_wgt_yr bigint,
    air_cha_mo bigint,
    air_cha_yr bigint,
    ves_cha_mo bigint,
    ves_cha_yr bigint,
    cnt_cha_mo bigint,
    cnt_cha_yr bigint,
    unit_qy1 character varying(5),
    unit_qy2 character varying(5),
    gen_qy1_mo bigint,
    gen_qy1_yr bigint,
    gen_qy2_mo bigint,
    gen_qy2_yr bigint,
    gen_qy1_mo_flag character varying(1),
    gen_qy2_mo_flag character varying(1),
    gen_qy1_yr_flag character varying(1),
    gen_qy2_yr_flag character varying(1),
    con_qy1_mo bigint,
    con_qy1_yr bigint,
    con_qy2_mo bigint,
    con_qy2_yr bigint,
    con_qy1_mo_flag character varying(1),
    con_qy2_mo_flag character varying(1),
    con_qy1_yr_flag character varying(1),
    con_qy2_yr_flag character varying(1),
    cc_mo integer,
    cc_yr integer,
    last_update date,
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: intltrade_imports_hs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intltrade_imports_hs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intltrade_imports_hs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intltrade_imports_hs_id_seq OWNED BY public.intltrade_imports_hs.id;


--
-- Name: intltrade_ingestion_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.intltrade_ingestion_log (
    id integer NOT NULL,
    dataset character varying(50) NOT NULL,
    time_period character varying(7) NOT NULL,
    comm_lvl character varying(4),
    rows_ingested integer,
    status character varying(20),
    error_message text,
    started_at timestamp without time zone,
    completed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: intltrade_ingestion_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.intltrade_ingestion_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intltrade_ingestion_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.intltrade_ingestion_log_id_seq OWNED BY public.intltrade_ingestion_log.id;


--
-- Name: nes_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nes_data (
    id integer NOT NULL,
    vintage integer NOT NULL,
    geo_level character varying(50) NOT NULL,
    state_fips character varying(2),
    county_fips character varying(3),
    geo_name character varying(255),
    naics_code character varying(10),
    establishments integer,
    receipts bigint,
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: nes_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.nes_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: nes_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.nes_data_id_seq OWNED BY public.nes_data.id;


--
-- Name: pep_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pep_data (
    id integer NOT NULL,
    vintage integer NOT NULL,
    geo_level character varying(50) NOT NULL,
    state_fips character varying(2),
    county_fips character varying(3),
    geo_name character varying(255),
    population integer,
    population_change integer,
    percent_change numeric(6,2),
    density numeric(10,2),
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: pep_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pep_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pep_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pep_data_id_seq OWNED BY public.pep_data.id;


--
-- Name: sahie_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sahie_data (
    id integer NOT NULL,
    vintage integer NOT NULL,
    geo_level character varying(50) NOT NULL,
    state_fips character varying(2),
    county_fips character varying(3),
    geo_name character varying(255),
    uninsured_count integer,
    insured_count integer,
    uninsured_rate numeric(5,2),
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: sahie_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sahie_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sahie_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sahie_data_id_seq OWNED BY public.sahie_data.id;


--
-- Name: saipe_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.saipe_data (
    id integer NOT NULL,
    vintage integer NOT NULL,
    geo_level character varying(50) NOT NULL,
    state_fips character varying(2),
    county_fips character varying(3),
    geo_name character varying(255),
    poverty_count integer,
    poverty_rate numeric(5,2),
    median_household_income integer,
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: saipe_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.saipe_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: saipe_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.saipe_data_id_seq OWNED BY public.saipe_data.id;


--
-- Name: sbo_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sbo_data (
    id integer NOT NULL,
    vintage integer NOT NULL,
    geo_level character varying(50) NOT NULL,
    state_fips character varying(2),
    geo_name character varying(255),
    naics_code character varying(10),
    firms integer,
    receipts bigint,
    employees integer,
    payroll bigint,
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: sbo_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sbo_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sbo_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sbo_data_id_seq OWNED BY public.sbo_data.id;


--
-- Name: zbp_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.zbp_data (
    id integer NOT NULL,
    vintage integer NOT NULL,
    zipcode character varying(5) NOT NULL,
    naics_code character varying(10),
    establishments integer,
    employees integer,
    annual_payroll bigint,
    ingested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: zbp_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.zbp_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: zbp_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.zbp_data_id_seq OWNED BY public.zbp_data.id;


--
-- Name: abs_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.abs_data ALTER COLUMN id SET DEFAULT nextval('public.abs_data_id_seq'::regclass);


--
-- Name: acs1_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acs1_data ALTER COLUMN id SET DEFAULT nextval('public.acs1_data_id_seq'::regclass);


--
-- Name: acs_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acs_data ALTER COLUMN id SET DEFAULT nextval('public.acs_data_id_seq'::regclass);


--
-- Name: bds_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bds_data ALTER COLUMN id SET DEFAULT nextval('public.bds_data_id_seq'::regclass);


--
-- Name: cbp_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cbp_data ALTER COLUMN id SET DEFAULT nextval('public.cbp_data_id_seq'::regclass);


--
-- Name: cps_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cps_data ALTER COLUMN id SET DEFAULT nextval('public.cps_data_id_seq'::regclass);


--
-- Name: dataset_metadata id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_metadata ALTER COLUMN id SET DEFAULT nextval('public.dataset_metadata_id_seq'::regclass);


--
-- Name: decennial_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.decennial_data ALTER COLUMN id SET DEFAULT nextval('public.decennial_data_id_seq'::regclass);


--
-- Name: ec_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ec_data ALTER COLUMN id SET DEFAULT nextval('public.ec_data_id_seq'::regclass);


--
-- Name: econ_indicators_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.econ_indicators_data ALTER COLUMN id SET DEFAULT nextval('public.econ_indicators_data_id_seq'::regclass);


--
-- Name: hhpulse_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hhpulse_data ALTER COLUMN id SET DEFAULT nextval('public.hhpulse_data_id_seq'::regclass);


--
-- Name: hps_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hps_data ALTER COLUMN id SET DEFAULT nextval('public.hps_data_id_seq'::regclass);


--
-- Name: intltrade_exports_hs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intltrade_exports_hs ALTER COLUMN id SET DEFAULT nextval('public.intltrade_exports_hs_id_seq'::regclass);


--
-- Name: intltrade_imports_hs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intltrade_imports_hs ALTER COLUMN id SET DEFAULT nextval('public.intltrade_imports_hs_id_seq'::regclass);


--
-- Name: intltrade_ingestion_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intltrade_ingestion_log ALTER COLUMN id SET DEFAULT nextval('public.intltrade_ingestion_log_id_seq'::regclass);


--
-- Name: nes_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nes_data ALTER COLUMN id SET DEFAULT nextval('public.nes_data_id_seq'::regclass);


--
-- Name: pep_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pep_data ALTER COLUMN id SET DEFAULT nextval('public.pep_data_id_seq'::regclass);


--
-- Name: sahie_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sahie_data ALTER COLUMN id SET DEFAULT nextval('public.sahie_data_id_seq'::regclass);


--
-- Name: saipe_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saipe_data ALTER COLUMN id SET DEFAULT nextval('public.saipe_data_id_seq'::regclass);


--
-- Name: sbo_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sbo_data ALTER COLUMN id SET DEFAULT nextval('public.sbo_data_id_seq'::regclass);


--
-- Name: zbp_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.zbp_data ALTER COLUMN id SET DEFAULT nextval('public.zbp_data_id_seq'::regclass);


--
-- Name: abs_data abs_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.abs_data
    ADD CONSTRAINT abs_data_pkey PRIMARY KEY (id);


--
-- Name: acs1_data acs1_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acs1_data
    ADD CONSTRAINT acs1_data_pkey PRIMARY KEY (id);


--
-- Name: acs_data acs_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acs_data
    ADD CONSTRAINT acs_data_pkey PRIMARY KEY (id);


--
-- Name: bds_data bds_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bds_data
    ADD CONSTRAINT bds_data_pkey PRIMARY KEY (id);


--
-- Name: cbp_data cbp_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cbp_data
    ADD CONSTRAINT cbp_data_pkey PRIMARY KEY (id);


--
-- Name: cps_data cps_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cps_data
    ADD CONSTRAINT cps_data_pkey PRIMARY KEY (id);


--
-- Name: dataset_metadata dataset_metadata_dataset_name_vintage_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_metadata
    ADD CONSTRAINT dataset_metadata_dataset_name_vintage_key UNIQUE (dataset_name, vintage);


--
-- Name: dataset_metadata dataset_metadata_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_metadata
    ADD CONSTRAINT dataset_metadata_pkey PRIMARY KEY (id);


--
-- Name: decennial_data decennial_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.decennial_data
    ADD CONSTRAINT decennial_data_pkey PRIMARY KEY (id);


--
-- Name: ec_data ec_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ec_data
    ADD CONSTRAINT ec_data_pkey PRIMARY KEY (id);


--
-- Name: econ_indicators_data econ_indicators_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.econ_indicators_data
    ADD CONSTRAINT econ_indicators_data_pkey PRIMARY KEY (id);


--
-- Name: geography_ref geography_ref_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geography_ref
    ADD CONSTRAINT geography_ref_pkey PRIMARY KEY (geo_id);


--
-- Name: hhpulse_data hhpulse_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hhpulse_data
    ADD CONSTRAINT hhpulse_data_pkey PRIMARY KEY (id);


--
-- Name: hps_data hps_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hps_data
    ADD CONSTRAINT hps_data_pkey PRIMARY KEY (id);


--
-- Name: intltrade_country_ref intltrade_country_ref_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intltrade_country_ref
    ADD CONSTRAINT intltrade_country_ref_pkey PRIMARY KEY (cty_code);


--
-- Name: intltrade_exports_hs intltrade_exports_hs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intltrade_exports_hs
    ADD CONSTRAINT intltrade_exports_hs_pkey PRIMARY KEY (id);


--
-- Name: intltrade_exports_hs intltrade_exports_hs_time_period_hs_code_cty_code_district__key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intltrade_exports_hs
    ADD CONSTRAINT intltrade_exports_hs_time_period_hs_code_cty_code_district__key UNIQUE (time_period, hs_code, cty_code, district, df, summary_lvl2);


--
-- Name: intltrade_imports_hs intltrade_imports_hs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intltrade_imports_hs
    ADD CONSTRAINT intltrade_imports_hs_pkey PRIMARY KEY (id);


--
-- Name: intltrade_imports_hs intltrade_imports_hs_time_period_hs_code_cty_code_cty_subco_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intltrade_imports_hs
    ADD CONSTRAINT intltrade_imports_hs_time_period_hs_code_cty_code_cty_subco_key UNIQUE (time_period, hs_code, cty_code, cty_subcode, district, rp, summary_lvl2);


--
-- Name: intltrade_ingestion_log intltrade_ingestion_log_dataset_time_period_comm_lvl_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intltrade_ingestion_log
    ADD CONSTRAINT intltrade_ingestion_log_dataset_time_period_comm_lvl_key UNIQUE (dataset, time_period, comm_lvl);


--
-- Name: intltrade_ingestion_log intltrade_ingestion_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.intltrade_ingestion_log
    ADD CONSTRAINT intltrade_ingestion_log_pkey PRIMARY KEY (id);


--
-- Name: nes_data nes_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nes_data
    ADD CONSTRAINT nes_data_pkey PRIMARY KEY (id);


--
-- Name: pep_data pep_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pep_data
    ADD CONSTRAINT pep_data_pkey PRIMARY KEY (id);


--
-- Name: sahie_data sahie_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sahie_data
    ADD CONSTRAINT sahie_data_pkey PRIMARY KEY (id);


--
-- Name: saipe_data saipe_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saipe_data
    ADD CONSTRAINT saipe_data_pkey PRIMARY KEY (id);


--
-- Name: sbo_data sbo_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sbo_data
    ADD CONSTRAINT sbo_data_pkey PRIMARY KEY (id);


--
-- Name: zbp_data zbp_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.zbp_data
    ADD CONSTRAINT zbp_data_pkey PRIMARY KEY (id);


--
-- Name: idx_abs_naics; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_abs_naics ON public.abs_data USING btree (naics_code);


--
-- Name: idx_abs_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_abs_state ON public.abs_data USING btree (state_fips);


--
-- Name: idx_abs_vintage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_abs_vintage ON public.abs_data USING btree (vintage);


--
-- Name: idx_acs1_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_acs1_state ON public.acs1_data USING btree (state_fips);


--
-- Name: idx_acs1_vintage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_acs1_vintage ON public.acs1_data USING btree (vintage);


--
-- Name: idx_acs_geo_level; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_acs_geo_level ON public.acs_data USING btree (geo_level);


--
-- Name: idx_acs_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_acs_state ON public.acs_data USING btree (state_fips);


--
-- Name: idx_acs_state_county; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_acs_state_county ON public.acs_data USING btree (state_fips, county_fips);


--
-- Name: idx_acs_vintage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_acs_vintage ON public.acs_data USING btree (vintage);


--
-- Name: idx_bds_geo_level; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bds_geo_level ON public.bds_data USING btree (geo_level);


--
-- Name: idx_bds_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bds_state ON public.bds_data USING btree (state_fips);


--
-- Name: idx_bds_vintage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bds_vintage ON public.bds_data USING btree (vintage);


--
-- Name: idx_cbp_geo_level; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cbp_geo_level ON public.cbp_data USING btree (geo_level);


--
-- Name: idx_cbp_naics; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cbp_naics ON public.cbp_data USING btree (naics_code);


--
-- Name: idx_cbp_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cbp_state ON public.cbp_data USING btree (state_fips);


--
-- Name: idx_cbp_vintage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cbp_vintage ON public.cbp_data USING btree (vintage);


--
-- Name: idx_cps_month; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cps_month ON public.cps_data USING btree (month);


--
-- Name: idx_cps_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cps_state ON public.cps_data USING btree (state_fips);


--
-- Name: idx_cps_year; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cps_year ON public.cps_data USING btree (year);


--
-- Name: idx_dec_geo_level; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dec_geo_level ON public.decennial_data USING btree (geo_level);


--
-- Name: idx_dec_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dec_state ON public.decennial_data USING btree (state_fips);


--
-- Name: idx_dec_vintage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dec_vintage ON public.decennial_data USING btree (vintage);


--
-- Name: idx_ec_geo_level; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ec_geo_level ON public.ec_data USING btree (geo_level);


--
-- Name: idx_ec_naics; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ec_naics ON public.ec_data USING btree (naics_code);


--
-- Name: idx_ec_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ec_state ON public.ec_data USING btree (state_fips);


--
-- Name: idx_ec_vintage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ec_vintage ON public.ec_data USING btree (vintage);


--
-- Name: idx_econ_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_econ_category ON public.econ_indicators_data USING btree (category_code);


--
-- Name: idx_econ_datatype; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_econ_datatype ON public.econ_indicators_data USING btree (data_type_code);


--
-- Name: idx_econ_indicator_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_econ_indicator_code ON public.econ_indicators_data USING btree (indicator_code);


--
-- Name: idx_econ_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_econ_time ON public.econ_indicators_data USING btree (time_period);


--
-- Name: idx_exp_hs_comm_lvl; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exp_hs_comm_lvl ON public.intltrade_exports_hs USING btree (comm_lvl);


--
-- Name: idx_exp_hs_cty; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exp_hs_cty ON public.intltrade_exports_hs USING btree (cty_code);


--
-- Name: idx_exp_hs_district; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exp_hs_district ON public.intltrade_exports_hs USING btree (district);


--
-- Name: idx_exp_hs_hs_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exp_hs_hs_code ON public.intltrade_exports_hs USING btree (hs_code);


--
-- Name: idx_exp_hs_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exp_hs_time ON public.intltrade_exports_hs USING btree (time_period);


--
-- Name: idx_exp_hs_year; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exp_hs_year ON public.intltrade_exports_hs USING btree (year);


--
-- Name: idx_hhpulse_cycle; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_hhpulse_cycle ON public.hhpulse_data USING btree (cycle);


--
-- Name: idx_hhpulse_measure; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_hhpulse_measure ON public.hhpulse_data USING btree (measure_name);


--
-- Name: idx_hhpulse_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_hhpulse_state ON public.hhpulse_data USING btree (state_fips);


--
-- Name: idx_hhpulse_year; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_hhpulse_year ON public.hhpulse_data USING btree (survey_year);


--
-- Name: idx_hps_indicator; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_hps_indicator ON public.hps_data USING btree (indicator_name);


--
-- Name: idx_hps_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_hps_state ON public.hps_data USING btree (state_fips);


--
-- Name: idx_hps_week; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_hps_week ON public.hps_data USING btree (week);


--
-- Name: idx_hps_year; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_hps_year ON public.hps_data USING btree (survey_year);


--
-- Name: idx_imp_hs_comm_lvl; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_imp_hs_comm_lvl ON public.intltrade_imports_hs USING btree (comm_lvl);


--
-- Name: idx_imp_hs_cty; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_imp_hs_cty ON public.intltrade_imports_hs USING btree (cty_code);


--
-- Name: idx_imp_hs_district; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_imp_hs_district ON public.intltrade_imports_hs USING btree (district);


--
-- Name: idx_imp_hs_hs_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_imp_hs_hs_code ON public.intltrade_imports_hs USING btree (hs_code);


--
-- Name: idx_imp_hs_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_imp_hs_time ON public.intltrade_imports_hs USING btree (time_period);


--
-- Name: idx_imp_hs_year; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_imp_hs_year ON public.intltrade_imports_hs USING btree (year);


--
-- Name: idx_nes_geo_level; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_nes_geo_level ON public.nes_data USING btree (geo_level);


--
-- Name: idx_nes_naics; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_nes_naics ON public.nes_data USING btree (naics_code);


--
-- Name: idx_nes_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_nes_state ON public.nes_data USING btree (state_fips);


--
-- Name: idx_nes_vintage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_nes_vintage ON public.nes_data USING btree (vintage);


--
-- Name: idx_pep_geo_level; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pep_geo_level ON public.pep_data USING btree (geo_level);


--
-- Name: idx_pep_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pep_state ON public.pep_data USING btree (state_fips);


--
-- Name: idx_pep_vintage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pep_vintage ON public.pep_data USING btree (vintage);


--
-- Name: idx_sahie_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sahie_state ON public.sahie_data USING btree (state_fips);


--
-- Name: idx_sahie_vintage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sahie_vintage ON public.sahie_data USING btree (vintage);


--
-- Name: idx_saipe_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_saipe_state ON public.saipe_data USING btree (state_fips);


--
-- Name: idx_saipe_vintage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_saipe_vintage ON public.saipe_data USING btree (vintage);


--
-- Name: idx_sbo_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sbo_state ON public.sbo_data USING btree (state_fips);


--
-- Name: idx_sbo_vintage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sbo_vintage ON public.sbo_data USING btree (vintage);


--
-- Name: idx_zbp_naics; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_zbp_naics ON public.zbp_data USING btree (naics_code);


--
-- Name: idx_zbp_vintage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_zbp_vintage ON public.zbp_data USING btree (vintage);


--
-- Name: idx_zbp_zip_naics; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_zbp_zip_naics ON public.zbp_data USING btree (zipcode, naics_code);


--
-- Name: idx_zbp_zipcode; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_zbp_zipcode ON public.zbp_data USING btree (zipcode);


--
-- PostgreSQL database dump complete
--


