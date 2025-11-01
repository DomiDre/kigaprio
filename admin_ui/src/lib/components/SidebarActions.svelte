<script lang="ts">
	import Plus from 'virtual:icons/mdi/plus';
	import Download from 'virtual:icons/mdi/download';
	import Lock from 'virtual:icons/mdi/lock';
	import type { Stats } from '$lib/types/dashboard';

	interface Props {
		keyUploaded: boolean;
		stats: Stats;
		decryptedUsersCount: number;
		onManualEntry: () => void;
		onExportExcel: () => void;
	}

	let { keyUploaded, stats, decryptedUsersCount, onManualEntry, onExportExcel }: Props = $props();
</script>

<div class="space-y-6">
	<!-- Quick Actions -->
	<div
		class="rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-800"
	>
		<h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Quick Actions</h3>
		<div class="space-y-3">
			<button
				type="button"
				class="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-3 font-semibold text-white shadow-lg transition-all hover:scale-105"
				onclick={onManualEntry}
			>
				<Plus class="h-5 w-5" />
				Manual Entry
			</button>

			<button
				type="button"
				class="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-green-600 to-emerald-600 px-4 py-3 font-semibold text-white shadow-lg transition-all hover:scale-105 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
				onclick={onExportExcel}
				disabled={!keyUploaded || stats.totalUsers === 0}
			>
				<Download class="h-5 w-5" />
				Export to Excel
			</button>
		</div>

		{#if !keyUploaded}
			<div
				class="mt-4 rounded-lg border border-yellow-200 bg-yellow-50 p-3 dark:border-yellow-800 dark:bg-yellow-900/20"
			>
				<p class="text-xs text-yellow-800 dark:text-yellow-400">
					Upload private key to enable export
				</p>
			</div>
		{/if}
	</div>

	<!-- Monthly Overview -->
	<div
		class="rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-800"
	>
		<h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Monthly Overview</h3>
		<div class="space-y-4">
			<div>
				<div class="mb-2 flex justify-between text-sm">
					<span class="text-gray-600 dark:text-gray-300">Completion Progress</span>
					<span class="font-medium text-gray-900 dark:text-white">{stats.submissionRate}%</span>
				</div>
				<div class="h-2.5 w-full rounded-full bg-gray-200 dark:bg-gray-700">
					<div
						class="h-2.5 rounded-full bg-gradient-to-r from-purple-500 to-blue-600 transition-all duration-500"
						style="width: {stats.submissionRate}%"
					></div>
				</div>
			</div>

			<div class="border-t border-gray-200 pt-4 dark:border-gray-700">
				<div class="mb-2 flex items-center justify-between">
					<span class="text-sm text-gray-600 dark:text-gray-300">Encrypted Submissions</span>
					<span class="text-sm font-medium text-gray-900 dark:text-white">{stats.submitted}</span>
				</div>
				<div class="flex items-center justify-between">
					<span class="text-sm text-gray-600 dark:text-gray-300">Paper Submissions</span>
					<span class="text-sm font-medium text-gray-900 dark:text-white">0</span>
				</div>
				{#if keyUploaded}
					<div
						class="mt-2 flex items-center justify-between border-t border-gray-200 pt-2 dark:border-gray-700"
					>
						<span class="text-sm text-gray-600 dark:text-gray-300">Decrypted</span>
						<span class="text-sm font-medium text-purple-600 dark:text-purple-400"
							>{decryptedUsersCount}</span
						>
					</div>
				{/if}
			</div>
		</div>
	</div>

	<!-- Data Status Info -->
	<div
		class="rounded-xl border border-purple-200 bg-gradient-to-br from-purple-50 to-blue-50 p-6 shadow-xl dark:border-purple-700 dark:from-purple-900/30 dark:to-blue-900/30"
	>
		<h3
			class="mb-2 flex items-center gap-2 text-sm font-semibold text-purple-900 dark:text-purple-300"
		>
			<Lock class="h-4 w-4" />
			Encryption Status
		</h3>
		<p class="text-xs text-purple-800 dark:text-purple-400">
			All user data is encrypted. Upload the admin private key to decrypt and view the
			priorities overview table.
		</p>
	</div>
</div>
