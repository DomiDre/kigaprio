<script lang="ts">
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/stores/auth';
	import { onMount } from 'svelte';

	import { PUBLIC_API_URL } from '$env/static/public';
	import { pb } from '$lib/services/pocketbase';

	export async function fetchProtectedData() {
		const token = pb.authStore.token;
		if (!token) throw new Error('Not authenticated');

		console.log('Attempting');
		const response = await fetch(`${PUBLIC_API_URL}/api/v1/protected-data`, {
			headers: {
				Authorization: `Bearer ${token}`
			}
		});

		if (!response.ok) {
			throw new Error('Unauthorized or fetch error');
		}

		return await response.json();
	}
	onMount(() => {
		// Redirect unauthenticated users to /login
		if (!$isAuthenticated) {
			goto('/login');
		} else {
			fetchProtectedData().then((response) => {
				console.log(response);
			});
		}
	});
</script>

Welcome to the dashboard
