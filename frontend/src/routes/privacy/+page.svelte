<script lang="ts">
	import { goto } from '$app/navigation';

	const lastUpdate = '10.11.2025';
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
			<h1 class="text-4xl font-bold text-gray-800 dark:text-white">Datenschutzerklärung</h1>
			<p class="mt-2 text-gray-600 dark:text-gray-300">
				Letzte Aktualisierung: {lastUpdate}
			</p>
		</div>

		<!-- Main Content -->
		<div class="space-y-6 rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800">
			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">1. Überblick</h2>
				<p class="text-gray-700 dark:text-gray-300">
					Diese Datenschutzerklärung informiert Sie über die Verarbeitung personenbezogener Daten
					bei der Nutzung von PrioTag. Wir nehmen den Schutz Ihrer persönlichen Daten sehr ernst und
					behandeln diese vertraulich sowie entsprechend der gesetzlichen Datenschutzvorschriften.
				</p>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">
					2. Verantwortliche Stelle
				</h2>
				<p class="text-gray-700 dark:text-gray-300">
					Verantwortlich für die Datenverarbeitung ist die Kindergartenverwaltung. Kontaktdaten
					finden Sie im Impressum.
				</p>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">3. Erhobene Daten</h2>
				<p class="mb-3 text-gray-700 dark:text-gray-300">
					Bei der Registrierung und Nutzung unseres Dienstes erheben wir folgende Daten:
				</p>
				<div class="ml-4 space-y-2 text-gray-700 dark:text-gray-300">
					<p><strong>Registrierungsdaten:</strong></p>
					<ul class="list-disc space-y-1" style="padding-left: 2rem;">
						<li>Loginname (kann ein beliebiges Pseudonym sein)</li>
						<li>Name Ihres Kindes</li>
					</ul>
					<p class="mt-3"><strong>Nutzungsdaten:</strong></p>
					<ul class="ml-6 list-disc space-y-1" style="padding-left: 2rem;">
						<li>Wochentags-Prioritäten für die Betreuungsplanung</li>
						<li>Zeitstempel der Datenerfassung</li>
					</ul>
				</div>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">
					4. Zweck der Datenverarbeitung
				</h2>
				<p class="mb-3 text-gray-700 dark:text-gray-300">
					Ihre Daten werden ausschließlich für folgende Zwecke verwendet:
				</p>
				<ul
					class="ml-6 list-disc space-y-2 text-gray-700 dark:text-gray-300"
					style="padding-left: 2rem;"
				>
					<li>
						<strong>Bedarfsplanung:</strong> Ermittlung der täglichen Prioritäten für die Kindergartenplatzvergabe
					</li>
					<li>
						<strong>Verwaltung:</strong> Kontoverwaltung und Zuordnung der Prioritäten zu Ihrem Kind
					</li>
				</ul>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">
					5. Datenspeicherung und -sicherheit
				</h2>
				<p class="mb-3 text-gray-700 dark:text-gray-300">
					<strong>Speicherort:</strong> Ihre Daten werden in einer PocketBase-Datenbank auf einem Server
					bei Netcup (Deutschland) gespeichert.
				</p>
				<p class="mb-3 text-gray-700 dark:text-gray-300">
					<strong>Zugriffsschutz:</strong> Der Zugriff auf die Datenbank ist durch ein Administrator-Passwort
					geschützt und ausschließlich der Kindergartenverwaltung zugänglich.
				</p>
				<p class="mb-3 text-gray-700 dark:text-gray-300">
					<strong>Verschlüsselung:</strong> Name des Kinds und Prioritätsdaten werden verschlüsselt in
					der Datenbank gespeichert, eine Entschlüsselung Ihrer eigenen Daten ist nur Ihnen mit Ihrem
					Passwort möglich oder der Administration mit einem generellen Schlüssel, der gesondert gesichert
					wird.
				</p>
				<p class="text-gray-700 dark:text-gray-300">
					<strong>Sicherheitsmaßnahmen:</strong> Wir setzen technische und organisatorische
					Sicherheitsmaßnahmen ein, um Ihre Daten gegen zufällige oder vorsätzliche Manipulationen,
					Verlust, Zerstörung oder den Zugriff unberechtigter Personen zu schützen. Eine Umfassende
					Beschreibung findet sich
					<a
						href="https://github.com/DomiDre/priotag/blob/main/ARCHITECTURE.md"
						target="_blank"
						rel="noopener noreferrer"
						class="transition-colors hover:text-blue-600 dark:hover:text-blue-400">hier</a
					>.
				</p>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">
					6. Speicherdauer und Löschung
				</h2>
				<div class="space-y-3 text-gray-700 dark:text-gray-300">
					<p>
						<strong>Accountdaten:</strong> Ihr Account und die zugehörigen Stammdaten (Kindername) werden
						nach 6 Monaten Inaktivität automatisch gelöscht.
					</p>
					<p>
						<strong>Prioritätsdaten:</strong> Die eingegebenen Wochentags-Prioritäten werden automatisch
						2 Monate nach Ablauf des jeweiligen Monats gelöscht, sobald sie nicht mehr für die aktuelle
						Planung benötigt werden. Der aktuelle und der vergangene Monat bleiben dabei verfügbar.
					</p>
					<p>
						<strong>Löschung auf Anfrage:</strong> Sie können jederzeit die sofortige Löschung Ihres
						Accounts und aller zugehörigen Daten beantragen. Die Daten werden unverzüglich gelöscht und
						ein Löschprotokoll entsprechend erstellt.
					</p>
				</div>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">
					7. Pseudonyme Nutzung
				</h2>
				<p class="text-gray-700 dark:text-gray-300">
					Sie können den Dienst mit einem Pseudonym nutzen. Sollte für den Kindesnamen ebenfalls ein
					Pseudonym verwendet werden, sprechen Sie dies einfach mit der Kindergarten Leitung ab.
				</p>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">
					8. Rechtsgrundlage
				</h2>
				<p class="text-gray-700 dark:text-gray-300">
					Die Verarbeitung erfolgt auf Grundlage Ihrer Einwilligung (Art. 6 Abs. 1 lit. a DSGVO)
					sowie zur Erfüllung der Leistungserbringung (Art. 6 Abs. 1 lit. b DSGVO). Sie können Ihre
					Einwilligung jederzeit widerrufen.
				</p>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">9. Ihre Rechte</h2>
				<p class="mb-3 text-gray-700 dark:text-gray-300">
					Sie haben folgende Rechte bezüglich Ihrer personenbezogenen Daten:
				</p>
				<ul
					class="ml-6 list-disc space-y-2 text-gray-700 dark:text-gray-300"
					style="padding-left: 2rem;"
				>
					<li><strong>Auskunftsrecht:</strong> Recht auf Auskunft über Ihre gespeicherten Daten</li>
					<li><strong>Berichtigungsrecht:</strong> Recht auf Korrektur unrichtiger Daten</li>
					<li><strong>Löschungsrecht:</strong> Recht auf Löschung Ihrer Daten</li>
					<li><strong>Einschränkungsrecht:</strong> Recht auf Einschränkung der Verarbeitung</li>
					<li>
						<strong>Datenübertragbarkeit:</strong> Recht auf Erhalt Ihrer Daten in strukturiertem Format
					</li>
					<li><strong>Widerspruchsrecht:</strong> Recht auf Widerspruch gegen die Verarbeitung</li>
					<li><strong>Beschwerderecht:</strong> Recht auf Beschwerde bei der Aufsichtsbehörde</li>
				</ul>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">
					10. Weitergabe von Daten
				</h2>
				<p class="text-gray-700 dark:text-gray-300">
					Ihre Daten werden nicht an Dritte weitergegeben, verkauft oder anderweitig übermittelt, es
					sei denn, dies ist zur Erfüllung vertraglicher Pflichten erforderlich oder gesetzlich
					vorgeschrieben.
				</p>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">
					11. Cookies und Tracking
				</h2>
				<p class="text-gray-700 dark:text-gray-300">
					Diese Website verwendet ausschließlich technisch notwendige Cookies für die
					Authentifizierung und Session-Verwaltung. Es werden keine Tracking-Tools oder
					Analyse-Software von Drittanbietern eingesetzt.
				</p>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">
					12. Änderungen der Datenschutzerklärung
				</h2>
				<p class="text-gray-700 dark:text-gray-300">
					Wir behalten uns vor, diese Datenschutzerklärung bei Bedarf anzupassen, um sie an
					geänderte Rechtslagen oder bei Änderungen des Dienstes sowie der Datenverarbeitung
					anzupassen. Das aktuelle Datum der letzten Aktualisierung finden Sie am Anfang dieser
					Erklärung.
				</p>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">13. Kontakt</h2>
				<p class="text-gray-700 dark:text-gray-300">
					Bei Fragen zum Datenschutz oder zur Ausübung Ihrer Rechte wenden Sie sich bitte an die im
					Impressum angegebenen Kontaktdaten.
				</p>
			</section>
		</div>

		<!-- Footer Navigation -->
		<div class="mt-8 text-center">
			<div class="flex flex-wrap justify-center gap-4 text-sm text-gray-600 dark:text-gray-400">
				<a
					href="https://github.com/domidre/priotag"
					target="_blank"
					rel="noopener noreferrer"
					class="transition-colors hover:text-blue-600 dark:hover:text-blue-400"
				>
					GitHub
				</a>
				<span class="text-gray-400">•</span>
				<a href="/imprint" class="transition-colors hover:text-blue-600 dark:hover:text-blue-400">
					Impressum
				</a>
			</div>
		</div>
	</div>
</div>
