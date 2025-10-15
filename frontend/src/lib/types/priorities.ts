// src/lib/types/priorities.ts

export type Priority = 1 | 2 | 3 | 4 | 5 | null;

export type WeekStatus = 'completed' | 'pending' | 'empty';

export type DayName = 'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday';

export type Priorities = {
	monday: Priority;
	tuesday: Priority;
	wednesday: Priority;
	thursday: Priority;
	friday: Priority;
};

// Core week data structure (Priorities + which week is set)
export type WeekPriority = Priorities & {
	weekNumber: number;
};

// Extended week data used in frontend
export type WeekData = WeekPriority & {
	// Optional fields used by the frontend
	startDate?: string; // Format: "DD.MM.YYYY"
	endDate?: string; // Format: "DD.MM.YYYY"
	id?: string; // Backend-provided ID (if needed)
	status?: WeekStatus; // Calculated status
};

// Backend response structure (matches PriorityResponse)
export type PriorityResponse = {
	month: string; // Format: "YYYY-MM"
	weeks: WeekPriority[];
};

// Request structure for updating priorities (entire month)
export type UpdatePrioritiesRequest = {
	month: string; // Format: "YYYY-MM"
	weeks: WeekPriority[];
};
