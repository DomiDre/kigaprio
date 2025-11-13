# Instructional Texts Proposal for PrioTag

## Overview
This document proposes detailed instructional texts to help users understand and effectively use the PrioTag childcare priority management system.

---

## 1. Main Priorities Page - Introduction Section

### Location: `/frontend/src/routes/priorities/+page.svelte`
### Placement: Below the Header, above the Legend

### Proposed Text Component: "How It Works" (Collapsible)

**Title:** "So funktioniert PrioTag"

**Content:**
```
Mit PrioTag geben Sie für jeden Wochentag Ihre Betreuungswünsche an:

📋 Grundprinzip:
• Vergeben Sie für jeden Tag (Mo-Fr) eine Priorität von 1-5
• 1 = Betreuung sehr wichtig | 5 = Betreuung weniger wichtig
• Jeder Wochentag muss eine UNTERSCHIEDLICHE Priorität haben
• So signalisieren Sie der Kita, an welchen Tagen Sie Betreuung am dringendsten benötigen

⏰ Wichtige Fristen:
• Prioritäten können nur VOR Wochenbeginn gesetzt werden
• Sobald eine Woche startet (Montag 00:00 Uhr), sind Änderungen nicht mehr möglich
• Planen Sie daher rechtzeitig - am besten für den gesamten Monat

🎯 Ziel:
Die Kita nutzt Ihre Prioritäten, um bei Personalengpässen faire Entscheidungen zu treffen.
Kinder mit höheren Prioritäten (1-2) an einem Tag bekommen bevorzugt einen Platz.
```

---

## 2. Enhanced Legend Component

### Location: `/frontend/src/lib/components/Legend.svelte`
### Enhancement: Add descriptive text for each priority level

### Current vs Proposed:

**Current:** Just shows priority number and label (e.g., "1 - Sehr wichtig")

**Proposed:** Add usage guidance

```
Prioritätsstufen - Was bedeuten sie?

1 - Sehr wichtig (Rot)
   → Betreuung absolut notwendig (z.B. wichtiger Arbeitstermin, Arztbesuch)

2 - Wichtig (Orange)
   → Betreuung sehr erwünscht (z.B. regulärer Arbeitstag)

3 - Normal (Gelb)
   → Betreuung wünschenswert (z.B. Homeoffice-Tag mit Meetings)

4 - Weniger wichtig (Blau)
   → Betreuung hilfreich aber flexibel (z.B. Homeoffice, flexible Arbeitszeit)

5 - Unwichtig (Grau)
   → Betreuung nicht erforderlich (z.B. freier Tag, Urlaub geplant)

💡 Tipp: Nutzen Sie die gesamte Skala! Vergeben Sie nicht nur 1er und 2er.
```

---

## 3. Desktop Grid View - Week Card Help Text

### Location: `/frontend/src/routes/priorities/DesktopGridView.svelte`
### Placement: Tooltip or help icon on first visit

### Proposed Quick Help:

```
❓ Wie bearbeite ich eine Woche?

1. Klicken Sie auf "Bearbeiten" unter der gewünschten Woche
2. Wählen Sie für jeden Tag eine Priorität (1-5)
3. Jeder Tag muss eine andere Priorität haben
4. Ihre Änderungen werden automatisch gespeichert
5. Schließen Sie das Fenster wenn Sie fertig sind

Status-Anzeigen:
✓ Fertig = Alle Tage haben Prioritäten
⚠ Offen = Noch nicht alle Tage priorisiert
🔒 Gesperrt = Woche hat bereits begonnen
```

---

## 4. Edit Modal - Enhanced Instructions

### Location: `/frontend/src/routes/priorities/EditModal.svelte`
### Placement: Add instruction text when modal opens (especially for incomplete weeks)

### Proposed Contextual Help:

**When week is empty/incomplete:**
```
🎯 Prioritäten vergeben

Wählen Sie für jeden Wochentag eine Priorität von 1-5:
• Klicken Sie auf eine Zahl unter dem gewünschten Tag
• Jede Priorität kann nur EINMAL pro Woche vergeben werden
• Wenn Sie eine bereits vergebene Priorität wählen, werden die Tage automatisch getauscht

Fortschritt: [X/5 Tage]

💾 Automatisches Speichern ist aktiviert - Ihre Änderungen werden sofort gesichert.
```

**When week has started (locked):**
```
🔒 Woche bereits gestartet

Diese Woche hat am [Startdatum] begonnen und kann nicht mehr bearbeitet werden.
Sie können Ihre Prioritäten nur noch ansehen.

ℹ️ Tipp: Planen Sie Ihre Prioritäten immer im Voraus, um rechtzeitig Änderungen vornehmen zu können.
```

