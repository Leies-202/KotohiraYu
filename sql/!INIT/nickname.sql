CREATE TABLE IF NOT EXISTS `nickname` (
	`ID`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	`ID_Inst`	INTEGER NOT NULL UNIQUE,
	`nickname`	TEXT NOT NULL
);
