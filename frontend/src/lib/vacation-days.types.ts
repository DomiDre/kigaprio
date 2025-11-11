/**
 * Type definitions for vacation days API
 */

export type VacationDayType = 'vacation' | 'admin_leave' | 'public_holiday';

export interface VacationDay {
	date: string; // YYYY-MM-DD HH:mm:ss.SSSZ format from backend
	type: VacationDayType;
	description: string;
}
