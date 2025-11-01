<script lang="ts">
	import Alert from 'virtual:icons/mdi/alert';
	import Close from 'virtual:icons/mdi/close';

	interface Props {
		message: string;
		title?: string;
		onClose: () => void;
	}

	let { message, title, onClose }: Props = $props();
</script>

<div
	class="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
>
	<div class="flex items-start gap-2">
		<Alert class="h-5 w-5 text-red-600 dark:text-red-400" />
		<div class="flex-1">
			{#if title}
				<p class="text-sm font-medium text-red-900 dark:text-red-300">{title}</p>
			{/if}
			<p class="text-sm text-red-800 dark:text-red-400">{message}</p>
		</div>
		<button
			type="button"
			class="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
			onclick={onClose}
		>
			<Close class="h-5 w-5" />
		</button>
	</div>
</div>
