<script lang="ts">
	import { goto } from '$app/navigation';
	import { pb } from '$lib/services/pocketbase';
	import { currentUser } from '$lib/stores/auth';
	import { loginUser, loginAdmin } from '$lib/services/auth';

	let email = '';
	let password = '';
	let isAdmin = false;
	let error = '';

	async function handleLogin() {
		error = '';
		try {
			if (isAdmin) {
				await loginAdmin(email, password);
				goto('/admin/dashboard');
			} else {
				await loginUser(email, password);
				goto('/dashboard');
			}
		} catch (err) {
			error = (err as Error).message;
		}
	}

	function handleLogout() {
		pb.authStore.clear();
		goto('/');
	}
</script>

{#if $currentUser}
	<div class="rounded bg-gray-100 p-4 shadow">
		<p class="mb-2 text-gray-800">Welcome, {$currentUser.email}!</p>
		<button
			class="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
			on:click={handleLogout}>Logout</button
		>
	</div>
{:else}
	<form
		class="mx-auto mt-8 max-w-sm rounded border bg-white p-6 shadow"
		on:submit|preventDefault={handleLogin}
	>
		<label class="mb-2 block text-sm font-medium text-gray-700">
			Email
			<input
				type="email"
				bind:value={email}
				class="mt-1 block w-full rounded border p-2 focus:ring-2 focus:ring-blue-600 focus:outline-none"
				required
			/>
		</label>
		<label class="mb-2 block text-sm font-medium text-gray-700">
			Password
			<input
				type="password"
				bind:value={password}
				class="mt-1 block w-full rounded border p-2 focus:ring-2 focus:ring-blue-600 focus:outline-none"
				required
			/>
		</label>
		<label class="mt-6 mb-4 inline-flex items-center">
			<input type="checkbox" bind:checked={isAdmin} class="mr-2" />
			<span>Admin Login</span>
		</label>
		<button type="submit" class="w-full rounded bg-blue-600 py-2 text-white hover:bg-blue-700">
			Login
		</button>
		{#if error}
			<p class="mt-2 text-red-500">{error}</p>
		{/if}
	</form>
{/if}

