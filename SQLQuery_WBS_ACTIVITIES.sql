-- WBS_ACTIVITIES

CREATE TABLE WBS_ACTIVITIES (
	Activity_ID INT IDENTITY(1, 1) PRIMARY KEY,
	Activity_Code VARCHAR(20) NOT NULL UNIQUE,
	Project_ID INT NOT NULL,
	Activity_Name VARCHAR(150) NOT NULL,
	Planned_Start DATE,
	Planned_Finish DATE,
	Actual_Start DATE,
	Actual_Finish DATE,
	Percent_Complete DECIMAL(5,2) NOT NULL DEFAULT 0 
		CONSTRAINT chk_wbs_pct CHECK (Percent_Complete BETWEEN 0 AND 100),
	Predecessor_ID INT NULL,	-- self-referencing FK
	CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
	UpdatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

	CONSTRAINT fk_wbs_project
		FOREIGN KEY (Project_ID) REFERENCES PROJECTS (Project_ID),
	CONSTRAINT fk_wbs_predecessor 
		FOREIGN KEY (Predecessor_ID) REFERENCES WBS_ACTIVITIES (Activity_ID),
	CONSTRAINT chk_wbs_planned_dates
		CHECK (Planned_Finish IS NULL OR Planned_Finish >= Planned_Start),
	CONSTRAINT chk_wbs_actual_dates
		CHECK (Actual_Finish IS NULL OR Actual_Finish >= Actual_Start )
);

CREATE INDEX ix_wbs_project ON WBS_ACTIVITIES (Project_ID);

CREATE INDEX ix_wbs_predecessor ON WBS_ACTIVITIES (Predecessor_ID);
		