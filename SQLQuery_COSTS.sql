-- 9. COSTS

CREATE TABLE COSTS (
	Cost_ID VARCHAR(20) PRIMARY KEY,
	Activity_ID VARCHAR(20),
	Cost_Type VARCHAR(50),
	Budgeted_Amount DECIMAL(15, 2),
	Actual_Amount DECIMAL(15, 2),
	Date_Recorded DATE,
	
	CONSTRAINT fk_costs_activity FOREIGN KEY (Activity_ID) REFERENCES WBS_ACTIVITIES (Activity_ID)
);