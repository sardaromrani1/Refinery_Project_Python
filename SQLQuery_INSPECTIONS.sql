-- INSPECTIONS

CREATE TABLE INSPECTIONS (
	Inspection_ID INT IDENTITY(1, 1) PRIMARY KEY,
	Inspection_Code VARCHAR(20) NOT NULL UNIQUE,
	Equipment_ID INT NOT NULL,
	Inspection_Date DATE NOT NULL,
	Next_Inspection_Date DATE NULL,
	Inspection_Type VARCHAR(50) NOT NULL,
	Result VARCHAR(50) NOT NULL
		CONSTRAINT chk_inspections_result
		CHECK (Result IN ('Pass', 'Fail', 'Conditional Pass', 'Pending')),
	Inspector VARCHAR(100) NOT NULL,
	Remarks VARCHAR(500) NULL,
	CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
	UpdatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

	CONSTRAINT fk_inspections_equipment 
		FOREIGN KEY (Equipment_ID) REFERENCES EQUIPMENT (Equipment_ID),
	CONSTRAINT chk_inspections_next_date 
		CHECK (Next_Inspection_Date IS NULL OR Next_Inspection_Date > Inspection_Date)
);

CREATE INDEX ix_inspections_equipment ON INSPECTIONS (Equipment_ID);

CREATE INDEX ix_inspections_date ON INSPECTIONS (Inspection_Date);