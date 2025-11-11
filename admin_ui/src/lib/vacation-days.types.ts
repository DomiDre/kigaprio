/**
 * Type definitions for vacation days API (Admin UI)
 */

export type VacationDayType = 'vacation' | 'admin_leave' | 'public_holiday';

export interface VacationDayAdmin {
	id: string;
	date: string; // YYYY-MM-DD HH:mm:ss.SSSZ format from backend
	type: VacationDayType;
	description: string;
	created_by: string;
	created: string;
	updated: string;
}

export interface VacationDayCreate {
	date: string; // YYYY-MM-DD format
	type: VacationDayType;
	description?: string;
}

export interface VacationDayUpdate {
	type?: VacationDayType;
	description?: string;
}

export interface BulkVacationDayCreate {
	days: VacationDayCreate[];
}

export interface BulkVacationDayResponse {
	created: number;
	skipped: number;
	errors: Array<{ date: string; error: string }>;
}
