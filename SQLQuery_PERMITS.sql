-- PERMITS

CREATE TABLE PERMITS (
	Permit_ID INT IDENTITY(1, 1) PRIMARY KEY,
	Permit_Code VARCHAR(20) NOT NULL UNIQUE,
	Project_ID INT NOT NULL,
	Activity_ID INT NULL,
	Permit_Type VARCHAR(80) NOT NULL,
	Issued_By VARCHAR(100),
	Issued_Date DATE,
	Expiry_Date DATE,
	Status VARCHAR(30) NOT NULL DEFAULT 'Pending'
		CONSTRAINT chk_permits_status
		CHECK (Status IN ('Pending', 'Approved', 'Rejected', 'Expired', 'Revoked')),
	CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
	UpdatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

	CONSTRAINT fk_permits_project
		FOREIGN KEY (Project_ID) REFERENCES PROJECTS (Project_ID),
	CONSTRAINT chk_permits_dates
		CHECK (Expiry_Date IS NULL OR Expiry_Date >= Issued_Date)
);

CREATE INDEX ix_permits_project ON PERMITS (Project_ID);

CREATE INDEX ix_permits_activity ON PERMITS (Activity_ID);
