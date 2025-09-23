<script lang="ts">
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/stores/auth';
	import { onMount } from 'svelte';

	import { pb } from '$lib/services/pocketbase';

	const apiUrl = import.meta.env.DEV
		? 'http://localhost:8000/' // Dev mode - full URL to FastAPI
		: '/'; // Prod mode - relative path
	export async function fetchProtectedData() {
		const token = pb.authStore.token;
		if (!token) throw new Error('Not authenticated');

		console.log('Attempting');
		const response = await fetch(`${apiUrl}/api/v1/protected-data`, {
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
