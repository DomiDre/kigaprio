import { SvelteDate } from 'svelte/reactivity';
import type { WeekData } from '$lib/types/priorities';
import { monthNames } from '$lib/config/priorities';

export function getWeeksForMonth(year: number, month: number): WeekData[] {
	const weeks: WeekData[] = [];
	const firstDay = new SvelteDate(year, month, 1);

	const currentDate = new SvelteDate(firstDay);
	const dayOfWeek = currentDate.getDay();
	const daysToSubtract = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
	currentDate.setDate(currentDate.getDate() - daysToSubtract);

	let weekNumber = 1;

	while (true) {
		const startDate = new SvelteDate(currentDate);
		const endDate = new SvelteDate(currentDate);
		endDate.setDate(endDate.getDate() + 4);

		const weekDays: Date[] = [];
		for (let i = 0; i < 5; i++) {
			const day = new SvelteDate(startDate);
			day.setDate(day.getDate() + i);
			weekDays.push(day);
		}

		const hasRelevantDay = weekDays.some(
			(day) => day.getMonth() === month && day.getFullYear() === year
		);

		if (!hasRelevantDay && weekNumber > 1) break;

		if (hasRelevantDay) {
			const formatDate = (date: Date) => {
				const day = date.getDate().toString().padStart(2, '0');
				const monthStr = (date.getMonth() + 1).toString().padStart(2, '0');
				const year = date.getFullYear();
				return `${day}.${monthStr}.${year}`;
			};

			weeks.push({
				weekNumber,
				startDate: formatDate(startDate),
				endDate: formatDate(endDate),
				priorities: {
					monday: null,
					tuesday: null,
					wednesday: null,
					thursday: null,
					friday: null
				},
				status: 'pending'
			});

			weekNumber++;
		}

		currentDate.setDate(currentDate.getDate() + 7);
		if (weekNumber > 6) break;
	}

	return weeks;
}

export function getMonthOptions(): string[] {
	const now = new Date();
	const currentMonth = now.getMonth();
	const currentYear = now.getFullYear();
	const options: string[] = [];

	options.push(`${monthNames[currentMonth]} ${currentYear}`);

	const nextMonth = new Date(currentYear, currentMonth + 1);
	options.push(`${monthNames[nextMonth.getMonth()]} ${nextMonth.getFullYear()}`);

	return options;
}

export function parseMonthString(monthStr: string): { year: number; month: number } {
	const months: Record<string, number> = {
		Januar: 0,
		Februar: 1,
		März: 2,
		April: 3,
		Mai: 4,
		Juni: 5,
		Juli: 6,
		August: 7,
		September: 8,
		Oktober: 9,
		November: 10,
		Dezember: 11
	};

	const [monthName, yearStr] = monthStr.split(' ');
	return {
		year: parseInt(yearStr),
		month: months[monthName]
	};
}

/**
 * Converts display format "Oktober 2025" to API format "2025-10"
 */
export function formatMonthForAPI(displayMonth: string): string {
	const { year, month } = parseMonthString(displayMonth);
	// month is 0-indexed (0 = January), so we add 1 for the API format
	const monthStr = (month + 1).toString().padStart(2, '0');
	return `${year}-${monthStr}`;
}

/**
 * Converts API format "2025-10" to display format "Oktober 2025"
 */
export function formatMonthForDisplay(apiMonth: string): string {
	const [year, monthStr] = apiMonth.split('-');
	const monthIndex = parseInt(monthStr) - 1; // Convert to 0-indexed
	return `${monthNames[monthIndex]} ${year}`;
}

export function getDayDates(weekData: WeekData): string[] {
	const [day, month, year] = weekData.startDate.split('.');
	const startDate = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));

	return Array.from({ length: 5 }, (_, i) => {
		const currentDate = new SvelteDate(startDate);
		currentDate.setDate(currentDate.getDate() + i);
		return `${currentDate.getDate()}.`;
	});
}

export function isWeekComplete(week: WeekData): boolean {
	const totalDaysInWeek = Object.keys(week.priorities).length;
	const validPriorities = Object.values(week.priorities).filter(
		(p) => p !== null && p !== undefined
	);

	return (
		totalDaysInWeek > 0 &&
		validPriorities.length === totalDaysInWeek &&
		new Set(validPriorities).size === totalDaysInWeek
	);
}

export function getWeekStatus(week: WeekData): 'completed' | 'pending' | 'empty' {
	const validCount = Object.values(week.priorities).filter(
		(p) => p !== null && p !== undefined
	).length;

	if (isWeekComplete(week)) {
		return 'completed';
	} else if (validCount > 0) {
		return 'pending';
	} else {
		return 'empty';
	}
}
