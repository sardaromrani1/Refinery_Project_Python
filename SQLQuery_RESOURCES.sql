-- RESOURCES

CREATE TABLE RESOURCES (
	Resource_ID VARCHAR(20) PRIMARY KEY,
	Activity_ID VARCHAR(20),
	Contractor_ID VARCHAR(20),
	Name VARCHAR(100),
	Role VARCHAR(100),
	Certification VARCHAR(100),
	Assigned_From DATE,
	Assigned_To DATE,
	
	CONSTRAINT fk_resources_activity FOREIGN KEY (Activity_ID) REFERENCES WBS_ACTIVITIES (Activity_ID),
	CONSTRAINT fk_resources_contractor FOREIGN KEY (Contractor_ID) REFERENCES CONTRACTORS (Contractor_ID)
);