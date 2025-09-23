import type { DayPriorities } from '$lib/types/priorities';

export function validateWeekPriorities(priorities: DayPriorities): {
	isValid: boolean;
	message: string;
} {
	const allDaysSet = Object.values(priorities).every((p) => p !== null);
	if (!allDaysSet) {
		return {
			isValid: false,
			message: 'Bitte vergeben Sie für jeden Tag eine Priorität'
		};
	}

	const usedPriorities = Object.values(priorities).filter((p) => p !== null);
	const uniquePriorities = new Set(usedPriorities);
	if (uniquePriorities.size !== 5) {
		return {
			isValid: false,
			message: 'Jede Priorität (1-5) muss genau einmal vergeben werden'
		};
	}

	return {
		isValid: true,
		message: ''
	};
}
