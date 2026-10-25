import { sqliteTable, text, integer } from 'drizzle-orm/sqlite-core';
export const heads = sqliteTable('research_heads', {
  workspace: text('workspace').primaryKey(),
  version: integer('version').notNull(),
  stateKey: text('state_key').notNull(),
  sha256: text('sha256').notNull(),
  manifest: text('manifest').notNull(),
  updatedAt: text('updated_at').notNull(),
});
export const revisions = sqliteTable('research_revisions', {
  id: text('id').primaryKey(),
  workspace: text('workspace').notNull(),
  version: integer('version').notNull(),
  previousVersion: integer('previous_version').notNull(),
  stateKey: text('state_key').notNull(),
  sha256: text('sha256').notNull(),
  manifest: text('manifest').notNull(),
  createdAt: text('created_at').notNull(),
});
