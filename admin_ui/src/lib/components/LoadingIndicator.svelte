<script lang="ts">
	interface Props {
		message: string;
		color?: 'purple' | 'blue';
	}

	let { message, color = 'purple' }: Props = $props();

	const colorClasses = {
		purple: {
			border: 'border-purple-200 dark:border-purple-800',
			bg: 'bg-purple-50 dark:bg-purple-900/20',
			spinner: 'border-purple-600 border-t-transparent',
			text: 'text-purple-900 dark:text-purple-300'
		},
		blue: {
			border: 'border-blue-200 dark:border-blue-800',
			bg: 'bg-blue-50 dark:bg-blue-900/20',
			spinner: 'border-blue-600 border-t-transparent',
			text: 'text-blue-900 dark:text-blue-300'
		}
	};

	const classes = colorClasses[color];
</script>

<div class="mb-6 rounded-lg border {classes.border} {classes.bg} p-4">
	<div class="flex items-center gap-3">
		<div class="h-5 w-5 animate-spin rounded-full border-2 {classes.spinner}"></div>
		<p class="text-sm font-medium {classes.text}">{message}</p>
	</div>
</div>
