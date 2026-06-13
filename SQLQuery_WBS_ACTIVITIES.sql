-- 4. WBS_ACTIVITIES ( Central table linking to the project schedule )

CREATE TABLE WBS_ACTIVITIES(
	Activity_ID VARCHAR(20) PRIMARY KEY,
	Project_ID VARCHAR(20) NOT NULL,
	Activity_Name VARCHAR(150) NOT NULL,
	Planned_Start DATE,
	Planned_Finish DATE,
	Actual_Start DATE,
	Actual_Finish DATE,
	Percent_Complete DECIMAL(5, 2) DEFAULT 0,
	Predecessor_ID VARCHAR(20),
	CONSTRAINT fk_wbs_project
	FOREIGN KEY(Project_ID)
	REFERENCES dbo.PROJECTT(Project_ID),
	CONSTRAINT fk_wbs_predecessor FOREIGN KEY (Predecessor_ID)REFERENCES WBS_ACTIVITIES (Activity_ID)

);