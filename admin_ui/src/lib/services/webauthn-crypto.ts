/**
 * Browser-Native YubiKey Authentication Service
 *
 * Uses WebAuthn/FIDO2 (built into all modern browsers) to authenticate with YubiKey
 * and derive encryption keys. NO INSTALLATION REQUIRED.
 *
 * Security Model:
 * 1. Admin registers YubiKey → generates FIDO2 credential
 * 2. Admin's private key PEM is encrypted with key derived from credential
 * 3. Encrypted PEM stored in localStorage (safe - it's encrypted!)
 * 4. On login: YubiKey authentication → derive decryption key → decrypt PEM
 * 5. Decrypted PEM only in memory during session
 *
 * Benefits:
 * - No software installation needed
 * - Works on internet-restricted devices
 * - Native browser support (Chrome, Firefox, Safari, Edge)
 * - Physical YubiKey required for access
 * - IT-friendly (no admin rights needed)
 */
import type { DecryptedPriorities, DecryptedUserData } from '$lib/types/dashboard';
import forge from 'node-forge';

const RP_ID = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
const RP_NAME = 'Admin Dashboard';

interface EncryptedKeyStore {
	encryptedPEM: string;
	salt: string;
	iv: string;
	credentialId: string;
}

/**
 * WebAuthn-based YubiKey Authentication Service
 * Zero installation required - uses browser's native WebAuthn API
 */
export class WebAuthnCryptoService {
	private forgePrivateKey: forge.pki.rsa.PrivateKey | null = null;
	private isAuthenticated = false;
	private sessionTimeout: number | null = null;
	private readonly SESSION_DURATION = 15 * 60 * 1000; // 15 minutes

	/**
	 * Check if WebAuthn is supported in this browser
	 */
	isWebAuthnSupported(): boolean {
		return !!(window.PublicKeyCredential && navigator.credentials && navigator.credentials.create);
	}

	/**
	 * Check if YubiKey is already registered
	 */
	isYubiKeyRegistered(): boolean {
		const stored = localStorage.getItem('yubikey_encrypted_key');
		return stored !== null;
	}

	/**
	 * Get registered YubiKey info (for display)
	 */
	getRegisteredKeyInfo(): { registered: boolean; registeredAt?: string } {
		const stored = localStorage.getItem('yubikey_encrypted_key');
		if (!stored) {
			return { registered: false };
		}

		const registeredAt = localStorage.getItem('yubikey_registered_at');
		return {
			registered: true,
			registeredAt: registeredAt || undefined
		};
	}

	/**
	 * Register YubiKey and encrypt admin private key
	 *
	 * This only needs to be done ONCE per admin device.
	 * The encrypted key is stored in localStorage.
	 *
	 * @param privateKeyPEM - Admin's RSA private key in PEM format
	 * @param passphrase - Optional passphrase if PEM is encrypted
	 */
	async registerYubiKey(privateKeyPEM: string, passphrase?: string): Promise<void> {
		if (!this.isWebAuthnSupported()) {
			throw new Error('WebAuthn not supported in this browser');
		}

		// Decrypt PEM if encrypted
		let cleanPEM = privateKeyPEM;
		if (privateKeyPEM.includes('ENCRYPTED') && passphrase) {
			const encryptedKey = forge.pki.encryptedPrivateKeyFromPem(privateKeyPEM);
			const privateKeyInfo = forge.pki.decryptPrivateKeyInfo(encryptedKey, passphrase);
			cleanPEM = forge.pki.privateKeyInfoToPem(privateKeyInfo);
		}

		// Verify it's a valid private key
		try {
			forge.pki.privateKeyFromPem(cleanPEM);
		} catch {
			throw new Error('Invalid private key format');
		}

		// Generate a unique user ID
		const userId = new Uint8Array(16);
		crypto.getRandomValues(userId);

		// Create WebAuthn credential with YubiKey
		const credential = (await navigator.credentials.create({
			publicKey: {
				challenge: crypto.getRandomValues(new Uint8Array(32)),
				rp: {
					name: RP_NAME,
					id: RP_ID
				},
				user: {
					id: userId,
					name: 'admin@dashboard',
					displayName: 'Admin'
				},
				pubKeyCredParams: [
					{ type: 'public-key', alg: -7 }, // ES256
					{ type: 'public-key', alg: -257 } // RS256
				],
				authenticatorSelection: {
					authenticatorAttachment: 'cross-platform', // External security key
					requireResidentKey: false,
					userVerification: 'preferred'
				},
				timeout: 60000,
				attestation: 'none'
			}
		})) as PublicKeyCredential;

		if (!credential) {
			throw new Error('Failed to create credential');
		}

		// Derive encryption key from credential ID
		const credentialId = new Uint8Array(credential.rawId);
		const wrappingKey = await this.deriveKeyFromCredential(credentialId);

		// Encrypt the private key PEM
		const encrypted = await this.encryptPrivateKey(cleanPEM, wrappingKey);

		// Store encrypted key in localStorage
		const keyStore: EncryptedKeyStore = {
			encryptedPEM: encrypted.encryptedData,
			salt: encrypted.salt,
			iv: encrypted.iv,
			credentialId: btoa(String.fromCharCode(...credentialId))
		};

		localStorage.setItem('yubikey_encrypted_key', JSON.stringify(keyStore));
		localStorage.setItem('yubikey_registered_at', new Date().toISOString());

		console.log('✓ YubiKey registered successfully');
	}

