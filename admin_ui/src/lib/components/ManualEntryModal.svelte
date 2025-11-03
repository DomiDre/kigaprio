<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Priority } from './priorities';
	import type { WeekPriority } from './dashboard';

	const dispatch = createEventDispatcher<{
		close: void;
		submit: { identifier: string; month: string; weeks: WeekPriority[] };
	}>();

	let identifier = '';
	let month = '';
	let error = '';

	// Initialize 4 weeks of priorities
	let weeks: WeekPriority[] = [
		{ weekNumber: 1, monday: null, tuesday: null, wednesday: null, thursday: null, friday: null },
		{ weekNumber: 2, monday: null, tuesday: null, wednesday: null, thursday: null, friday: null },
		{ weekNumber: 3, monday: null, tuesday: null, wednesday: null, thursday: null, friday: null },
		{ weekNumber: 4, monday: null, tuesday: null, wednesday: null, thursday: null, friday: null }
	];

	const days: Array<'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday'> = [
		'monday',
		'tuesday',
		'wednesday',
		'thursday',
		'friday'
	];

	const dayLabels = {
		monday: 'Mo',
		tuesday: 'Di',
		wednesday: 'Mi',
		thursday: 'Do',
		friday: 'Fr'
	};

	function validatePriority(value: string): Priority {
		if (value === '' || value === null) return null;
		const num = parseInt(value, 10);
		if (num >= 1 && num <= 5) return num as Priority;
		return null;
	}

	function handlePriorityInput(
		weekIndex: number,
		day: 'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday',
		event: Event
	) {
		const target = event.target as HTMLInputElement;
		weeks[weekIndex][day] = validatePriority(target.value);
	}

	function handleSubmit() {
		error = '';

		// Validate identifier
		if (!identifier.trim()) {
			error = 'Bitte geben Sie eine Kennung ein (z.B. Teilnehmernummer)';
			return;
		}

		// Validate month format (YYYY-MM)
		const monthRegex = /^\d{4}-\d{2}$/;
		if (!monthRegex.test(month)) {
			error = 'Bitte geben Sie einen gültigen Monat ein (Format: YYYY-MM)';
			return;
		}

		// Check if at least one priority is set
		const hasAnyPriority = weeks.some((week) =>
			days.some((day) => week[day] !== null && week[day] !== undefined)
		);

		if (!hasAnyPriority) {
			error = 'Bitte geben Sie mindestens eine Priorität ein';
			return;
		}

		dispatch('submit', { identifier, month, weeks });
	}

	// Set default month to current month
	const now = new Date();
	month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
</script>

