import { writable } from 'svelte/store';
import { pb } from '$lib/services/pocketbase';
import type { User } from '$lib/types/pocketbase';

export const currentUser = writable<User | null>(pb.authStore.model as User | null);
export const isAuthenticated = writable<boolean>(pb.authStore.isValid);

pb.authStore.onChange(() => {
	currentUser.set(pb.authStore.model as User | null);
	isAuthenticated.set(pb.authStore.isValid);
});
