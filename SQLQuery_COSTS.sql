-- COSTS

CREATE TABLE COSTS ( 
	Cost_ID INT IDENTITY (1,1) PRIMARY KEY,
	Cost_Code VARCHAR(20) NOT NULL UNIQUE,
	Activity_ID INT NOT NULL,
	Cost_Type VARCHAR(50) NOT NULL
		CONSTRAINT chk_costs_type
		CHECK (Cost_Type IN ('Labour', 'Materials', 'Equipment', 'Contractor', 'Overhead', 'Other')),
	Budgeted_Amount DECIMAL(15, 2) NULL
		CONSTRAINT chk_costs_budget
		CHECK (Budgeted_Amount >= 0),
	Actual_Amount DECIMAL(15, 2) NULL
		CONSTRAINT chk_costs_actual 
		CHECK (Actual_Amount >= 0),
	Currency CHAR(3) NOT NULL DEFAULT 'USD',	-- ISO 4217
	Date_Recorded DATE NOT NULL DEFAULT CAST (SYSDATETIME() AS DATE),
	CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
	UpdatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

	CONSTRAINT fk_costs_activity
		FOREIGN KEY (Activity_ID) REFERENCES WBS_ACTIVITIES (Activity_ID)
);

CREATE INDEX ix_costs_activity ON COSTS (Activity_ID);