<div class="modal-backdrop" on:click={() => dispatch('close')} on:keydown={() => {}}>
	<div class="modal-content" on:click|stopPropagation on:keydown={() => {}}>
		<div class="modal-header">
			<h2>Manuelle Prioritäten-Eingabe</h2>
			<button class="close-btn" on:click={() => dispatch('close')}>&times;</button>
		</div>

		<div class="modal-body">
			<div class="form-section">
				<div class="form-row">
					<div class="form-group">
						<label for="identifier">Kennung (z.B. Teilnehmernummer):</label>
						<input
							id="identifier"
							type="text"
							bind:value={identifier}
							placeholder="123 oder ABC"
							class="form-input"
						/>
					</div>

					<div class="form-group">
						<label for="month">Monat:</label>
						<input id="month" type="month" bind:value={month} class="form-input" />
					</div>
				</div>

				{#if error}
					<div class="error-message">{error}</div>
				{/if}
			</div>

			<div class="priorities-grid">
				<div class="grid-header">
					<div class="week-label">Woche</div>
					{#each days as day, i (i)}
						<div class="day-label">{dayLabels[day]}</div>
					{/each}
				</div>

				{#each weeks as week, weekIndex (weekIndex)}
					<div class="grid-row">
						<div class="week-number">KW {week.weekNumber}</div>
						{#each days as day, i (i)}
							<div class="priority-cell">
								<input
									type="number"
									min="1"
									max="5"
									value={week[day] ?? ''}
									on:input={(e) => handlePriorityInput(weekIndex, day, e)}
									placeholder="-"
									class="priority-input"
								/>
							</div>
						{/each}
					</div>
				{/each}
			</div>

			<div class="help-text">
				<strong>Hinweis:</strong> Geben Sie Prioritäten von 1-5 ein (1 = höchste Priorität). Leer lassen
				= keine Angabe.
			</div>
		</div>

		<div class="modal-footer">
			<button class="btn btn-secondary" on:click={() => dispatch('close')}>Abbrechen</button>
			<button class="btn btn-primary" on:click={handleSubmit}>Speichern</button>
		</div>
	</div>
</div>

<style>
	.modal-backdrop {
		position: fixed;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		justify-content: center;
		align-items: center;
		z-index: 1000;
	}

	.modal-content {
		background: white;
		border-radius: 12px;
		width: 90%;
		max-width: 800px;
		max-height: 90vh;
		overflow-y: auto;
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
	}

	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1.5rem;
		border-bottom: 1px solid #e5e7eb;
	}

	.modal-header h2 {
		margin: 0;
		font-size: 1.5rem;
		color: #1f2937;
	}

	.close-btn {
		background: none;
		border: none;
		font-size: 2rem;
		color: #6b7280;
		cursor: pointer;
		padding: 0;
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 4px;
		transition: background-color 0.2s;
	}

	.close-btn:hover {
		background-color: #f3f4f6;
	}

	.modal-body {
		padding: 1.5rem;
	}

	.form-section {
		margin-bottom: 2rem;
	}

	.form-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.form-group label {
		font-weight: 600;
		color: #374151;
		font-size: 0.875rem;
	}

	.form-input {
		padding: 0.5rem;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 1rem;
	}

	.form-input:focus {
		outline: none;
		border-color: #3b82f6;
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
	}

	.error-message {
		margin-top: 1rem;
		padding: 0.75rem;
		background-color: #fef2f2;
		border: 1px solid #fecaca;
		border-radius: 6px;
		color: #991b1b;
		font-size: 0.875rem;
	}

	.priorities-grid {
		background: #f9fafb;
		border-radius: 8px;
		padding: 1rem;
		margin-bottom: 1rem;
	}

	.grid-header {
		display: grid;
		grid-template-columns: 80px repeat(5, 1fr);
		gap: 0.5rem;
		margin-bottom: 0.75rem;
		font-weight: 600;
		color: #6b7280;
		font-size: 0.875rem;
	}

	.week-label,
	.day-label {
		text-align: center;
	}

	.grid-row {
		display: grid;
		grid-template-columns: 80px repeat(5, 1fr);
		gap: 0.5rem;
		margin-bottom: 0.5rem;
		align-items: center;
	}

	.week-number {
		font-weight: 600;
		color: #374151;
		text-align: center;
		font-size: 0.875rem;
	}

	.priority-cell {
		display: flex;
		justify-content: center;
	}

	.priority-input {
		width: 100%;
		max-width: 60px;
		padding: 0.5rem;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		text-align: center;
		font-size: 1rem;
		font-weight: 600;
	}

	.priority-input:focus {
		outline: none;
		border-color: #3b82f6;
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
	}

	.priority-input::placeholder {
		color: #d1d5db;
	}

	/* Remove spinner buttons on number input */
	.priority-input::-webkit-inner-spin-button,
	.priority-input::-webkit-outer-spin-button {
		-webkit-appearance: none;
		margin: 0;
	}

	.priority-input[type='number'] {
		-moz-appearance: textfield;
	}

	.help-text {
		padding: 0.75rem;
		background-color: #eff6ff;
		border-radius: 6px;
		color: #1e40af;
		font-size: 0.875rem;
	}

	.modal-footer {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		padding: 1.5rem;
		border-top: 1px solid #e5e7eb;
	}

	.btn {
		padding: 0.625rem 1.25rem;
		border-radius: 6px;
		font-weight: 600;
		font-size: 0.875rem;
		cursor: pointer;
		border: none;
		transition: all 0.2s;
	}

	.btn-secondary {
		background-color: #f3f4f6;
		color: #374151;
	}

	.btn-secondary:hover {
		background-color: #e5e7eb;
	}

	.btn-primary {
		background-color: #3b82f6;
		color: white;
	}

	.btn-primary:hover {
		background-color: #2563eb;
	}

	@media (max-width: 640px) {
		.modal-content {
			width: 95%;
			max-height: 95vh;
		}

		.form-row {
			grid-template-columns: 1fr;
		}

		.grid-header,
		.grid-row {
			grid-template-columns: 60px repeat(5, 1fr);
			gap: 0.25rem;
		}

		.priority-input {
			max-width: 50px;
			padding: 0.375rem;
			font-size: 0.875rem;
		}

		.modal-header h2 {
			font-size: 1.25rem;
		}
	}
</style>
