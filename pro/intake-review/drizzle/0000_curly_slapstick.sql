CREATE TABLE `answers` (
	`trial_id` text PRIMARY KEY NOT NULL,
	`uses` integer NOT NULL,
	`minutes` integer NOT NULL,
	`useful` text NOT NULL,
	`willingness` text NOT NULL,
	`feedback` text NOT NULL,
	`price_yen` integer NOT NULL,
	`answered_at` text NOT NULL,
	FOREIGN KEY (`trial_id`) REFERENCES `trials`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE TABLE `trials` (
	`id` text PRIMARY KEY NOT NULL,
	`key_hash` text NOT NULL,
	`store` text NOT NULL,
	`business` text NOT NULL,
	`area` text NOT NULL,
	`email` text NOT NULL,
	`created_at` text NOT NULL,
	`start_date` text NOT NULL,
	`end_date` text NOT NULL,
	`consent_version` text NOT NULL
);