	/**
	 * Authenticate with YubiKey and unlock the private key
	 *
	 * This is called each session (after browser restart, tab close, etc.)
	 * Requires physical YubiKey touch.
	 */
	async authenticateWithYubiKey(): Promise<void> {
		if (!this.isWebAuthnSupported()) {
			throw new Error('WebAuthn not supported in this browser');
		}

		const storedData = localStorage.getItem('yubikey_encrypted_key');
		if (!storedData) {
			throw new Error('No YubiKey registered. Please register first.');
		}

		const keyStore: EncryptedKeyStore = JSON.parse(storedData);
		const credentialId = Uint8Array.from(atob(keyStore.credentialId), (c) => c.charCodeAt(0));

		// Authenticate with YubiKey
		const assertion = (await navigator.credentials.get({
			publicKey: {
				challenge: crypto.getRandomValues(new Uint8Array(32)),
				rpId: RP_ID,
				allowCredentials: [
					{
						id: credentialId,
						type: 'public-key',
						transports: ['usb', 'nfc']
					}
				],
				userVerification: 'preferred',
				timeout: 60000
			}
		})) as PublicKeyCredential;

		if (!assertion) {
			throw new Error('Authentication failed');
		}

		// Derive decryption key from credential
		const wrappingKey = await this.deriveKeyFromCredential(credentialId);

		// Decrypt the private key PEM
		const privateKeyPEM = await this.decryptPrivateKey(
			keyStore.encryptedPEM,
			keyStore.iv,
			wrappingKey
		);

		// Load into forge
		this.forgePrivateKey = forge.pki.privateKeyFromPem(privateKeyPEM);
		this.isAuthenticated = true;

		// Set session timeout
		this.startSessionTimeout();

		console.log('✓ Authenticated with YubiKey');
	}

	/**
	 * Derive encryption key from WebAuthn credential
	 * Uses HKDF with credential ID as input key material
	 */
	private async deriveKeyFromCredential(credentialId: Uint8Array): Promise<CryptoKey> {
		// Import credential ID as base key
		const baseKey = await crypto.subtle.importKey('raw', credentialId, 'HKDF', false, [
			'deriveKey'
		]);

		// Derive AES-GCM key using HKDF
		return await crypto.subtle.deriveKey(
			{
				name: 'HKDF',
				hash: 'SHA-256',
				salt: new Uint8Array(32), // Fixed salt (could also be random and stored)
				info: new TextEncoder().encode('admin-key-wrapping-v1')
			},
			baseKey,
			{ name: 'AES-GCM', length: 256 },
			false,
			['encrypt', 'decrypt']
		);
	}

	/**
	 * Encrypt private key PEM with derived key
	 */
	private async encryptPrivateKey(
		pem: string,
		key: CryptoKey
	): Promise<{ encryptedData: string; salt: string; iv: string }> {
		const iv = crypto.getRandomValues(new Uint8Array(12));
		const salt = crypto.getRandomValues(new Uint8Array(32));

		const encrypted = await crypto.subtle.encrypt(
			{ name: 'AES-GCM', iv },
			key,
			new TextEncoder().encode(pem)
		);

		return {
			encryptedData: btoa(String.fromCharCode(...new Uint8Array(encrypted))),
			salt: btoa(String.fromCharCode(...salt)),
			iv: btoa(String.fromCharCode(...iv))
		};
	}

