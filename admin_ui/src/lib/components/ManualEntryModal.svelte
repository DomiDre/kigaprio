<script lang="ts">
	import Close from 'virtual:icons/mdi/close';

	interface Props {
		onClose: () => void;
	}

	let { onClose }: Props = $props();
</script>

<div class="bg-opacity-50 fixed inset-0 z-50 flex items-center justify-center bg-black p-4">
	<div
		class="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white shadow-2xl dark:bg-gray-800"
	>
		<div class="border-b border-gray-200 p-6 dark:border-gray-700">
			<div class="flex items-center justify-between">
				<h2 class="text-xl font-bold text-gray-900 dark:text-white">Manual Data Entry</h2>
				<button
					type="button"
					class="text-gray-400 transition-colors hover:text-gray-600 dark:hover:text-gray-300"
					onclick={onClose}
				>
					<Close class="h-6 w-6" />
				</button>
			</div>
		</div>

		<div class="space-y-4 p-6">
			<div
				class="rounded-lg border border-purple-200 bg-gradient-to-br from-purple-50 to-blue-50 p-4 dark:border-purple-700 dark:from-purple-900/30 dark:to-blue-900/30"
			>
				<p class="text-sm text-purple-800 dark:text-purple-400">
					Enter data for users who submitted on paper. This data will be encrypted with the public
					key before storage.
				</p>
			</div>

			<!-- Placeholder for data entry form -->
			<div
				class="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center dark:border-gray-600"
			>
				<p class="text-gray-500 dark:text-gray-400">Data entry form will be displayed here</p>
				<p class="mt-2 text-sm text-gray-400 dark:text-gray-500">
					This will be implemented in the next step
				</p>
			</div>
		</div>

		<div class="flex justify-end gap-3 border-t border-gray-200 p-6 dark:border-gray-700">
			<button
				type="button"
				class="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
				onclick={onClose}
			>
				Cancel
			</button>
			<button
				type="button"
				class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 font-semibold text-white shadow-lg transition-all hover:scale-105"
			>
				Save Entry
			</button>
		</div>
	</div>
</div>
