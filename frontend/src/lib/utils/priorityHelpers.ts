import type { Priorities } from '$lib/types/priorities';

export function validateWeekPriorities(priorities: Priorities): {
	isValid: boolean;
	isComplete: boolean;
	message: string;
} {
	// Get all assigned priorities (non-null values)
	const assignedPriorities = Object.values(priorities).filter((p) => p !== null);

	// Check if there are any assigned priorities
	if (assignedPriorities.length === 0) {
		return {
			isValid: false,
			isComplete: false,
			message: 'Bitte vergeben Sie mindestens eine Priorität'
		};
	}

	// Check for duplicates
	const uniquePriorities = new Set(assignedPriorities);
	if (uniquePriorities.size !== assignedPriorities.length) {
		return {
			isValid: false,
			isComplete: false,
			message: 'Jede Priorität kann nur einmal vergeben werden'
		};
	}

	// Check if all priorities are within valid range (1-5)
	const invalidPriorities = assignedPriorities.filter((p) => p < 1 || p > 5);
	if (invalidPriorities.length > 0) {
		return {
			isValid: false,
			isComplete: false,
			message: 'Prioritäten müssen zwischen 1 und 5 liegen'
		};
	}

	// Check if the week is complete (all 5 days have priorities)
	const isComplete = assignedPriorities.length === 5;

	// Validation passes if:
	// - No duplicates exist
	// - All assigned priorities are valid (1-5)
	// - At least one priority is assigned
	return {
		isValid: true,
		isComplete: isComplete,
		message: isComplete
			? 'Alle Prioritäten vollständig vergeben'
			: `${assignedPriorities.length} von 5 Prioritäten vergeben`
	};
}

// Optional: Strict validation for final submission (if needed)
export function validateWeekPrioritiesStrict(priorities: Priorities): {
	isValid: boolean;
	message: string;
} {
	const result = validateWeekPriorities(priorities);

	if (!result.isValid) {
		return {
			isValid: false,
			message: result.message
		};
	}

	if (!result.isComplete) {
		return {
			isValid: false,
			message: 'Bitte vergeben Sie für jeden Tag eine Priorität (1-5)'
		};
	}

	return {
		isValid: true,
		message: ''
	};
}
