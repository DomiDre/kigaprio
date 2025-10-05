<script lang="ts">
	import { goto } from '$app/navigation';
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
			<h1 class="text-4xl font-bold text-gray-800 dark:text-white">Impressum</h1>
		</div>

		<!-- Main Content -->
		<div class="space-y-6 rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800">
			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">
					Angaben gemäß § 5 TMG
				</h2>
				<div class="space-y-1 text-gray-700 dark:text-gray-300">
					<p class="font-semibold">[Name des Kindergartens / der Einrichtung]</p>
					<p>[Straße und Hausnummer]</p>
					<p>[PLZ und Ort]</p>
				</div>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">Vertreten durch</h2>
				<p class="text-gray-700 dark:text-gray-300">
					[Name der verantwortlichen Person / Leitung]<br />
					[Position / Funktion]
				</p>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">Kontakt</h2>
				<div class="space-y-1 text-gray-700 dark:text-gray-300">
					<p><strong>Telefon:</strong> [Telefonnummer]</p>
					<p>
						<strong>E-Mail:</strong>
						<a href="mailto:[email]" class="text-blue-600 hover:text-blue-700 dark:text-blue-400"
							>[E-Mail-Adresse]</a
						>
					</p>
				</div>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">Träger</h2>
				<p class="text-gray-700 dark:text-gray-300">
					[Name des Trägers]<br />
					[Rechtsform, falls zutreffend]
				</p>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">Umsatzsteuer-ID</h2>
				<p class="text-gray-700 dark:text-gray-300">
					Umsatzsteuer-Identifikationsnummer gemäß § 27 a Umsatzsteuergesetz:<br />
					[USt-IdNr., falls vorhanden]
				</p>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">Aufsichtsbehörde</h2>
				<p class="text-gray-700 dark:text-gray-300">
					[Name der zuständigen Aufsichtsbehörde]<br />
					[Adresse der Aufsichtsbehörde]
				</p>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">
					Verantwortlich für den Inhalt nach § 55 Abs. 2 RStV
				</h2>
				<p class="text-gray-700 dark:text-gray-300">
					[Name der inhaltlich verantwortlichen Person]<br />
					[Adresse]
				</p>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">
					Haftung für Inhalte
				</h2>
				<p class="text-gray-700 dark:text-gray-300">
					Als Diensteanbieter sind wir gemäß § 7 Abs.1 TMG für eigene Inhalte auf diesen Seiten nach
					den allgemeinen Gesetzen verantwortlich. Nach §§ 8 bis 10 TMG sind wir als Diensteanbieter
					jedoch nicht verpflichtet, übermittelte oder gespeicherte fremde Informationen zu
					überwachen oder nach Umständen zu forschen, die auf eine rechtswidrige Tätigkeit
					hinweisen.
				</p>
				<p class="mt-3 text-gray-700 dark:text-gray-300">
					Verpflichtungen zur Entfernung oder Sperrung der Nutzung von Informationen nach den
					allgemeinen Gesetzen bleiben hiervon unberührt. Eine diesbezügliche Haftung ist jedoch
					erst ab dem Zeitpunkt der Kenntnis einer konkreten Rechtsverletzung möglich. Bei
					Bekanntwerden von entsprechenden Rechtsverletzungen werden wir diese Inhalte umgehend
					entfernen.
				</p>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">Haftung für Links</h2>
				<p class="text-gray-700 dark:text-gray-300">
					Unser Angebot enthält Links zu externen Websites Dritter, auf deren Inhalte wir keinen
					Einfluss haben. Deshalb können wir für diese fremden Inhalte auch keine Gewähr übernehmen.
					Für die Inhalte der verlinkten Seiten ist stets der jeweilige Anbieter oder Betreiber der
					Seiten verantwortlich. Die verlinkten Seiten wurden zum Zeitpunkt der Verlinkung auf
					mögliche Rechtsverstöße überprüft. Rechtswidrige Inhalte waren zum Zeitpunkt der
					Verlinkung nicht erkennbar.
				</p>
				<p class="mt-3 text-gray-700 dark:text-gray-300">
					Eine permanente inhaltliche Kontrolle der verlinkten Seiten ist jedoch ohne konkrete
					Anhaltspunkte einer Rechtsverletzung nicht zumutbar. Bei Bekanntwerden von
					Rechtsverletzungen werden wir derartige Links umgehend entfernen.
				</p>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">Urheberrecht</h2>
				<p class="text-gray-700 dark:text-gray-300">
					Die durch die Seitenbetreiber erstellten Inhalte und Werke auf diesen Seiten unterliegen
					dem deutschen Urheberrecht. Die Vervielfältigung, Bearbeitung, Verbreitung und jede Art
					der Verwertung außerhalb der Grenzen des Urheberrechtes bedürfen der schriftlichen
					Zustimmung des jeweiligen Autors bzw. Erstellers. Downloads und Kopien dieser Seite sind
					nur für den privaten, nicht kommerziellen Gebrauch gestattet.
				</p>
				<p class="mt-3 text-gray-700 dark:text-gray-300">
					Soweit die Inhalte auf dieser Seite nicht vom Betreiber erstellt wurden, werden die
					Urheberrechte Dritter beachtet. Insbesondere werden Inhalte Dritter als solche
					gekennzeichnet. Sollten Sie trotzdem auf eine Urheberrechtsverletzung aufmerksam werden,
					bitten wir um einen entsprechenden Hinweis. Bei Bekanntwerden von Rechtsverletzungen
					werden wir derartige Inhalte umgehend entfernen.
				</p>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">
					Technische Umsetzung
				</h2>
				<div class="space-y-1 text-gray-700 dark:text-gray-300">
					<p><strong>Entwicklung:</strong>Dominique Dresen</p>
					<p>
						<strong>GitHub:</strong>
						<a
							href="https://github.com/domidre/kigaprio"
							target="_blank"
							rel="noopener noreferrer"
							class="text-blue-600 hover:text-blue-700 dark:text-blue-400"
							>github.com/domidre/kigaprio</a
						>
					</p>
					<p><strong>Hosting:</strong> netcup GmbH, Deutschland</p>
				</div>
			</section>

			<section>
				<h2 class="mb-3 text-2xl font-semibold text-gray-800 dark:text-white">Streitschlichtung</h2>
				<p class="text-gray-700 dark:text-gray-300">
					Die Europäische Kommission stellt eine Plattform zur Online-Streitbeilegung (OS) bereit:
					<a
						href="https://ec.europa.eu/consumers/odr/"
						target="_blank"
						rel="noopener noreferrer"
						class="text-blue-600 hover:text-blue-700 dark:text-blue-400"
					>
						https://ec.europa.eu/consumers/odr/
					</a>. Unsere E-Mail-Adresse finden Sie oben im Impressum.
				</p>
				<p class="mt-3 text-gray-700 dark:text-gray-300">
					Wir sind nicht bereit oder verpflichtet, an Streitbeilegungsverfahren vor einer
					Verbraucherschlichtungsstelle teilzunehmen.
				</p>
			</section>
		</div>

		<!-- Footer Navigation -->
		<div class="mt-8 text-center">
			<div class="flex flex-wrap justify-center gap-4 text-sm text-gray-600 dark:text-gray-400">
				<a
					href="https://github.com/domidre/kigaprio"
					target="_blank"
					rel="noopener noreferrer"
					class="transition-colors hover:text-blue-600 dark:hover:text-blue-400"
				>
					GitHub
				</a>
				<span class="text-gray-400">•</span>
				<a href="/privacy" class="transition-colors hover:text-blue-600 dark:hover:text-blue-400">
					Datenschutz
				</a>
			</div>
		</div>
	</div>
</div>

