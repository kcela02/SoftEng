-- data/schema.sql
-- Product Master Table
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    unit_cost DECIMAL(10, 2),
    current_stock INT NOT NULL DEFAULT 0
);

-- Historical Sales Data Table
CREATE TABLE sales (
    sale_id SERIAL PRIMARY KEY,
    product_id INT REFERENCES products(product_id),
    sale_date DATE NOT NULL,
    sales_quantity INT NOT NULL,
    sale_price DECIMAL(10, 2),
    UNIQUE (product_id, sale_date) -- Enforce one entry per product per day
);

-- Forecasting Results Table (To store model performance and latest predictions)
CREATE TABLE forecasts (
    forecast_id SERIAL PRIMARY KEY,
    product_id INT REFERENCES products(product_id),
    forecast_date DATE NOT NULL,
    predicted_quantity INT,
    model_used VARCHAR(50),
    accuracy DECIMAL(5, 4) -- Store the model's accuracy (e.g., MAPE or R2)
);