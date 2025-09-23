import type { DayPriorities } from '$lib/types/priorities.ts';

// Priority configuration with proper typing
export const priorityColors: Record<1 | 2 | 3 | 4 | 5, string> = {
	5: 'bg-red-500',
	4: 'bg-orange-500',
	3: 'bg-yellow-500',
	2: 'bg-blue-500',
	1: 'bg-gray-400'
} as const;

export const priorityLabels: Record<1 | 2 | 3 | 4 | 5, string> = {
	5: 'Sehr wichtig',
	4: 'Wichtig',
	3: 'Normal',
	2: 'Weniger wichtig',
	1: 'Unwichtig'
} as const;

export const dayNames: Record<keyof DayPriorities, string> = {
	monday: 'Montag',
	tuesday: 'Dienstag',
	wednesday: 'Mittwoch',
	thursday: 'Donnerstag',
	friday: 'Freitag'
} as const;

export const monthNames = [
	'Januar',
	'Februar',
	'März',
	'April',
	'Mai',
	'Juni',
	'Juli',
	'August',
	'September',
	'Oktober',
	'November',
	'Dezember'
] as const;
