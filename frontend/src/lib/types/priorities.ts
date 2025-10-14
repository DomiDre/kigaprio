export type Priority = 1 | 2 | 3 | 4 | 5 | null;

export type WeekData = {
	weekNumber: number;
	monday: Priority;
	tuesday: Priority;
	wednesday: Priority;
	thursday: Priority;
	friday: Priority;
};
