export type Priority = 1 | 2 | 3 | 4 | 5 | null;

export type DayPriorities = {
	monday: Priority;
	tuesday: Priority;
	wednesday: Priority;
	thursday: Priority;
	friday: Priority;
};

export type WeekData = {
	weekNumber: number;
	startDate: string;
	endDate: string;
	priorities: DayPriorities;
	status: 'completed' | 'pending';
	userId?: string;
	id?: string;
};