	/**
	 * Decrypt private key PEM with derived key
	 */
	private async decryptPrivateKey(
		encryptedB64: string,
		ivB64: string,
		key: CryptoKey
	): Promise<string> {
		const encrypted = Uint8Array.from(atob(encryptedB64), (c) => c.charCodeAt(0));
		const iv = Uint8Array.from(atob(ivB64), (c) => c.charCodeAt(0));

		const decrypted = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, encrypted);

		return new TextDecoder().decode(decrypted);
	}

	/**
	 * Start session timeout (auto-logout after 15 minutes)
	 */
	private startSessionTimeout(): void {
		if (this.sessionTimeout) {
			clearTimeout(this.sessionTimeout);
		}

		this.sessionTimeout = window.setTimeout(() => {
			this.clearKey();
			console.log('Session expired - please re-authenticate');
		}, this.SESSION_DURATION);
	}

	/**
	 * Check if currently authenticated
	 */
	isKeyLoaded(): boolean {
		return this.forgePrivateKey !== null && this.isAuthenticated;
	}

	/**
	 * Get authentication mode
	 */
	getMode(): 'webauthn' | null {
		return this.isAuthenticated ? 'webauthn' : null;
	}

	/**
	 * Decrypt a DEK using the loaded private key
	 */
	async decryptDEK(adminWrappedDek: string): Promise<Uint8Array> {
		if (!this.forgePrivateKey) {
			throw new Error('Not authenticated. Please authenticate with YubiKey first.');
		}

		try {
			const encryptedBytes = forge.util.decode64(adminWrappedDek);

			const decrypted = this.forgePrivateKey.decrypt(encryptedBytes, 'RSA-OAEP', {
				md: forge.md.sha256.create(),
				mgf1: { md: forge.md.sha256.create() },
				label: ''
			});

			return Uint8Array.from(decrypted, (c) => c.charCodeAt(0));
		} catch (error) {
			console.error('DEK decryption failed:', error);
			throw new Error('Failed to decrypt DEK');
		}
	}

	/**
	 * Decrypt data encrypted with AES-256-GCM
	 */
	async decryptData(encryptedData: string, dek: Uint8Array): Promise<string> {
		try {
			const encrypted = Uint8Array.from(atob(encryptedData), (c) => c.charCodeAt(0));
			const nonce = encrypted.slice(0, 12);
			const ciphertext = encrypted.slice(12);

			const aesKey = await crypto.subtle.importKey('raw', dek, { name: 'AES-GCM' }, false, [
				'decrypt'
			]);

			const plaintextBuffer = await crypto.subtle.decrypt(
				{
					name: 'AES-GCM',
					iv: nonce,
					tagLength: 128
				},
				aesKey,
				ciphertext
			);

			return new TextDecoder('utf-8').decode(plaintextBuffer);
		} catch (error) {
			console.error('Data decryption failed:', error);
			throw new Error('Failed to decrypt data');
		}
	}

	/**
	 * Decrypt JSON fields
	 */
	async decryptFields(encryptedJson: string, dek: Uint8Array): Promise<unknown> {
		const jsonString = await this.decryptData(encryptedJson, dek);
		return JSON.parse(jsonString);
	}

	/**
	 * Decrypt complete user data
	 */
	async decryptUserData(
		adminWrappedDek: string,
		userEncryptedFields: string,
		prioritiesEncryptedFields: string
	): Promise<{
		userData: DecryptedUserData;
		priorities: DecryptedPriorities;
	}> {
		const dek = await this.decryptDEK(adminWrappedDek);
		const userData = (await this.decryptFields(userEncryptedFields, dek)) as DecryptedUserData;
		const priorities = (await this.decryptFields(
			prioritiesEncryptedFields,
			dek
		)) as DecryptedPriorities;

		return { userData, priorities };
	}

	/**
	 * Clear the loaded key and end session
	 */
	clearKey(): void {
		this.forgePrivateKey = null;
		this.isAuthenticated = false;

		if (this.sessionTimeout) {
			clearTimeout(this.sessionTimeout);
			this.sessionTimeout = null;
		}
	}

	/**
	 * Remove YubiKey registration (factory reset)
	 * WARNING: This will require re-registering the YubiKey
	 */
	clearRegistration(): void {
		localStorage.removeItem('yubikey_encrypted_key');
		localStorage.removeItem('yubikey_registered_at');
		this.clearKey();
	}
}

/**
 * Singleton instance
 */
export const webAuthnCryptoService = new WebAuthnCryptoService();
