export type User = {
	id: string;
	email: string;
	role: 'user' | 'admin';
	[key: string]: unknown;
};
