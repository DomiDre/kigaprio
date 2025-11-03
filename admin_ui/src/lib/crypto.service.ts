/**
 * Client-Side Decryption Service
 *
 * Provides secure browser-based decryption for encrypted user data using RSA-OAEP
 * and AES-GCM algorithms. This service implements a zero-access encryption architecture
 * where the server stores encrypted data and can only decrypt it either with the users
 * help or send it in encrypted format to the admin who can decrypt locally with the private key.
 *
 * Architecture:
 * - Server: Stores encrypted data, has no access to decryption keys
 * - Admin: Holds private key, performs decryption client-side
 * - Data flow: Server → Encrypted data → Client → Decrypt → View (never sent back)
 *
 * Encryption Scheme:
 * - Data Encryption Keys (DEK): 32-byte AES-256 keys
 * - DEK Protection: RSA-OAEP with SHA-256 hash and MGF1
 * - Data Encryption: AES-GCM with 12-byte nonces and 128-bit authentication tags
 * - Encoding: Base64 encoding of nonce + ciphertext
 */
import type { DecryptedPriorities, DecryptedUserData } from '$lib/dashboard.types';
import forge from 'node-forge';

/**
 * Decryption service for admin dashboard operations.
 *
 * This service handles:
 * - Loading and decrypting passphrase-protected RSA private keys
 * - Decrypting RSA-wrapped Data Encryption Keys (DEKs)
 * - Decrypting AES-GCM encrypted user data and metadata
 *
 * Security Features:
 * - Private keys stored only in memory (non-extractable)
 * - Support for passphrase-protected PKCS#8 private keys
 * - All operations performed client-side
 * - Automatic key cleanup
 */
export class CryptoService {
	/**
	 * Node-forge private key object.
	 * Used for RSA-OAEP decryption operations that require specific padding parameters.
	 */
	private forgePrivateKey: forge.pki.rsa.PrivateKey | null = null;

	/**
	 * Loads and optionally decrypts an RSA private key from a PEM file.
	 *
	 * Supports both encrypted (PKCS#8 EncryptedPrivateKeyInfo) and unencrypted
	 * (PKCS#8 PrivateKeyInfo) private keys. Encrypted keys require a passphrase
	 * for decryption.
	 *
	 * The method performs the following operations:
	 * 1. Reads and parses PEM format
	 * 2. Detects encryption status
	 * 3. Decrypts key with passphrase if encrypted
	 * 4. Imports key into both node-forge and Web Crypto API
	 *
	 * @param file - PEM-encoded private key file
	 * @param passphrase - Optional passphrase for encrypted keys
	 * @throws {Error} If key is encrypted but no passphrase provided (PASSPHRASE_REQUIRED)
	 * @throws {Error} If key format is invalid or passphrase is incorrect
	 *
	 * @example
	 * ```typescript
	 * const keyFile = new File([pemContent], 'private.pem');
	 * await cryptoService.loadPrivateKey(keyFile, 'my-passphrase');
	 * ```
	 */
	async loadPrivateKey(file: File, passphrase?: string): Promise<void> {
		try {
			const pemText = await file.text();
			const isEncrypted = pemText.includes('ENCRYPTED');

			if (isEncrypted && !passphrase) {
				throw new Error('PASSPHRASE_REQUIRED');
			}

			let privateKeyPem: string;

			if (isEncrypted && passphrase) {
				// Decrypt PKCS#8 encrypted private key using node-forge
				const encryptedPrivateKey = forge.pki.encryptedPrivateKeyFromPem(pemText);
				const privateKeyInfo = forge.pki.decryptPrivateKeyInfo(encryptedPrivateKey, passphrase);
				privateKeyPem = forge.pki.privateKeyInfoToPem(privateKeyInfo);
			} else {
				privateKeyPem = pemText;
			}

			// Store forge private key for RSA-OAEP operations
			this.forgePrivateKey = forge.pki.privateKeyFromPem(privateKeyPem);
		} catch (error) {
			console.error('Failed to load private key:', error);
			if (error instanceof Error && error.message === 'PASSPHRASE_REQUIRED') {
				throw new Error('This key is passphrase-protected. Please enter the passphrase.');
			}
			throw new Error('Invalid private key or incorrect passphrase.');
		}
	}

	/**
	 * Checks if a private key has been successfully loaded.
	 *
	 * @returns true if a private key is loaded and ready for use, false otherwise
	 */
	isKeyLoaded(): boolean {
		return this.forgePrivateKey !== null;
	}

