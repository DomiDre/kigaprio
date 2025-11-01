<script lang="ts">
	import { onMount } from 'svelte';
	import KeyVariant from 'virtual:icons/mdi/key-variant';
	import Upload from 'virtual:icons/mdi/upload';
	import CheckCircle from 'virtual:icons/mdi/check-circle';
	import Fingerprint from 'virtual:icons/mdi/fingerprint';
	import SecurityIcon from 'virtual:icons/mdi/security';
	import Alert from 'virtual:icons/mdi/alert';
	import { webAuthnCryptoService } from '$lib/services/webauthn-crypto';

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
		onYubiKeyAuth: () => Promise<void>;
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
		onRemoveKey,
		onYubiKeyAuth
	}: Props = $props();

	// Tab state
	let activeTab: 'file' | 'yubikey' = $state('file');
	let webAuthnSupported = $state(false);
	let yubiKeyRegistered = $state(false);
	let isAuthenticating = $state(false);

	// YubiKey registration
	let showYubiKeyRegistration = $state(false);
	let registrationKeyFile = $state<File | null>(null);
	let registrationPassphrase = $state('');

	onMount(() => {
		webAuthnSupported = webAuthnCryptoService.isWebAuthnSupported();
		if (webAuthnSupported) {
			yubiKeyRegistered = webAuthnCryptoService.isYubiKeyRegistered();
		}
	});

	function preventDefaults(event: DragEvent) {
		event.preventDefault();
	}

	async function handleRegistrationKeyUpload(event: Event) {
		const input = event.target as HTMLInputElement;
		if (input.files && input.files[0]) {
			registrationKeyFile = input.files[0];
		}
	}

	async function startYubiKeyRegistration() {
		showYubiKeyRegistration = true;
	}

	function cancelYubiKeyRegistration() {
		showYubiKeyRegistration = false;
		registrationKeyFile = null;
		registrationPassphrase = '';
	}

	async function completeYubiKeyRegistration() {
		if (!registrationKeyFile) {
			return;
		}

		isAuthenticating = true;

		try {
			const pemText = await registrationKeyFile.text();
			await webAuthnCryptoService.registerYubiKey(pemText, registrationPassphrase || undefined);

			yubiKeyRegistered = true;
			showYubiKeyRegistration = false;
			registrationKeyFile = null;
			registrationPassphrase = '';

			// Now authenticate
			await onYubiKeyAuth();
		} catch (err) {
			console.error('Registration failed:', err);
			throw err;
		} finally {
			isAuthenticating = false;
		}
	}

	async function authenticateWithYubiKey() {
		if (!yubiKeyRegistered) {
			startYubiKeyRegistration();
			return;
		}

		isAuthenticating = true;
		try {
			await onYubiKeyAuth();
		} finally {
			isAuthenticating = false;
		}
	}
</script>

<div
	class="rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-800"
