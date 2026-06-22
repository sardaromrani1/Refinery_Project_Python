-- PROJECTS

CREATE TABLE PROJECTS (
	Project_ID INT IDENTITY(1, 1) PRIMARY KEY,
	Project_Code VARCHAR(20) NOT NULL UNIQUE,
	Project_Name VARCHAR(150) NOT NULL,
	Start_Date DATE,
	End_Date DATE,
	Status VARCHAR(30) NOT NULL DEFAULT 'Planned'
		CONSTRAINT chk_projects_status
		CHECK (Status IN ( 'Planned', 'Active', 'OnHOld', 'Completed', 'Cancelled' )),
	
	CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
	UpdatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

	CONSTRAINT chk_prrojects_dates CHECK (End_Date IS NULL OR End_Date >= Start_Date )
);