use tasks;
select * from sales_data_sample;
alter table sales_data_sample rename to sales;
alter table sales add column sales_generated double;
update sales set sales_generated = sales;
-- total revenue generated
select sum(sales_generated) as total_revenue from sales;
-- total sales generated in each month in all 3 years
select sum(sales_generated) as total_sales,month_id from sales group by month_id order by month_id;
-- all unique orders in each month in each year
SELECT YEAR_ID, MONTH_ID, COUNT(DISTINCT ORDERNUMBER) AS monthly_order_volume
	FROM sales GROUP BY YEAR_ID, MONTH_ID ORDER BY YEAR_ID, MONTH_ID;
-- top 5 months with highest sales
SELECT YEAR_ID, MONTH_ID, SUM(SALES) AS total_sales
FROM sales GROUP BY YEAR_ID, MONTH_ID ORDER BY total_sales DESC
LIMIT 5;
-- country wise  sales summary in 3 years
SELECT distinct(COUNTRY),  SUM(SALES) AS revenue
FROM sales GROUP BY COUNTRY
ORDER BY COUNTRY;
-- average quantity ordered per month
SELECT YEAR_ID, MONTH_ID, AVG(QUANTITYORDERED) AS avg_qty_per_order
FROM sales GROUP BY YEAR_ID, MONTH_ID
ORDER BY YEAR_ID, MONTH_ID;

