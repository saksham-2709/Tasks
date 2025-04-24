use tasks;
select * from job_postings_fact;
ALTER TABLE job_postings_fact
MODIFY job_title VARCHAR(255);

CREATE INDEX idx_title ON job_postings_fact(job_title);

select job_title_short,salary_year_avg,job_location from job_postings_fact where salary_rate = "year" order by salary_year_avg + 0 desc ;
select * from  company_dim;
select job_id,job_country,job_title_short,job_location,salary_rate,d.name,d.link  from job_postings_fact j left join company_dim d on j.company_id = d.company_id limit 20;
select job_id,job_title_short,job_location,salary_rate,d.name from job_postings_fact j inner join company_dim d on j.company_id = d.company_id limit 20;
select job_title,job_id,company_id,job_location from job_postings_fact where job_country in ( select job_country from job_postings_fact where job_schedule_type = 'Full-Time') limit 40;

select max(salary_year_avg),max(salary_hour_avg),avg(salary_hour_avg),avg(salary_year_avg) from job_postings_fact;
CREATE VIEW yearly_jobs AS
SELECT job_title_short, salary_year_avg
FROM job_postings_fact
WHERE salary_rate = 'year';