**When vacation days are present:**
```
🏖️ Abwesenheitstage erkannt

An Tagen mit Urlaub (🏖️), Feiertagen (🎉) oder sonstigen Abwesenheiten (📋)
müssen Sie keine Priorität vergeben. Diese Tage werden automatisch übersprungen.

Sie müssen nur die verbleibenden [X] Tage priorisieren.
```

**Priority button tooltips (enhanced):**
```
When clicking on unused priority:
"Priorität [X] für [Wochentag] setzen"

When clicking on priority used elsewhere:
"Priorität [X] wählen und mit [anderer Wochentag] tauschen"

When hovering over the swap icon (⇄):
"Diese Priorität ist bereits bei [Wochentag] vergeben.
Beim Klicken werden die Prioritäten getauscht."
```

---

## 5. Mobile Week View - Instructions

### Location: `/frontend/src/routes/priorities/MobileWeekView.svelte`
### Placement: Above priority selection buttons

### Proposed Text:

```
Wählen Sie für jeden Tag eine Priorität:

👆 Tippen Sie auf eine Zahl (1-5) unter dem Tag
🔄 Jede Priorität nur einmal pro Woche
💾 Speichern Sie Ihre Auswahl mit dem Button unten

[Aktuelle Woche: X/5 Tage vollständig]
```

---

## 6. First-Time User Onboarding

### Location: New component - `FirstTimeHelp.svelte`
### Trigger: Show on first visit or when user has no priorities set

### Proposed Onboarding Flow:

**Step 1: Welcome**
```
Willkommen bei PrioTag! 👋

PrioTag hilft Ihnen, Ihre Betreuungswünsche für die Kita zu organisieren.

In 3 einfachen Schritten:
1️⃣ Monat auswählen
2️⃣ Prioritäten für jede Woche setzen (1-5)
3️⃣ Fertig! Die Kita sieht Ihre Wünsche

Bereit? Los geht's! →
```

**Step 2: Priority Explanation**
```
Was sind Prioritäten?

Für jeden Wochentag (Mo-Fr) geben Sie an, wie wichtig Ihnen
die Betreuung an diesem Tag ist:

1 = Sehr wichtig (z.B. wichtige Arbeitstermine)
5 = Unwichtig (z.B. freie Tage)

⚠️ WICHTIG: Jede Woche müssen alle 5 Zahlen (1,2,3,4,5)
genau einmal vergeben werden.

Beispiel:
Mo: 1 (Sehr wichtig)
Di: 3 (Normal)
Mi: 2 (Wichtig)
Do: 5 (Unwichtig)
Fr: 4 (Weniger wichtig)

Verstanden! →
```

**Step 3: Deadlines**
```
⏰ Wichtige Fristen

✅ Sie können Prioritäten setzen für:
   • Den aktuellen Monat
   • Die nächsten 2 Monate

⏰ Änderungsfrist:
   Prioritäten können nur VOR Wochenbeginn geändert werden!

🔒 Ab Montag 00:00 Uhr ist die Woche gesperrt.

💡 Unser Tipp:
   Setzen Sie Ihre Prioritäten am besten für den ganzen Monat auf einmal!

Alles klar, loslegen! →
```

---

## 7. Progress Bar - Enhanced Labels

### Location: `/frontend/src/lib/components/ProgressBar.svelte` (if exists) or inline

### Current: Shows percentage only

### Proposed:
```
Ihr Fortschritt für [Monat]

[Progress bar]

[X] von [Y] Wochen vollständig priorisiert

[If incomplete:]
⚠️ Noch [Z] Wochen zu bearbeiten

[If complete:]
✅ Super! Alle Wochen sind priorisiert.
```

---

## 8. Error Messages - User-Friendly Explanations

### Location: Throughout the application

### Proposed Enhanced Error Messages:

**Current:** "Jeder Wochentag muss eine eindeutige Priorität haben"

**Proposed:**
```
❌ Doppelte Priorität erkannt

Sie haben die Priorität [X] mehrmals vergeben.
Jede Zahl (1-5) darf nur einmal pro Woche verwendet werden.

So beheben Sie das:
• Prüfen Sie, welche Tage die gleiche Priorität haben
• Ändern Sie eine der Prioritäten
• Oder löschen Sie die doppelte Priorität
```

**Current:** "Fehler beim Speichern"

**Proposed:**
```
💾 Speichern fehlgeschlagen

Ihre Prioritäten konnten nicht gespeichert werden.

Mögliche Ursachen:
• Keine Internetverbindung
• Sitzung abgelaufen (bitte neu anmelden)
• Server-Probleme

Bitte versuchen Sie es erneut oder kontaktieren Sie den Support.
```

---

## 9. Dashboard - Explanation of Statistics

### Location: `/frontend/src/routes/dashboard/+page.svelte`

### Proposed Help Text for Statistics:

**Add tooltip/info icon for each statistic:**