>
	<div class="mb-4 flex items-center justify-between">
		<div class="flex items-center gap-2">
			<KeyVariant class="h-5 w-5 text-gray-700 dark:text-gray-300" />
			<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Authentication</h2>
		</div>
		{#if keyUploaded}
			<span
				class="flex items-center gap-2 rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800 dark:bg-green-900/30 dark:text-green-400"
			>
				<CheckCircle class="h-4 w-4" />
				Authenticated
			</span>
		{/if}
	</div>

	<!-- Tabs -->
	<div class="mb-6 flex gap-2 border-b border-gray-200 dark:border-gray-700">
		<button
			type="button"
			class="px-4 py-2 text-sm font-medium transition-colors {activeTab === 'file'
				? 'border-b-2 border-purple-600 text-purple-600 dark:border-purple-400 dark:text-purple-400'
				: 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200'}"
			onclick={() => (activeTab = 'file')}
		>
			<div class="flex items-center gap-2">
				<Upload class="h-4 w-4" />
				File Upload
			</div>
		</button>

		<button
			type="button"
			class="px-4 py-2 text-sm font-medium transition-colors {activeTab === 'yubikey'
				? 'border-b-2 border-purple-600 text-purple-600 dark:border-purple-400 dark:text-purple-400'
				: 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200'}"
			onclick={() => (activeTab = 'yubikey')}
		>
			<div class="flex items-center gap-2">
				<Fingerprint class="h-4 w-4" />
				YubiKey
				{#if !webAuthnSupported}
					<Alert class="h-3 w-3 text-yellow-600" />
				{/if}
			</div>
		</button>
	</div>

	<!-- File Upload Tab -->
	{#if activeTab === 'file'}
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
	{/if}

	<!-- YubiKey Tab -->
	{#if activeTab === 'yubikey'}
		{#if !webAuthnSupported}
			<div
				class="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
			>
				<div class="flex items-start gap-2">
					<Alert class="h-5 w-5 text-red-600 dark:text-red-400" />
					<div>
						<p class="text-sm font-medium text-red-900 dark:text-red-300">WebAuthn Not Supported</p>
						<p class="text-sm text-red-800 dark:text-red-400">
							Your browser doesn't support WebAuthn/FIDO2. Please use Chrome, Firefox, Safari, or
							Edge.
						</p>
					</div>
				</div>
			</div>
		{:else if !keyUploaded}
			<!-- Not Authenticated -->
			<div
				class="rounded-lg border-2 border-blue-300 bg-gradient-to-br from-blue-50 to-indigo-50 p-6 dark:border-blue-700 dark:from-blue-900/30 dark:to-indigo-900/30"
			>
				<div class="mb-4 flex items-center gap-3">
					<div class="rounded-full bg-blue-600 p-3 dark:bg-blue-500">
						<SecurityIcon class="h-8 w-8 text-white" />
					</div>
					<div>
						<h3 class="font-semibold text-gray-900 dark:text-white">Browser-Native Security</h3>
						<p class="text-sm text-gray-600 dark:text-gray-400">
							No installation required • Works on restricted devices
						</p>
					</div>
				</div>

				{#if yubiKeyRegistered}
					<div
						class="mb-4 rounded-lg border border-green-200 bg-green-50 p-3 dark:border-green-800 dark:bg-green-900/20"
					>
						<p class="text-sm font-medium text-green-900 dark:text-green-300">
							✓ YubiKey Registered
						</p>
						<p class="text-xs text-green-700 dark:text-green-400">Ready to authenticate</p>
					</div>
				{:else}
					<div
						class="mb-4 rounded-lg border border-yellow-200 bg-yellow-50 p-3 dark:border-yellow-800 dark:bg-yellow-900/20"
					>
						<p class="text-sm font-medium text-yellow-900 dark:text-yellow-300">
							⚠ First Time Setup
						</p>
						<p class="text-xs text-yellow-700 dark:text-yellow-400">
							You need to register your YubiKey once
						</p>
					</div>
				{/if}

				<button
					type="button"
					class="w-full rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-blue-500 dark:hover:bg-blue-600"
					onclick={authenticateWithYubiKey}
					disabled={isAuthenticating}
				>
					{#if isAuthenticating}
						Authenticating...
					{:else if yubiKeyRegistered}
						Authenticate with YubiKey
					{:else}
						Setup YubiKey
					{/if}
				</button>

				<div
					class="mt-4 rounded-lg border border-blue-100 bg-blue-50 p-3 dark:border-blue-800 dark:bg-blue-900/20"
				>
					<p class="text-xs font-medium text-blue-900 dark:text-blue-300">How it works:</p>
					<ul class="mt-2 space-y-1 text-xs text-blue-800 dark:text-blue-400">
						<li>• First time: Upload your private key & touch YubiKey</li>
						<li>• Your key is encrypted & stored securely in browser</li>
						<li>• Future logins: Just touch your YubiKey</li>
						<li>• No software installation needed!</li>
					</ul>
				</div>
			</div>
		{:else}
			<!-- Authenticated -->
			<div
				class="rounded-lg border-2 border-green-200 bg-green-50 p-6 dark:border-green-800 dark:bg-green-900/20"
			>
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-3">
						<div class="rounded-full bg-green-600 p-2 dark:bg-green-500">
							<CheckCircle class="h-6 w-6 text-white" />
						</div>
						<div>
							<p class="font-medium text-gray-900 dark:text-white">YubiKey Authenticated</p>
							<p class="text-sm text-gray-600 dark:text-gray-400">
								Session active (15 min timeout)
							</p>
						</div>
					</div>
					<button
						type="button"
						class="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
						onclick={onRemoveKey}
					>
						End Session
					</button>
				</div>
			</div>
		{/if}
	{/if}
</div>

<!-- YubiKey Registration Modal -->
{#if showYubiKeyRegistration}
	<div
		class="bg-opacity-50 fixed inset-0 z-50 flex items-center justify-center bg-black p-4"
		role="dialog"
	>
		<div class="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl dark:bg-gray-800">
			<div class="mb-4">
				<h2 class="text-xl font-bold text-gray-900 dark:text-white">Setup YubiKey</h2>
				<p class="text-sm text-gray-600 dark:text-gray-400">
					One-time setup to register your YubiKey
				</p>
			</div>

			<div class="space-y-4">
				<div>
					<label class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
						Upload your private key
					</label>
					<input
						type="file"
						accept=".pem,.key"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						onchange={handleRegistrationKeyUpload}
						disabled={isAuthenticating}
					/>
					{#if registrationKeyFile}
						<p class="mt-1 text-xs text-green-600 dark:text-green-400">
							✓ {registrationKeyFile.name}
						</p>
					{/if}
				</div>

				<div>
					<label class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
						Passphrase (if key is encrypted)
					</label>
					<input
						type="password"
						bind:value={registrationPassphrase}
						placeholder="Leave empty if not encrypted"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						disabled={isAuthenticating}
					/>
				</div>

				<div
					class="rounded-lg border border-blue-200 bg-blue-50 p-3 dark:border-blue-800 dark:bg-blue-900/20"
				>
					<p class="text-xs text-blue-900 dark:text-blue-300">
						<strong>What happens next:</strong><br />
						1. Your private key will be encrypted<br />
						2. You'll be prompted to touch your YubiKey<br />
						3. Encrypted key stored in browser<br />
						4. Original key never stored!
					</p>
				</div>
			</div>

			<div class="mt-6 flex gap-3">
				<button
					type="button"
					class="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
					onclick={cancelYubiKeyRegistration}
					disabled={isAuthenticating}
				>
					Cancel
				</button>
				<button
					type="button"
					class="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-blue-500 dark:hover:bg-blue-600"
					onclick={completeYubiKeyRegistration}
					disabled={!registrationKeyFile || isAuthenticating}
				>
					{isAuthenticating ? 'Setting up...' : 'Register YubiKey'}
				</button>
			</div>
		</div>
	</div>
{/if}