	/**
	 * Decrypts a Data Encryption Key (DEK) using RSA-OAEP with SHA-256.
	 *
	 * The DEK is encrypted with the admin's RSA public key during user registration
	 * or data submission. This method reverses that encryption using the corresponding
	 * private key, employing RSA-OAEP with:
	 * - Hash algorithm: SHA-256
	 * - Mask generation function: MGF1 with SHA-256
	 * - Label: empty string (equivalent to Python's None)
	 *
	 * @param adminWrappedDek - Base64-encoded RSA-encrypted DEK
	 * @returns Raw DEK bytes (32 bytes for AES-256-GCM)
	 * @throws {Error} If private key is not loaded
	 * @throws {Error} If decryption fails (wrong key, corrupted data, or invalid padding)
	 *
	 * @example
	 * ```typescript
	 * const dek = await cryptoService.decryptDEK(user.adminWrappedDek);
	 * console.log('DEK length:', dek.length); // Should be 32
	 * ```
	 */
	async decryptDEK(adminWrappedDek: string): Promise<Uint8Array<ArrayBuffer>> {
		if (!this.forgePrivateKey) {
			throw new Error('Private key not loaded. Please upload your private key first.');
		}

		try {
			const encryptedBytes = forge.util.decode64(adminWrappedDek);

			// Decrypt using RSA-OAEP with parameters matching Python's cryptography library
			const decrypted = this.forgePrivateKey.decrypt(encryptedBytes, 'RSA-OAEP', {
				md: forge.md.sha256.create(),
				mgf1: {
					md: forge.md.sha256.create()
				},
				label: '' // Python's label=None is equivalent to empty string
			});

			return Uint8Array.from(decrypted, (c) => c.charCodeAt(0));
		} catch (error) {
			console.error('DEK decryption failed:', error);
			throw new Error(
				'Failed to decrypt DEK. Ensure the private key matches the public key used for encryption.'
			);
		}
	}

	/**
	 * Decrypts data encrypted with AES-256-GCM.
	 *
	 * The encrypted data format from the Python backend is:
	 * base64(nonce[12 bytes] || ciphertext || tag[16 bytes])
	 *
	 * AES-GCM parameters:
	 * - Key size: 256 bits (32 bytes)
	 * - Nonce size: 96 bits (12 bytes)
	 * - Tag size: 128 bits (16 bytes, implicit in ciphertext)
	 *
	 * @param encryptedData - Base64-encoded encrypted data (nonce + ciphertext + tag)
	 * @param dek - Raw Data Encryption Key bytes (32 bytes)
	 * @returns Decrypted plaintext string
	 * @throws {Error} If decryption fails (wrong DEK, corrupted data, or authentication failure)
	 *
	 * @example
	 * ```typescript
	 * const plaintext = await cryptoService.decryptData(encryptedFields, dek);
	 * const data = JSON.parse(plaintext);
	 * ```
	 */
	async decryptData(encryptedData: string, dek: Uint8Array<ArrayBuffer>): Promise<string> {
		try {
			// Decode base64 to get binary data
			const encrypted = Uint8Array.from(atob(encryptedData), (c) => c.charCodeAt(0));

			// Extract nonce (first 12 bytes) and ciphertext with tag (remaining bytes)
			const nonce = encrypted.slice(0, 12);
			const ciphertext = encrypted.slice(12);

			// Import DEK as AES-GCM key
			const aesKey = await window.crypto.subtle.importKey(
				'raw',
				dek,
				{
					name: 'AES-GCM'
				},
				false,
				['decrypt']
			);

			// Decrypt with AES-GCM
			const plaintextBuffer = await window.crypto.subtle.decrypt(
				{
					name: 'AES-GCM',
					iv: nonce,
					tagLength: 128 // 16 bytes, matches Python AESGCM default
				},
				aesKey,
				ciphertext.buffer // Fix linter error: use .buffer to get ArrayBuffer
			);

			// Convert ArrayBuffer to string
			const decoder = new TextDecoder('utf-8');
			return decoder.decode(plaintextBuffer);
		} catch (error) {
			console.error('Data decryption failed:', error);
			throw new Error(
				'Failed to decrypt data. The data may be corrupted or the DEK may be incorrect.'
			);
		}
	}

	/**
	 * Decrypts and parses JSON-encoded encrypted fields.
	 *
	 * This is a convenience method that combines data decryption with JSON parsing.
	 * Used for decrypting structured data such as user information and priority records.
	 *
	 * @param encryptedJson - Base64-encoded encrypted JSON string
	 * @param dek - Raw Data Encryption Key bytes (32 bytes)
	 * @returns Parsed JavaScript object
	 * @throws {Error} If decryption fails or JSON is malformed
	 *
	 * @example
	 * ```typescript
	 * const userData = await cryptoService.decryptFields(
	 *   user.encryptedFields,
	 *   dek
	 * );
	 * console.log(userData.name); // Access decrypted properties
	 * ```
	 */
	async decryptFields(encryptedJson: string, dek: Uint8Array<ArrayBuffer>): Promise<unknown> {
		const jsonString = await this.decryptData(encryptedJson, dek);
		return JSON.parse(jsonString);
	}