**Fortschritt:**
```
ℹ️ Fortschritt

Zeigt an, wie viele Tage Sie bereits priorisiert haben.
100% = Alle Wochentage des Monats haben eine Priorität.

Ziel: 100% erreichen, damit die Kita Ihre Wünsche vollständig kennt.
```

**Fokus-Tag:**
```
ℹ️ Fokus-Tag

Der Wochentag, an dem Sie am häufigsten hohe Prioritäten (1-2) vergeben.
Dies ist vermutlich Ihr wichtigster Betreuungstag.

Beispiel: Wenn "Mittwoch" angezeigt wird, brauchen Sie mittwochs
besonders oft Betreuung.
```

**Entspannter Tag:**
```
ℹ️ Entspannter Tag

Der Wochentag, an dem Sie am häufigsten niedrige Prioritäten (4-5) vergeben.
An diesem Tag sind Sie oft flexibler.

Beispiel: Wenn "Freitag" angezeigt wird, können Sie freitags
häufiger auf Betreuung verzichten.
```

---

## 10. Vacation Days - Explanation

### Location: Wherever vacation days are shown

### Proposed Help Text:

```
🏖️ Urlaub & Abwesenheiten

Ihr Arbeitgeber/Ihre Kita kann Urlaubstage, Feiertage und
andere Abwesenheiten im System hinterlegen.

Für diese Tage müssen Sie keine Prioritäten vergeben:

🏖️ Urlaub - Ihre eingetragenen Urlaubstage
🎉 Feiertag - Gesetzliche oder betriebliche Feiertage
📋 Abwesend - Sonstige Abwesenheiten (Fortbildung, etc.)

Diese Tage werden automatisch bei der Berechnung übersprungen.
```

---

## 11. Week Status Indicators - Detailed Explanation

### Location: Add as tooltips or info popover

### Proposed:

**Status: Fertig ✓**
```
✅ Woche vollständig

Alle Wochentage haben eine eindeutige Priorität (1-5).
Ihre Angaben sind gespeichert und für die Kita sichtbar.

Sie können Änderungen vornehmen, solange die Woche noch nicht begonnen hat.
```

**Status: Offen ⚠**
```
⚠️ Woche unvollständig

Diese Woche ist noch nicht vollständig priorisiert.

Bitte vergeben Sie für alle verbleibenden Tage Prioritäten,
damit die Kita Ihre Wünsche berücksichtigen kann.

Fehlende Tage: [Liste]
```

**Status: Gesperrt 🔒**
```
🔒 Woche gesperrt

Diese Woche hat bereits begonnen (Startdatum: [Datum]).
Änderungen sind nicht mehr möglich.

Sie können Ihre Prioritäten nur noch ansehen.

💡 Tipp: Planen Sie rechtzeitig für die kommenden Wochen!
```

---

## 12. FAQ Section (Optional - New Page or Expandable Section)

### Location: New route `/faq` or expandable section on priorities page

### Proposed FAQ:

```
Häufig gestellte Fragen (FAQ)

❓ Warum muss ich überhaupt Prioritäten setzen?
Die Kita nutzt Ihre Prioritäten, um bei Personalengpässen oder
Überbelegung faire Entscheidungen zu treffen. Kinder, deren Eltern
für einen Tag hohe Priorität (1-2) angegeben haben, werden bevorzugt betreut.

❓ Was passiert, wenn ich keine Prioritäten setze?
Ohne Prioritäten kann die Kita Ihre Betreuungswünsche nicht berücksichtigen.
Im Zweifelsfall könnten andere Familien bevorzugt werden.

❓ Warum kann ich nicht alle Tage mit Priorität 1 markieren?
Das System verlangt eine Rangliste. Wenn jeden Tag gleich wichtig wäre,
könnte die Kita keine informierte Entscheidung treffen. Durch die
unterschiedlichen Prioritäten helfen Sie der Kita, die besten Entscheidungen
für alle Familien zu treffen.

❓ Bis wann muss ich Prioritäten setzen?
Spätestens bis Sonntag 23:59 Uhr vor Beginn der jeweiligen Woche.
Ab Montag 00:00 Uhr ist die Woche gesperrt.

❓ Kann ich Prioritäten für mehrere Monate im Voraus setzen?
Ja! Sie können für den aktuellen Monat und bis zu 2 Monate im Voraus planen.
Je früher Sie planen, desto besser kann die Kita disponieren.

❓ Was passiert an Urlaubstagen oder Feiertagen?
Diese Tage werden automatisch erkannt und müssen nicht priorisiert werden.
Sie sehen ein entsprechendes Symbol (🏖️, 🎉 oder 📋) bei diesen Tagen.

❓ Ich habe einen Fehler gemacht. Kann ich Prioritäten ändern?
Ja, solange die Woche noch nicht begonnen hat, können Sie beliebig
oft Änderungen vornehmen. Ihre Änderungen werden automatisch gespeichert.

❓ Was bedeutet "Prioritäten tauschen"?
Wenn Sie eine bereits vergebene Priorität auswählen, tauscht das System
automatisch die Prioritäten der beiden Tage. So müssen Sie nicht manuell
alle Tage neu zuordnen.

❓ Wie sehe ich, ob meine Prioritäten gespeichert wurden?
Im Bearbeitungsfenster sehen Sie einen Speicher-Status:
• "Speichere..." = Wird gerade gespeichert
• "Gespeichert ✓" = Erfolgreich gesichert
• "Fehler" = Problem beim Speichern (bitte erneut versuchen)

❓ An wen kann ich mich bei Problemen wenden?
Bei technischen Problemen oder Fragen wenden Sie sich bitte an:
[Kontaktinformation hier einfügen]
```

