<script lang="ts">
	import KeyVariant from 'virtual:icons/mdi/key-variant';
	import Upload from 'virtual:icons/mdi/upload';
	import CheckCircle from 'virtual:icons/mdi/check-circle';

	interface Props {
		keyUploaded: boolean;
		keyFile: File | null;
		showPassphrasePrompt: boolean;
		passphraseInput: string;
		decryptedUsersCount: number;
		onKeyUpload: (event: Event) => void;
		onKeyDrop: (event: DragEvent) => void;
		onPassphraseChange: (value: string) => void;
		onSubmitPassphrase: () => void;
		onCancelPassphrase: () => void;
		onRemoveKey: () => void;
	}

	let {
		keyUploaded,
		keyFile,
		showPassphrasePrompt,
		passphraseInput,
		decryptedUsersCount,
		onKeyUpload,
		onKeyDrop,
		onPassphraseChange,
		onSubmitPassphrase,
		onCancelPassphrase,
		onRemoveKey
	}: Props = $props();

	function preventDefaults(event: DragEvent) {
		event.preventDefault();
	}
</script>

<div
	class="rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-800"
>
	<div class="mb-4 flex items-center gap-2">
		<KeyVariant class="h-5 w-5 text-gray-700 dark:text-gray-300" />
		<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Private Key</h2>
	</div>

	{#if showPassphrasePrompt}
		<!-- Passphrase Input -->
		<div
			class="rounded-lg border-2 border-purple-300 bg-gradient-to-br from-purple-50 to-blue-50 p-6 dark:border-purple-700 dark:from-purple-900/30 dark:to-blue-900/30"
		>
			<div class="mb-4 text-center">
				<p class="text-sm font-medium text-gray-900 dark:text-white">
					This key is passphrase-protected
				</p>
				<p class="mt-1 text-xs text-gray-600 dark:text-gray-400">
					Enter your passphrase to decrypt the private key
				</p>
			</div>

			<input
				type="password"
				value={passphraseInput}
				oninput={(e) => onPassphraseChange((e.target as HTMLInputElement).value)}
				placeholder="Enter passphrase"
				class="mb-4 w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-purple-500 focus:ring-2 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
				onkeypress={(e) => e.key === 'Enter' && onSubmitPassphrase()}
			/>

			<div class="flex gap-3">
				<button
					type="button"
					class="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
					onclick={onCancelPassphrase}
				>
					Cancel
				</button>
				<button
					type="button"
					class="flex-1 rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 font-semibold text-white shadow-lg transition-all hover:scale-105 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
					onclick={onSubmitPassphrase}
					disabled={!passphraseInput}
				>
					Unlock Key
				</button>
			</div>
		</div>
	{:else}
		<!-- Normal upload area -->
		<div
			class="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center transition-colors hover:border-purple-400 hover:bg-purple-50 dark:border-gray-600 dark:hover:border-purple-600 dark:hover:bg-purple-900/20"
			ondrop={onKeyDrop}
			ondragover={preventDefaults}
			ondragenter={preventDefaults}
			role="region"
			aria-label="Private key file drop zone to locally decrypt data"
		>
			<input
				type="file"
				id="keyFileInput"
				accept=".pem,.key"
				class="hidden"
				onchange={onKeyUpload}
			/>

			{#if keyUploaded && keyFile}
				<div class="flex flex-col items-center">
					<div class="mb-3 rounded-full bg-green-50 p-3 dark:bg-green-900/30">
						<CheckCircle class="h-8 w-8 text-green-600 dark:text-green-400" />
					</div>
					<p class="text-sm font-medium text-gray-900 dark:text-white">{keyFile.name}</p>
					<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
						Private key loaded successfully
					</p>
					{#if decryptedUsersCount > 0}
						<p class="mt-2 text-xs font-medium text-purple-600 dark:text-purple-400">
							✓ {decryptedUsersCount} user(s) decrypted
						</p>
					{/if}
					<button
						type="button"
						class="mt-4 rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
						onclick={onRemoveKey}
					>
						Remove Key
					</button>
				</div>
			{:else}
				<div class="flex flex-col items-center">
					<Upload class="mb-3 h-12 w-12 text-gray-400 dark:text-gray-500" />
					<p class="mb-1 text-sm font-medium text-gray-900 dark:text-white">
						Drop your private key file here
					</p>
					<p class="mb-4 text-xs text-gray-500 dark:text-gray-400">or</p>
					<label
						for="keyFileInput"
						class="cursor-pointer rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 font-semibold text-white shadow-lg transition-all hover:scale-105"
					>
						Browse Files
					</label>
					<p class="mt-2 text-xs text-gray-400 dark:text-gray-500">Accepts .pem or .key files</p>
				</div>
			{/if}
		</div>
	{/if}

	{#if keyUploaded}
		<div
			class="mt-4 rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-900/20"
		>
			<p class="text-sm text-green-800 dark:text-green-400">
				✓ Key loaded. Data decrypted and overview available above.
			</p>
		</div>
	{:else}
		<div
			class="mt-4 rounded-lg border border-yellow-200 bg-yellow-50 p-4 dark:border-yellow-800 dark:bg-yellow-900/20"
		>
			<p class="text-sm text-yellow-800 dark:text-yellow-400">
				⚠ Upload your private key to decrypt and view submission data.
			</p>
		</div>
	{/if}
</div>
