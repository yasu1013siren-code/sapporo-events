import { sqliteTable, text, integer } from 'drizzle-orm/sqlite-core';
export const trials = sqliteTable('trials', {
 id: text('id').primaryKey(), keyHash: text('key_hash').notNull(),
 store: text('store').notNull(), business: text('business').notNull(),
 area: text('area').notNull(), email: text('email').notNull(),
 createdAt: text('created_at').notNull(), startDate: text('start_date').notNull(),
 endDate: text('end_date').notNull(), consentVersion: text('consent_version').notNull(),
});
export const answers = sqliteTable('answers', {
 trialId: text('trial_id').primaryKey().references(()=>trials.id, {onDelete:'cascade'}),
 uses: integer('uses').notNull(), minutes: integer('minutes').notNull(),
 useful: text('useful').notNull(), willingness: text('willingness').notNull(),
 feedback: text('feedback').notNull(), priceYen: integer('price_yen').notNull(),
 answeredAt: text('answered_at').notNull(),
});
