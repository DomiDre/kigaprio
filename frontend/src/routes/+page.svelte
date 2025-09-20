<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { currentUser, isAuthenticated } from '$lib/stores/auth';

	onMount(() => {
		if (!$isAuthenticated) {
			goto('/login');
		}
	});
</script>

{#if $isAuthenticated && $currentUser}
	<div class="flex min-h-screen flex-col items-center justify-center bg-gray-50">
		<div class="mt-20 w-full max-w-md rounded bg-white p-8 shadow">
			<h1 class="mb-4 text-3xl font-bold text-gray-900">Welcome</h1>
			<p class="text-gray-700">Hello, {$currentUser.email}!</p>
			<!-- content for logged-in users -->
		</div>
	</div>
{/if}
