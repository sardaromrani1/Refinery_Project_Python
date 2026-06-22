--===============================================================================================================
-- OPTIONAL: UpdatedAt trigger example ( apply to each table )
--===============================================================================================================

CREATE OR ALTER TRIGGER trg_projects_updated
ON PROJECTS
AFTER UPDATE AS
BEGIN
	SET NOCOUNT ON;
	UPDATE PROJECTS
	SET UpdatedAt = SYSDATETIME()
	FROM PROJECTS p
	INNER JOIN inserted i ON p.Project_ID = i.Project_ID
END;

-- Repeat same trigger pattern for each table