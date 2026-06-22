-- EQUIPMENT

CREATE TABLE EQUIPMENT (
	Equipment_ID INT IDENTITY(1, 1) PRIMARY KEY,
	Equipment_Tag VARCHAR(20) NOT NULL UNIQUE,	-- original PK kept as business key
	Activity_ID INT NULL,
	Description VARCHAR(150),
	Location VARCHAR(100),
	Manufacturer VARCHAR(100),
	Model_Number VARCHAR(80),
	Install_Date DATE,
	Status VARCHAR(30) NOT NULL DEFAULT 'Active'
		CONSTRAINT chk_equipment_status
		CHECK (Status IN ('Active', 'Inactive', 'Under Maintenance', 'Decommissioned')),
	CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
	UpdatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

	CONSTRAINT fk_equipment_activity
		FOREIGN KEY (Activity_ID) REFERENCES WBS_ACTIVITIES (Activity_ID)
);

CREATE INDEX ix_equipment_activity ON EQUIPMENT (Activity_ID);