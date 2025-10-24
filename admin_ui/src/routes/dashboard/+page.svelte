<script lang="ts">
	import AccountGroup from 'virtual:icons/mdi/account-group';
	import CheckCircle from 'virtual:icons/mdi/check-circle';
	import ClockOutline from 'virtual:icons/mdi/clock-outline';
	import TrendingUp from 'virtual:icons/mdi/trending-up';
	import KeyVariant from 'virtual:icons/mdi/key-variant';
	import Upload from 'virtual:icons/mdi/upload';
	import Download from 'virtual:icons/mdi/download';
	import Plus from 'virtual:icons/mdi/plus';
	import Magnify from 'virtual:icons/mdi/magnify';
	import Close from 'virtual:icons/mdi/close';

	let selectedMonth = '2025-10';
	let keyUploaded = false;
	let showManualEntry = false;
	let searchQuery = '';
	let keyFile: File | null = null;

	// Mock data for design purposes
	const stats = {
		totalUsers: 45,
		submitted: 32,
		pending: 13,
		submissionRate: 71
	};

	const users = [
		{ id: 1, name: 'Anna Schmidt', submitted: true, date: '2025-10-15', encrypted: true },
		{ id: 2, name: 'Max Müller', submitted: true, date: '2025-10-18', encrypted: true },
		{ id: 3, name: 'Lisa Weber', submitted: false, date: null, encrypted: false },
		{ id: 4, name: 'Tom Fischer', submitted: true, date: '2025-10-12', encrypted: true },
		{ id: 5, name: 'Sarah Klein', submitted: false, date: null, encrypted: false },
		{ id: 6, name: 'Michael Wolf', submitted: true, date: '2025-10-20', encrypted: true },
		{ id: 7, name: 'Julia Becker', submitted: false, date: null, encrypted: false },
		{ id: 8, name: 'David Koch', submitted: true, date: '2025-10-14', encrypted: true },
		{ id: 9, name: 'Emma Wagner', submitted: true, date: '2025-10-16', encrypted: true },
		{ id: 10, name: 'Lukas Hoffmann', submitted: false, date: null, encrypted: false }
	];

	function handleKeyUpload(event: Event) {
		const input = event.target as HTMLInputElement;
		if (input.files && input.files[0]) {
			keyFile = input.files[0];
			keyUploaded = true;
		}
	}

	function handleKeyDrop(event: DragEvent) {
		event.preventDefault();
		if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
			keyFile = event.dataTransfer.files[0];
			keyUploaded = true;
		}
	}

	function preventDefaults(event: DragEvent) {
		event.preventDefault();
	}

	function exportToExcel() {
		console.log('Exporting to Excel...');
	}

	function openManualEntry() {
		showManualEntry = true;
	}

	function closeManualEntry() {
		showManualEntry = false;
	}
</script>