---

## 13. Tooltips for Icons and Buttons

### Throughout the application

### Proposed Tooltips:

**Edit Button (when week not started):**
```
"Prioritäten für diese Woche bearbeiten"
```

**Edit Button (when week started) → Changes to "View":**
```
"Prioritäten ansehen (Bearbeitung nicht mehr möglich)"
```

**Lock Icon 🔒:**
```
"Woche bereits gestartet - keine Änderungen mehr möglich"
```

**Vacation Icons:**
```
🏖️: "Urlaubstag - keine Priorität erforderlich"
🎉: "Feiertag - keine Priorität erforderlich"
📋: "Abwesenheit - keine Priorität erforderlich"
```

**Week Status Badges:**
```
"✓ Fertig": "Alle Tage priorisiert"
"Offen": "Noch nicht vollständig - [X/5] Tage priorisiert"
"Gesperrt": "Woche begonnen am [Datum] - schreibgeschützt"
```

**Save Icon in Edit Modal:**
```
"Automatisches Speichern aktiv - Änderungen werden sofort gesichert"
```

---

## 14. Empty State Messages

### When user has no priorities set yet

**Main Priorities Page (no data):**
```
📋 Noch keine Prioritäten gesetzt

Sie haben für [Monat] noch keine Prioritäten angegeben.

So starten Sie:
1. Wählen Sie unten eine Woche aus
2. Klicken Sie auf "Bearbeiten"
3. Setzen Sie Prioritäten für jeden Tag (1-5)
4. Ihre Änderungen werden automatisch gespeichert

💡 Tipp: Beginnen Sie mit der aktuellen Woche und arbeiten
Sie sich dann nach vorne.

[Button: Erste Woche bearbeiten]
```

**Dashboard (no data):**
```
👋 Willkommen bei PrioTag!

Sie haben noch keine Prioritäten gesetzt.

Gehen Sie zu "Prioritäten" und starten Sie mit Ihrer ersten Woche.

[Button: Zu den Prioritäten →]
```

---

## 15. Success Messages

### After completing actions

**Week Completed:**
```
✅ Woche vollständig!

Alle Tage der Woche [Nummer] haben nun eine Priorität.
Ihre Angaben wurden gespeichert.

Möchten Sie die nächste Woche bearbeiten?

[Button: Nächste Woche] [Button: Schließen]
```

**Month Completed:**
```
🎉 Monat vollständig priorisiert!

Super! Sie haben alle Wochen für [Monat] priorisiert.

Die Kita kann nun Ihre Betreuungswünsche optimal berücksichtigen.

[Button: Nächsten Monat planen] [Button: Zum Dashboard]
```

**Changes Saved:**
```
💾 Gespeichert

Ihre Prioritäten wurden erfolgreich aktualisiert.
```

---

## Implementation Priority

### Recommended Implementation Order:

1. **High Priority** (Essential for user understanding):
   - Main page introduction ("How It Works")
   - Enhanced Legend with usage guidance
   - Edit Modal instructions (contextual help)
   - Enhanced error messages

2. **Medium Priority** (Important for UX):
   - First-time user onboarding
   - Empty state messages
   - Week status explanations
   - Tooltips for all interactive elements

3. **Lower Priority** (Nice to have):
   - FAQ section
   - Dashboard statistics explanations
   - Success messages
   - Vacation days detailed explanation

---

## Notes

- All texts are in German (as the application is German-language)
- Texts use familiar "Sie" form (formal address)
- Emoji are used sparingly for visual guidance
- Texts are concise but comprehensive
- Focus on action-oriented language ("Do this", "Click here")
- Each section can be implemented independently
- Consider making longer explanations collapsible/expandable
- Some texts could be hidden after first view (using localStorage)

---

## Next Steps

1. Review and approve these proposed texts
2. Decide on implementation order
3. Create UI components for instruction sections
4. Implement texts in existing components
5. Add persistence for "don't show again" preferences (optional)
6. User testing with actual parents
7. Refinement based on feedback
