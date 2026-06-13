-- 5. EQUIPMENT

CREATE TABLE EQUIPMENT(
	Equipment_Tag VARCHAR(20) PRIMARY KEY,
	Activity_ID VARCHAR(20),
	Description VARCHAR(150),
	Location VARCHAR(100),
	Manufacurer VARCHAR(100),
	Install_Date DATE,
	Status VARCHAR(30),

	CONSTRAINT fk_equipment_activity FOREIGN KEY (Activity_ID) REFERENCES WBS_ACTIVITIES (Activity_ID)
);