-- 11. INSPECTIONS

CREATE TABLE INSPECTIONS (
	Inspection_ID VARCHAR(20) PRIMARY KEY,
	Equipment_Tag VARCHAR(20),
	Inspection_Date DATE,
	Inspection_Type VARCHAR(50),
	Result VARCHAR(50),
	Inspector VARCHAR(100),

	CONSTRAINT fk_inspections_equipment FOREIGN KEY (Equipment_Tag) REFERENCES EQUIPMENT (Equipment_Tag)
);