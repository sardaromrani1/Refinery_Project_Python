-- RESOURCES

CREATE TABLE RESOURCES (
	Resource_ID INT IDENTITY(1, 1) PRIMARY KEY,
	Resource_Code VARCHAR(20) NOT NULL UNIQUE,
	Activity_ID INT NOT NULL,
	Contractor_ID INT NULL,
	Full_Name VARCHAR(100) NOT NULL,
	Role VARCHAR(100) NOT NULL,
	Certification VARCHAR(100),
	Assigned_From DATE NOT NULL,
	Assigned_To DATE NULL,
	CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
	UpdatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

	CONSTRAINT fk_resources_activity
		FOREIGN KEY (Activity_ID) REFERENCES WBS_ACTIVITIES (Activity_ID),
	CONSTRAINT fk_resources_contractor
		FOREIGN KEY (Contractor_ID) REFERENCES CONTRACTORS (Contractor_ID),
	CONSTRAINT chk_resources_dates
		CHECK (Assigned_To IS NULL OR Assigned_To >= Assigned_From)
);

CREATE INDEX ix_resources_activity ON RESOURCES (Activity_ID);

CREATE INDEX ix_resources_contractor ON RESOURCES (Contractor_ID);