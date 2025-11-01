<script lang="ts">
	import Magnify from 'virtual:icons/mdi/magnify';
	import CheckCircle from 'virtual:icons/mdi/check-circle';
	import ClockOutline from 'virtual:icons/mdi/clock-outline';
	import Lock from 'virtual:icons/mdi/lock';
	import type { UserDisplay } from '$lib/types/dashboard';

	interface Props {
		filteredUsers: UserDisplay[];
		searchQuery: string;
		keyUploaded: boolean;
		isDecrypting: boolean;
		totalUsers: number;
		isDecrypted: (userName: string) => boolean;
		getDisplayName: (userName: string) => string;
		onSearchChange: (value: string) => void;
		onViewUser: (user: UserDisplay) => void;
		onManualEntry: () => void;
	}

	let {
		filteredUsers,
		searchQuery,
		keyUploaded,
		isDecrypting,
		totalUsers,
		isDecrypted,
		getDisplayName,
		onSearchChange,
		onViewUser,
		onManualEntry
	}: Props = $props();
</script>

<div
	class="rounded-xl border border-gray-200 bg-white shadow-xl dark:border-gray-700 dark:bg-gray-800"
>
	<div class="border-b border-gray-200 p-6 dark:border-gray-700">
		<div class="mb-4 flex items-center justify-between">
			<h2 class="text-lg font-semibold text-gray-900 dark:text-white">User Submissions</h2>
			<div class="flex items-center gap-3">
				<div class="relative">
					<Magnify
						class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400"
					/>
					<input
						type="text"
						value={searchQuery}
						oninput={(e) => onSearchChange((e.target as HTMLInputElement).value)}
						placeholder="Search users..."
						class="rounded-lg border border-gray-300 py-2 pr-4 pl-10 text-sm focus:border-purple-500 focus:ring-2 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
					/>
				</div>
			</div>
		</div>
	</div>

	<div class="overflow-x-auto">
		<table class="w-full">
			<thead
				class="border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900/50"
			>
				<tr>
					<th
						class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400"
					>
						User
					</th>
					<th
						class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400"
					>
						Status
					</th>
					<th
						class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400"
					>
						Encryption
					</th>
					<th
						class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400"
					>
						Actions
					</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-800">
				{#if filteredUsers.length === 0}
					<tr>
						<td colspan="4" class="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
							{#if totalUsers === 0}
								Keine Einreichungen für diesen Monat gefunden
							{:else}
								Keine Benutzer gefunden für "{searchQuery}"
							{/if}
						</td>
					</tr>
				{:else}
					{#each filteredUsers as user (user.name)}
						{@const displayName = getDisplayName(user.name)}
						{@const userDecrypted = isDecrypted(user.name)}
						<tr class="transition-colors hover:bg-gray-50 dark:hover:bg-gray-700/50">
							<td class="whitespace-nowrap px-6 py-4">
								<div class="flex items-center">
									<div
										class="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-purple-400 to-blue-600 font-semibold text-white"
									>
										{displayName.charAt(0).toUpperCase()}
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-gray-900 dark:text-white">
											{displayName}
											{#if userDecrypted && displayName !== user.name}
												<span class="ml-1 text-xs text-purple-600 dark:text-purple-400">✓</span>
											{/if}
										</p>
										<p class="text-xs text-gray-500 dark:text-gray-400">ID: {user.id}</p>
									</div>
								</div>
							</td>
							<td class="whitespace-nowrap px-6 py-4">
								{#if user.submitted && user.hasData}
									<span
										class="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900/30 dark:text-green-400"
									>
										<CheckCircle class="mr-1 h-3 w-3" />
										Submitted
									</span>
								{:else}
									<span
										class="inline-flex items-center rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-800 dark:bg-orange-900/30 dark:text-orange-400"
									>
										<ClockOutline class="mr-1 h-3 w-3" />
										Pending
									</span>
								{/if}
							</td>
							<td class="whitespace-nowrap px-6 py-4">
								{#if user.encrypted}
									{#if userDecrypted}
										<span
											class="inline-flex items-center rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-800 dark:bg-purple-900/30 dark:text-purple-400"
											title="Decrypted locally"
										>
											<CheckCircle class="mr-1 h-3 w-3" />
											Decrypted
										</span>
									{:else}
										<span
											class="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900/30 dark:text-blue-400"
											title="Data is encrypted"
										>
											<Lock class="mr-1 h-3 w-3" />
											Encrypted
										</span>
									{/if}
								{:else}
									<span class="text-xs text-gray-400">No data</span>
								{/if}
							</td>
							<td class="whitespace-nowrap px-6 py-4 text-sm">
								{#if user.submitted && user.hasData && keyUploaded}
									<button
										type="button"
										class="font-medium text-purple-600 transition-colors hover:text-purple-800 disabled:cursor-not-allowed disabled:opacity-50 dark:text-purple-400 dark:hover:text-purple-300"
										onclick={() => onViewUser(user)}
										disabled={isDecrypting}
									>
										{isDecrypting ? 'Entschlüsseln...' : 'View Data'}
									</button>
								{:else if user.submitted && user.hasData && !keyUploaded}
									<span class="text-gray-400 dark:text-gray-500">Upload key first</span>
								{:else}
									<button
										type="button"
										class="font-medium text-gray-600 transition-colors hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-300"
										onclick={onManualEntry}
									>
										Enter Manually
									</button>
								{/if}
							</td>
						</tr>
					{/each}
				{/if}
			</tbody>
		</table>
	</div>
</div>