	/**
	 * Decrypts user data and/or priority records.
	 *
	 * This high-level method orchestrates the decryption process:
	 * 1. Decrypt the DEK (either from RSA-wrapped DEK or use provided DEK)
	 * 2. Decrypt user fields if provided (name, email, etc.)
	 * 3. Decrypt priority data if provided (weekly schedules)
	 *
	 * All operations are performed client-side; the server does not see decrypted data.
	 *
	 * @param options - Decryption options object
	 * @param options.adminWrappedDek - Base64-encoded RSA-encrypted DEK (required if dek not provided)
	 * @param options.dek - Pre-decrypted DEK as Uint8Array (required if adminWrappedDek not provided)
	 * @param options.userEncryptedFields - Base64-encoded AES-encrypted user information (optional)
	 * @param options.prioritiesEncryptedFields - Base64-encoded AES-encrypted priority data (optional)
	 * @returns Object containing decrypted user data and/or priorities
	 * @throws {Error} If any decryption step fails or if neither adminWrappedDek nor dek provided
	 *
	 * @example
	 * // Regular user with RSA-wrapped DEK
	 * const { userData, priorities } = await cryptoService.decryptUserData({
	 *   adminWrappedDek: user.adminWrappedDek,
	 *   userEncryptedFields: user.userEncryptedFields,
	 *   prioritiesEncryptedFields: user.prioritiesEncryptedFields
	 * });
	 *
	 * @example
	 * // Manual entry with priorities only
	 * const { priorities } = await cryptoService.decryptUserData({
	 *   adminWrappedDek: adminWrappedDek,
	 *   prioritiesEncryptedFields: manualEntry.encrypted_fields
	 * });
	 *
	 * @example
	 * // With pre-decrypted DEK (e.g., from WebAuthn session)
	 * const { userData, priorities } = await cryptoService.decryptUserData({
	 *   dek: sessionDek,
	 *   prioritiesEncryptedFields: entry.encrypted_fields
	 * });
	 */
	async decryptUserData(options: {
		adminWrappedDek?: string;
		dek?: Uint8Array<ArrayBuffer>;
		userEncryptedFields?: string;
		prioritiesEncryptedFields?: string;
	}): Promise<{
		userData?: DecryptedUserData;
		priorities?: DecryptedPriorities;
	}> {
		const {
			adminWrappedDek,
			dek: providedDek,
			userEncryptedFields,
			prioritiesEncryptedFields
		} = options;

		// Validate inputs
		if (!adminWrappedDek && !providedDek) {
			throw new Error('Either adminWrappedDek or dek must be provided');
		}

		if (!userEncryptedFields && !prioritiesEncryptedFields) {
			throw new Error(
				'At least one of userEncryptedFields or prioritiesEncryptedFields must be provided'
			);
		}

		// Step 1: Get the DEK (either decrypt from RSA or use provided)
		const dek = providedDek ?? (await this.decryptDEK(adminWrappedDek!));

		// Step 2: Decrypt user fields if provided
		let userData: DecryptedUserData | undefined;
		if (userEncryptedFields) {
			userData = (await this.decryptFields(userEncryptedFields, dek)) as DecryptedUserData;
		}

		// Step 3: Decrypt priorities if provided
		let priorities: DecryptedPriorities | undefined;
		if (prioritiesEncryptedFields) {
			priorities = (await this.decryptFields(
				prioritiesEncryptedFields,
				dek
			)) as DecryptedPriorities;
		}

		return {
			userData,
			priorities
		};
	}
	/**
	 * Clears the loaded private key from memory.
	 *
	 * This should be called when:
	 * - Admin logs out
	 * - Admin explicitly requests to clear the key
	 * - Session expires
	 *
	 * After calling this method, `loadPrivateKey` must be called again before
	 * performing any decryption operations.
	 *
	 * @example
	 * ```typescript
	 * cryptoService.clearKey();
	 * console.log(cryptoService.isKeyLoaded()); // false
	 * ```
	 */
	clearKey(): void {
		this.forgePrivateKey = null;
	}
}

/**
 * Singleton instance of the CryptoService.
 *
 * Use this instance throughout the application to maintain a single
 * private key context and avoid redundant key loading operations.
 *
 * @example
 * ```typescript
 * import { cryptoService } from '$lib/services/crypto';
 *
 * await cryptoService.loadPrivateKey(keyFile, passphrase);
 * const data = await cryptoService.decryptUserData(...);
 * ```
 */
export const cryptoService = new CryptoService();
