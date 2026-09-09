-- Hyundai PoS Analyst warehouse schema
-- Load generated CSVs from output/warehouse after running:
--   python scripts/build_dataset.py

CREATE DATABASE IF NOT EXISTS car CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE car;

DROP VIEW IF EXISTS vw_hyundai_sales_monthly;
DROP VIEW IF EXISTS vw_market_registration_monthly;
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS fact_registration;
DROP TABLE IF EXISTS dim_model;
DROP TABLE IF EXISTS dim_fuel;
DROP TABLE IF EXISTS dim_powertrain;
DROP TABLE IF EXISTS dim_vehicle_type;
DROP TABLE IF EXISTS dim_region;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_date (
    date_id INT PRIMARY KEY,
    `year` SMALLINT NOT NULL,
    `month` TINYINT NOT NULL,
    `year_month` CHAR(6) NOT NULL,
    UNIQUE KEY uq_dim_date_year_month (`year_month`)
) ENGINE=InnoDB;

CREATE TABLE dim_region (
    region_id INT PRIMARY KEY,
    region_name VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE dim_vehicle_type (
    vehicle_type_id INT PRIMARY KEY,
    vehicle_type_name VARCHAR(30) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE dim_powertrain (
    powertrain_id INT PRIMARY KEY,
    powertrain_name VARCHAR(30) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE dim_fuel (
    fuel_id INT PRIMARY KEY,
    fuel_name VARCHAR(50) NOT NULL UNIQUE,
    powertrain_name VARCHAR(30) NOT NULL,
    CONSTRAINT fk_fuel_powertrain FOREIGN KEY (powertrain_name) REFERENCES dim_powertrain (powertrain_name)
) ENGINE=InnoDB;

CREATE TABLE dim_model (
    model_id INT PRIMARY KEY,
    model_name VARCHAR(150) NOT NULL UNIQUE,
    model_family VARCHAR(100) NOT NULL,
    category VARCHAR(10) NOT NULL,
    powertrain VARCHAR(30) NOT NULL,
    CONSTRAINT fk_model_powertrain FOREIGN KEY (powertrain) REFERENCES dim_powertrain (powertrain_name)
) ENGINE=InnoDB;

CREATE TABLE fact_registration (
    registration_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    date_id INT NOT NULL,
    region_id INT NOT NULL,
    fuel_id INT NOT NULL,
    vehicle_type_id INT NOT NULL,
    usage_name VARCHAR(30) NOT NULL,
    registered_qty BIGINT NOT NULL,
    CONSTRAINT fk_registration_date FOREIGN KEY (date_id) REFERENCES dim_date (date_id),
    CONSTRAINT fk_registration_region FOREIGN KEY (region_id) REFERENCES dim_region (region_id),
    CONSTRAINT fk_registration_fuel FOREIGN KEY (fuel_id) REFERENCES dim_fuel (fuel_id),
    CONSTRAINT fk_registration_vehicle_type FOREIGN KEY (vehicle_type_id) REFERENCES dim_vehicle_type (vehicle_type_id),
    UNIQUE KEY uq_registration_grain (date_id, region_id, fuel_id, vehicle_type_id, usage_name),
    INDEX ix_registration_date_region (date_id, region_id)
) ENGINE=InnoDB;

CREATE TABLE fact_sales (
    sales_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    date_id INT NOT NULL,
    model_id INT NOT NULL,
    market VARCHAR(20) NOT NULL,
    category VARCHAR(10) NOT NULL,
    sales_month TINYINT NOT NULL,
    sales_qty BIGINT NOT NULL,
    CONSTRAINT fk_sales_date FOREIGN KEY (date_id) REFERENCES dim_date (date_id),
    CONSTRAINT fk_sales_model FOREIGN KEY (model_id) REFERENCES dim_model (model_id),
    UNIQUE KEY uq_sales_grain (date_id, model_id, market, category, sales_month),
    INDEX ix_sales_date_market (date_id, market)
) ENGINE=InnoDB;

CREATE VIEW vw_market_registration_monthly AS
SELECT d.`year`, d.`month`, r.region_name, f.fuel_name, f.powertrain_name,
       v.vehicle_type_name, SUM(fr.registered_qty) AS registered_qty
FROM fact_registration fr
JOIN dim_date d ON d.date_id = fr.date_id
JOIN dim_region r ON r.region_id = fr.region_id
JOIN dim_fuel f ON f.fuel_id = fr.fuel_id
JOIN dim_vehicle_type v ON v.vehicle_type_id = fr.vehicle_type_id
GROUP BY d.`year`, d.`month`, r.region_name, f.fuel_name, f.powertrain_name, v.vehicle_type_name;

CREATE VIEW vw_hyundai_sales_monthly AS
SELECT d.`year`, fs.sales_month, fs.market, fs.category,
       m.model_family, m.powertrain, SUM(fs.sales_qty) AS sales_qty
FROM fact_sales fs
JOIN dim_date d ON d.date_id = fs.date_id
JOIN dim_model m ON m.model_id = fs.model_id
GROUP BY d.`year`, fs.sales_month, fs.market, fs.category, m.model_family, m.powertrain;
