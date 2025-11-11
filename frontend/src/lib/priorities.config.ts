import type { DayName } from '$lib/priorities.types';

// Priority configuration with proper typing
export const priorityColors: Record<1 | 2 | 3 | 4 | 5, string> = {
	1: 'bg-red-500',
	2: 'bg-orange-500',
	3: 'bg-yellow-500',
	4: 'bg-blue-500',
	5: 'bg-gray-400'
} as const;

export const priorityLabels: Record<1 | 2 | 3 | 4 | 5, string> = {
	1: 'Sehr wichtig',
	2: 'Wichtig',
	3: 'Normal',
	4: 'Weniger wichtig',
	5: 'Unwichtig'
} as const;

export const dayKeys: DayName[] = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'];

export const dayNames: Record<DayName, string> = {
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
