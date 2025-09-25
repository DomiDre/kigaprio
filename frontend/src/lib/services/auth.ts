import { pb } from '$lib/services/pocketbase';
import type { User } from '$lib/types/pocketbase';

export async function loginUser(email: string, password: string): Promise<User | null> {
	await pb.collection('users').authWithPassword(email, password);
	return pb.authStore.record as User | null;
}

export async function loginAdmin(email: string, password: string): Promise<User | null> {
	await pb.collection('_superusers').authWithPassword(email, password);
	return pb.authStore.record as User | null;
}