<div class="min-h-screen bg-gray-50">
	<!-- Header -->
	<div class="border-b bg-white shadow-sm">
		<div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
			<div class="flex items-center justify-between">
				<div>
					<h1 class="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
					<p class="mt-1 text-sm text-gray-500">Manage user submissions and export data</p>
				</div>
				<div class="flex items-center gap-4">
					<select
						bind:value={selectedMonth}
						class="rounded-lg border border-gray-300 px-4 py-2 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
					>
						<option value="2025-10">October 2025</option>
						<option value="2025-09">September 2025</option>
						<option value="2025-08">August 2025</option>
					</select>
				</div>
			</div>
		</div>
	</div>

	<div class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
		<!-- Statistics Cards -->
		<div class="mb-8 grid grid-cols-1 gap-6 md:grid-cols-4">
			<!-- Total Users -->
			<div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm font-medium text-gray-600">Total Users</p>
						<p class="mt-2 text-3xl font-bold text-gray-900">{stats.totalUsers}</p>
					</div>
					<div class="rounded-lg bg-blue-50 p-3">
						<AccountGroup class="h-6 w-6 text-blue-600" />
					</div>
				</div>
			</div>

			<!-- Submitted -->
			<div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm font-medium text-gray-600">Submitted</p>
						<p class="mt-2 text-3xl font-bold text-green-600">{stats.submitted}</p>
					</div>
					<div class="rounded-lg bg-green-50 p-3">
						<CheckCircle class="h-6 w-6 text-green-600" />
					</div>
				</div>
			</div>

			<!-- Pending -->
			<div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm font-medium text-gray-600">Pending</p>
						<p class="mt-2 text-3xl font-bold text-orange-600">{stats.pending}</p>
					</div>
					<div class="rounded-lg bg-orange-50 p-3">
						<ClockOutline class="h-6 w-6 text-orange-600" />
					</div>
				</div>
			</div>

			<!-- Submission Rate -->
			<div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm font-medium text-gray-600">Submission Rate</p>
						<p class="mt-2 text-3xl font-bold text-purple-600">{stats.submissionRate}%</p>
					</div>
					<div class="rounded-lg bg-purple-50 p-3">
						<TrendingUp class="h-6 w-6 text-purple-600" />
					</div>
				</div>
			</div>
		</div>

		<div class="grid grid-cols-1 gap-8 lg:grid-cols-3">
			<!-- Main Content Area -->
			<div class="space-y-6 lg:col-span-2">
				<!-- Private Key Upload -->
				<div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
					<div class="mb-4 flex items-center gap-2">
						<KeyVariant class="h-5 w-5 text-gray-700" />
						<h2 class="text-lg font-semibold text-gray-900">Private Key</h2>
					</div>

					<div
						class="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center transition-colors hover:border-blue-400 hover:bg-blue-50"
						on:drop={handleKeyDrop}
						on:dragover={preventDefaults}
						on:dragenter={preventDefaults}
					>
						<input
							type="file"
							id="keyFileInput"
							accept=".pem,.key"
							class="hidden"
							on:change={handleKeyUpload}
						/>

						{#if keyUploaded && keyFile}
							<div class="flex flex-col items-center">
								<div class="mb-3 rounded-full bg-green-50 p-3">
									<CheckCircle class="h-8 w-8 text-green-600" />
								</div>
								<p class="text-sm font-medium text-gray-900">{keyFile.name}</p>
								<p class="mt-1 text-xs text-gray-500">Private key loaded successfully</p>
								<button
									type="button"
									class="mt-4 px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
									on:click={() => {
										keyUploaded = false;
										keyFile = null;
									}}
								>
									Remove
								</button>
							</div>
						{:else}
							<div class="flex flex-col items-center">
								<Upload class="mb-3 h-12 w-12 text-gray-400" />
								<p class="mb-1 text-sm font-medium text-gray-900">
									Drop your private key file here
								</p>
								<p class="mb-4 text-xs text-gray-500">or</p>
								<label
									for="keyFileInput"
									class="cursor-pointer rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700"
								>
									Browse Files
								</label>
								<p class="mt-2 text-xs text-gray-400">Accepts .pem or .key files</p>
							</div>
						{/if}
					</div>

					{#if keyUploaded}
						<div class="mt-4 rounded-lg border border-green-200 bg-green-50 p-4">
							<p class="text-sm text-green-800">
								✓ Key loaded. You can now view and decrypt user data.
							</p>
						</div>
					{:else}
						<div class="mt-4 rounded-lg border border-yellow-200 bg-yellow-50 p-4">
							<p class="text-sm text-yellow-800">
								⚠ Upload your private key to decrypt and view submission data.
							</p>
						</div>
					{/if}
				</div>

				<!-- User Submissions Table -->
				<div class="rounded-xl border border-gray-200 bg-white shadow-sm">
					<div class="border-b border-gray-200 p-6">
						<div class="mb-4 flex items-center justify-between">
							<h2 class="text-lg font-semibold text-gray-900">User Submissions</h2>
							<div class="flex items-center gap-3">
								<div class="relative">
									<Magnify
										class="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 transform text-gray-400"
									/>
									<input
										type="text"
										bind:value={searchQuery}
										placeholder="Search users..."
										class="rounded-lg border border-gray-300 py-2 pr-4 pl-10 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
									/>
								</div>
							</div>
						</div>
					</div>

					<div class="overflow-x-auto">
						<table class="w-full">
							<thead class="border-b border-gray-200 bg-gray-50">
								<tr>
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										User
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Status
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Submission Date
									</th>
									<th
										class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
									>
										Actions
									</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-gray-200 bg-white">
								{#each users as user}
									<tr class="transition-colors hover:bg-gray-50">
										<td class="px-6 py-4 whitespace-nowrap">
											<div class="flex items-center">
												<div
													class="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-blue-400 to-blue-600 font-semibold text-white"
												>
													{user.name.charAt(0)}
												</div>
												<div class="ml-3">
													<p class="text-sm font-medium text-gray-900">{user.name}</p>
													<p class="text-xs text-gray-500">ID: {user.id}</p>
												</div>
											</div>
										</td>
										<td class="px-6 py-4 whitespace-nowrap">
											{#if user.submitted}
												<span
													class="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800"
												>
													<CheckCircle class="mr-1 h-3 w-3" />
													Submitted
												</span>
											{:else}
												<span
													class="inline-flex items-center rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-800"
												>
													<ClockOutline class="mr-1 h-3 w-3" />
													Pending
												</span>
											{/if}
										</td>
										<td class="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
											{user.date || 'Not submitted'}
										</td>
										<td class="px-6 py-4 text-sm whitespace-nowrap">
											{#if user.submitted && keyUploaded}
												<button type="button" class="font-medium text-blue-600 hover:text-blue-800">
													View Data
												</button>
											{:else if !user.submitted}
												<button
													type="button"
													class="font-medium text-gray-600 hover:text-gray-800"
													on:click={openManualEntry}
												>
													Enter Manually
												</button>
											{:else}
												<span class="text-gray-400">Upload key first</span>
											{/if}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			</div>

			<!-- Sidebar Actions -->
			<div class="space-y-6">
				<!-- Quick Actions -->
				<div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
					<h3 class="mb-4 text-lg font-semibold text-gray-900">Quick Actions</h3>
					<div class="space-y-3">
						<button
							type="button"
							class="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 font-medium text-white transition-colors hover:bg-blue-700"
							on:click={openManualEntry}
						>
							<Plus class="h-5 w-5" />
							Manual Entry
						</button>

						<button
							type="button"
							class="flex w-full items-center justify-center gap-2 rounded-lg bg-green-600 px-4 py-3 font-medium text-white transition-colors hover:bg-green-700"
							on:click={exportToExcel}
							disabled={!keyUploaded}
							class:opacity-50={!keyUploaded}
							class:cursor-not-allowed={!keyUploaded}
						>
							<Download class="h-5 w-5" />
							Export to Excel
						</button>
					</div>

					{#if !keyUploaded}
						<div class="mt-4 rounded-lg border border-yellow-200 bg-yellow-50 p-3">
							<p class="text-xs text-yellow-800">Upload private key to enable export</p>
						</div>
					{/if}
				</div>

				<!-- Monthly Overview -->
				<div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
					<h3 class="mb-4 text-lg font-semibold text-gray-900">Monthly Overview</h3>
					<div class="space-y-4">
						<div>
							<div class="mb-2 flex justify-between text-sm">
								<span class="text-gray-600">Completion Progress</span>
								<span class="font-medium text-gray-900">{stats.submissionRate}%</span>
							</div>
							<div class="h-2.5 w-full rounded-full bg-gray-200">
								<div
									class="h-2.5 rounded-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all duration-500"
									style="width: {stats.submissionRate}%"
								></div>
							</div>
						</div>

						<div class="border-t border-gray-200 pt-4">
							<div class="mb-2 flex items-center justify-between">
								<span class="text-sm text-gray-600">Encrypted Submissions</span>
								<span class="text-sm font-medium text-gray-900">{stats.submitted}</span>
							</div>
							<div class="flex items-center justify-between">
								<span class="text-sm text-gray-600">Paper Submissions</span>
								<span class="text-sm font-medium text-gray-900">0</span>
							</div>
						</div>
					</div>
				</div>

				<!-- Recent Activity -->
				<div class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
					<h3 class="mb-4 text-lg font-semibold text-gray-900">Recent Activity</h3>
					<div class="space-y-3">
						<div class="flex items-start gap-3">
							<div class="mt-2 h-2 w-2 rounded-full bg-green-500"></div>
							<div class="flex-1">
								<p class="text-sm text-gray-900">Michael Wolf submitted</p>
								<p class="text-xs text-gray-500">2 hours ago</p>
							</div>
						</div>
						<div class="flex items-start gap-3">
							<div class="mt-2 h-2 w-2 rounded-full bg-green-500"></div>
							<div class="flex-1">
								<p class="text-sm text-gray-900">Max Müller submitted</p>
								<p class="text-xs text-gray-500">5 hours ago</p>
							</div>
						</div>
						<div class="flex items-start gap-3">
							<div class="mt-2 h-2 w-2 rounded-full bg-green-500"></div>
							<div class="flex-1">
								<p class="text-sm text-gray-900">Anna Schmidt submitted</p>
								<p class="text-xs text-gray-500">1 day ago</p>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>

<!-- Manual Entry Modal -->
{#if showManualEntry}
	<div class="bg-opacity-50 fixed inset-0 z-50 flex items-center justify-center bg-black p-4">
		<div class="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white shadow-2xl">
			<div class="border-b border-gray-200 p-6">
				<div class="flex items-center justify-between">
					<h2 class="text-xl font-bold text-gray-900">Manual Data Entry</h2>
					<button
						type="button"
						class="text-gray-400 transition-colors hover:text-gray-600"
						on:click={closeManualEntry}
					>
						<Close class="h-6 w-6" />
					</button>
				</div>
			</div>

			<div class="space-y-4 p-6">
				<div>
					<label class="mb-2 block text-sm font-medium text-gray-700">Select User</label>
					<select
						class="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
					>
						<option value="">Choose a user...</option>
						{#each users.filter((u) => !u.submitted) as user}
							<option value={user.id}>{user.name}</option>
						{/each}
					</select>
				</div>

				<div class="rounded-lg border border-blue-200 bg-blue-50 p-4">
					<p class="text-sm text-blue-800">
						Enter data for users who submitted on paper. This data will be encrypted with the public
						key before storage.
					</p>
				</div>

				<!-- Placeholder for data entry form -->
				<div class="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
					<p class="text-gray-500">Data entry form will be displayed here</p>
					<p class="mt-2 text-sm text-gray-400">This will be implemented in the next step</p>
				</div>
			</div>

			<div class="flex justify-end gap-3 border-t border-gray-200 p-6">
				<button
					type="button"
					class="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50"
					on:click={closeManualEntry}
				>
					Cancel
				</button>
				<button
					type="button"
					class="rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700"
				>
					Save Entry
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	/* Additional custom styles if needed */
</style>

