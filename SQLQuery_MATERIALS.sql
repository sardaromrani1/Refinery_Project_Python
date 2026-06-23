-- 6. MATERIALS

CREATE TABLE MATERIALS(
	Material_ID VARCHAR(20) PRIMARY KEY,
	Activity_ID VARCHAR(20),
	Vendor_ID VARCHAR(20),
	Description VARCHAR(150),
	Quantity INT,
	PO_Number VARCHAR(50),
	Order_Date DATE,
	Expected_Delivery DATE,
	Actual_Delivery DATE,
	Status VARCHAR(30),

	CONSTRAINT fk_materials_activity FOREIGN KEY (Activity_ID) REFERENCES WBS_ACTIVITIES (Activity_ID),
	CONSTRAINT fk_materials_vendor FOREIGN KEY (Vendor_ID) REFERENCES VENDORS (Vendor_ID)
);