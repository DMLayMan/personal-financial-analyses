CREATE TABLE `research_heads` (
	`workspace` text PRIMARY KEY NOT NULL,
	`version` integer NOT NULL,
	`state_key` text NOT NULL,
	`sha256` text NOT NULL,
	`manifest` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `research_revisions` (
	`id` text PRIMARY KEY NOT NULL,
	`workspace` text NOT NULL,
	`version` integer NOT NULL,
	`previous_version` integer NOT NULL,
	`state_key` text NOT NULL,
	`sha256` text NOT NULL,
	`manifest` text NOT NULL,
	`created_at` text NOT NULL
);
