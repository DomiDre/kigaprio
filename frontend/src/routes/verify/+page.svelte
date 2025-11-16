<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	interface BuildInfo {
		version: string;
		commit: string;
		build_date: string;
		source_url: string;
	}

	let buildInfo: BuildInfo | null = null;
	let loading = true;
	let error: string | null = null;

	onMount(async () => {
		try {
			const response = await fetch('/api/v1/build-info');
			if (!response.ok) {
				throw new Error('Failed to fetch build information');
			}
			buildInfo = await response.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error occurred';
		} finally {
			loading = false;
		}
	});

	function copyToClipboard(text: string) {
		navigator.clipboard.writeText(text);
	}
</script>

<div
	class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
>
	<div class="container mx-auto max-w-4xl px-4 py-8">
		<!-- Header -->
		<div class="mb-8">
			<button
				on:click={() => goto('/')}
				class="mb-4 text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
			>
				← Zurück zur Startseite
			</button>
			<h1 class="text-4xl font-bold text-gray-800 dark:text-white">Build Verification</h1>
			<p class="mt-2 text-gray-600 dark:text-gray-300">
				Verify that this deployment matches the open source code
			</p>
		</div>

		<!-- Security Warning Banner -->
		<div class="mb-6 rounded-2xl bg-red-50 border-2 border-red-200 p-6 dark:bg-red-900/20 dark:border-red-800">
			<div class="flex items-start gap-3">
				<span class="text-2xl">⚠️</span>
				<div>
					<h2 class="text-xl font-bold text-red-900 dark:text-red-200 mb-2">
						Security Warning
					</h2>
					<p class="text-red-800 dark:text-red-300 mb-3">
						<strong>This page shows metadata that can be forged.</strong> A malicious actor could create a fake image
						with falsified build information while running different code.
					</p>
					<p class="text-red-800 dark:text-red-300">
						<strong>For TRUE cryptographic verification</strong>, you must verify the Docker image digest
						externally. See the <a href="#true-verification" class="underline font-semibold">True Verification</a> section below.
					</p>
				</div>
			</div>
		</div>

		<!-- Main Content -->
		<div class="space-y-6 rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800">
			{#if loading}
				<div class="flex justify-center py-8">
					<div class="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"></div>
				</div>
			{:else if error}
				<div class="rounded-lg bg-red-50 p-4 dark:bg-red-900/20">
					<p class="text-red-700 dark:text-red-400">Error: {error}</p>
				</div>
			{:else if buildInfo}
				<!-- Build Information -->
				<section>
					<h2 class="mb-4 text-2xl font-semibold text-gray-800 dark:text-white">
						Current Build Information (Informational Only)
					</h2>
					<div class="mb-4 rounded-lg bg-yellow-50 p-3 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
						<p class="text-sm text-yellow-900 dark:text-yellow-200">
							⚠️ This data is embedded in the image and can be faked. Use for transparency, not security.
						</p>
					</div>
					<div class="space-y-3">
						<div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-700">
							<div class="mb-1 text-sm font-medium text-gray-600 dark:text-gray-400">Version</div>
							<div class="font-mono text-gray-800 dark:text-white">{buildInfo.version}</div>
						</div>

						<div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-700">
							<div class="mb-1 flex items-center justify-between">
								<span class="text-sm font-medium text-gray-600 dark:text-gray-400">Commit SHA</span>
								<button
									on:click={() => copyToClipboard(buildInfo.commit)}
									class="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400"
								>
									Copy
								</button>
							</div>
							<div class="font-mono text-sm text-gray-800 dark:text-white break-all">
								{buildInfo.commit}
							</div>
						</div>

						<div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-700">
							<div class="mb-1 text-sm font-medium text-gray-600 dark:text-gray-400">Build Date</div>
							<div class="font-mono text-gray-800 dark:text-white">{buildInfo.build_date}</div>
						</div>

						<div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-700">
							<div class="mb-1 text-sm font-medium text-gray-600 dark:text-gray-400">Source Code</div>
							<a
								href={buildInfo.source_url}
								target="_blank"
								rel="noopener noreferrer"
								class="font-mono text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 break-all"
							>
								{buildInfo.source_url}
							</a>
						</div>
					</div>
				</section>

				<!-- True Verification Section -->
				<section id="true-verification">
					<h2 class="mb-4 text-2xl font-semibold text-red-700 dark:text-red-400">
						🔒 True Cryptographic Verification
					</h2>
					<div class="rounded-lg bg-blue-50 p-4 dark:bg-blue-900/20 border-2 border-blue-200 dark:border-blue-800 mb-4">
						<p class="font-semibold text-blue-900 dark:text-blue-200 mb-2">
							This is the ONLY way to verify what's actually running.
						</p>
						<p class="text-blue-800 dark:text-blue-300 text-sm">
							The build information above can be forged. To truly verify this deployment, you must
							check the actual Docker image digest being used and verify its cryptographic signature.
						</p>
					</div>

					<div class="space-y-4">
						<div>
							<h3 class="mb-2 text-lg font-medium text-gray-700 dark:text-gray-300">
								Step 1: Get the Running Image Digest
							</h3>
							<p class="mb-2 text-gray-600 dark:text-gray-400">
								You need server access or trust in the operator. SSH into the server and run:
							</p>
							<div class="rounded-lg bg-gray-900 p-4 font-mono text-sm text-green-400">
								<pre class="whitespace-pre-wrap break-all"># Find the running container
docker ps | grep priotag-backend

# Get the actual image digest
docker inspect &lt;container-id&gt; --format='{{.Image}}'
# Output: sha256:abc123def456...</pre>
							</div>
						</div>

						<div>
							<h3 class="mb-2 text-lg font-medium text-gray-700 dark:text-gray-300">
								Step 2: Verify the Image Signature
							</h3>
							<p class="mb-2 text-gray-600 dark:text-gray-400">
								Using the digest from Step 1, verify it was built by GitHub Actions:
							</p>
							<div class="rounded-lg bg-gray-900 p-4 font-mono text-sm text-green-400">
								<pre class="whitespace-pre-wrap break-all"># Install cosign first (see below)
cosign verify \
  --certificate-identity-regexp='https://github.com/DomiDre/priotag' \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  ghcr.io/domidre/priotag-backend@sha256:&lt;digest-from-step-1&gt;</pre>
							</div>
							<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
								✅ If successful, this PROVES the image was built by our public GitHub Actions workflow.
							</p>
						</div>

						<div>
							<h3 class="mb-2 text-lg font-medium text-gray-700 dark:text-gray-300">
								Step 3: Verify the Source Commit
							</h3>
							<p class="mb-2 text-gray-600 dark:text-gray-400">
								Check which commit was used to build this image:
							</p>
							<div class="rounded-lg bg-gray-900 p-4 font-mono text-sm text-green-400">
								<pre class="whitespace-pre-wrap break-all">cosign verify-attestation \
  --type slsaprovenance \
  --certificate-identity-regexp='https://github.com/DomiDre/priotag' \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  ghcr.io/domidre/priotag-backend@sha256:&lt;digest&gt; \
  | jq -r '.payload' | base64 -d | jq</pre>
							</div>
							<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
								Compare the commit SHA with the one shown above. If they match AND the signature verified,
								you have cryptographic proof.
							</p>
						</div>

						<div class="rounded-lg bg-orange-50 p-4 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800">
							<h4 class="font-semibold text-orange-900 dark:text-orange-200 mb-2">
								Why You Need Server Access
							</h4>
							<p class="text-sm text-orange-800 dark:text-orange-300">
								A malicious actor controls the server and can fake any data served by the application
								(including this page). The ONLY trustworthy verification is checking the actual Docker
								image digest from outside the application, then verifying that digest's signature with Cosign.
							</p>
						</div>
					</div>
				</section>

				<!-- Additional Verification Instructions -->
				<section>
					<h2 class="mb-4 text-2xl font-semibold text-gray-800 dark:text-white">
						Additional Verification Methods
					</h2>
					<div class="space-y-4">
						<div>
							<h3 class="mb-2 text-lg font-medium text-gray-700 dark:text-gray-300">
								1. Install Cosign
							</h3>
							<p class="mb-2 text-gray-600 dark:text-gray-400">
								Required for signature verification:
							</p>
							<div class="rounded-lg bg-gray-900 p-4 font-mono text-sm text-green-400">
								<pre class="whitespace-pre-wrap break-all"># Linux
curl -O -L "https://github.com/sigstore/cosign/releases/latest/download/cosign-linux-amd64"
sudo mv cosign-linux-amd64 /usr/local/bin/cosign
sudo chmod +x /usr/local/bin/cosign

# macOS
brew install cosign

# Windows
choco install cosign</pre>
							</div>
						</div>

						<div>
							<h3 class="mb-2 text-lg font-medium text-gray-700 dark:text-gray-300">
								2. Compare Source Code (Informational)
							</h3>
							<p class="mb-2 text-gray-600 dark:text-gray-400">
								Click the source code link above to view the code. Note: This commit SHA could be faked,
								so only trust it after verifying the image signature (see True Verification above).
							</p>
						</div>

						<div>
							<h3 class="mb-2 text-lg font-medium text-gray-700 dark:text-gray-300">
								3. Check GitHub Actions
							</h3>
							<p class="mb-2 text-gray-600 dark:text-gray-400">
								All builds are performed in public GitHub Actions workflows. You can verify:
							</p>
							<ul class="list-inside list-disc space-y-1 text-gray-600 dark:text-gray-400">
								<li>The workflow runs in a clean environment each time</li>
								<li>All build steps are logged and publicly visible</li>
								<li>Images are built from the exact commit shown above</li>
								<li>SBOM (Software Bill of Materials) is generated for each build</li>
							</ul>
							<a
								href="https://github.com/DomiDre/priotag/actions"
								target="_blank"
								rel="noopener noreferrer"
								class="mt-2 inline-block text-blue-600 hover:text-blue-700 dark:text-blue-400"
							>
								View GitHub Actions →
							</a>
						</div>

						<div>
							<h3 class="mb-2 text-lg font-medium text-gray-700 dark:text-gray-300">
								4. Review SBOM
							</h3>
							<p class="mb-2 text-gray-600 dark:text-gray-400">
								Software Bill of Materials (SBOM) files list all dependencies in our images. You can download
								them from GitHub releases to see exactly what packages are included.
							</p>
							<a
								href="https://github.com/DomiDre/priotag/releases"
								target="_blank"
								rel="noopener noreferrer"
								class="text-blue-600 hover:text-blue-700 dark:text-blue-400"
							>
								View Releases →
							</a>
						</div>
					</div>
				</section>

				<!-- Transparency Section -->
				<section>
					<h2 class="mb-4 text-2xl font-semibold text-gray-800 dark:text-white">
						Our Commitment to Transparency
					</h2>
					<div class="space-y-3 text-gray-600 dark:text-gray-400">
						<p>
							<strong class="text-gray-800 dark:text-white">Open Source:</strong> All code is publicly available
							on GitHub under an open source license.
						</p>
						<p>
							<strong class="text-gray-800 dark:text-white">Verifiable Builds:</strong> Every deployment is
							built from a specific Git commit that you can verify.
						</p>
						<p>
							<strong class="text-gray-800 dark:text-white">Signed Images:</strong> Docker images are
							cryptographically signed to prevent tampering.
						</p>
						<p>
							<strong class="text-gray-800 dark:text-white">Public CI/CD:</strong> All builds happen in
							public GitHub Actions workflows that anyone can audit.
						</p>
						<p>
							<strong class="text-gray-800 dark:text-white">SBOM Included:</strong> Complete list of all
							software dependencies is available for each release.
						</p>
					</div>
				</section>
			{/if}
		</div>
	</div>
</div>
