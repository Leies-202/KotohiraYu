CREATE TABLE IF NOT EXISTS `fav_rate` (
	`ID`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`ID_Inst`	INTEGER NOT NULL UNIQUE,
	`rate`	TEXT NOT NULL DEFAULT 100
);
