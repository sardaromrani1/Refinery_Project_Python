-- 10. PERMITS

CREATE TABLE PERMITS (
	Permit_ID VARCHAR(20) PRIMARY KEY,
	Activity_ID VARCHAR(20),
	Permit_Type VARCHAR(50),
	Issue_Date DATE,
	Expiray_Date DATE,
	Status VARCHAR(30),

	CONSTRAINT fk_permits_activity FOREIGN KEY (Activity_ID) REFERENCES WBS_ACTIVITIES (Activity_ID)
);