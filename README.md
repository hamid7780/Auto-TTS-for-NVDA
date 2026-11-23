# Auto TTS for NVDA

Auto TTS is an add-on for the NVDA screen reader. It looks at the text NVDA is about to read, works out which language each part is written in, and reads each part with the voice you picked for that language. If you read Urdu, Arabic and English in the same page, message or document, you no longer have to change voices by hand.

**[Download the latest release](https://github.com/hamid7780/Auto-TTS-for-NVDA/releases/latest)**

Needs NVDA 2023.3 or newer, 32-bit or 64-bit. Last tested with NVDA 2026.3.1. Free software under the GPL-2.0 license.

## What it does

NVDA normally reads everything with one voice. When a text mixes languages, that voice reads some of it badly. With Auto TTS you create a profile for each language. A profile holds a synthesizer, a voice, and optionally its own speed, pitch and volume. While NVDA reads, Auto TTS splits the text by language and sends each piece to the matching profile.

- Every language can use a different synthesizer and voice, for example Windows OneCore for English and another synthesizer for Urdu.
- Language detection runs on your computer. Auto TTS does not send your text anywhere.
- Urdu and Arabic are told apart, including Quranic text with tashkeel.
- Numbers and math can be read in a language you choose.
- It includes a language lock, per application exclusions, and settings backup.

## Install

1. Download the `.nvda-addon` file from the [latest release](https://github.com/hamid7780/Auto-TTS-for-NVDA/releases/latest).
2. Open the file and confirm the installation. Restart NVDA when it asks.
3. After the restart, a welcome message offers to open the settings.

## Set up your languages

Open the NVDA menu, then Preferences, Settings, and choose **Auto TTS for NVDA**. You can also press NVDA+Alt+A from anywhere.

1. Choose **Add Profile**.
2. Pick a language from the list, or type a language code such as `ur`, `ar` or `en-GB`.
3. Choose the **TTS Engine** and the **Voice** for that language.
4. Choose **Test Speech** to hear the voice.
5. Repeat for every language you read.
6. Select your main language in the profile list and choose **Set as Default**.
7. Press NVDA+Ctrl+S, select **Auto TTS for NVDA** as your synthesizer, and press OK.

The default language is used for text whose language is not clear, and in excluded applications.

## Keyboard shortcuts

| Shortcut | What it does |
| --- | --- |
| NVDA+Alt+A | Open the Auto TTS settings |
| NVDA+Shift+L | Turn automatic language switching on or off |
| NVDA+Alt+L | Lock Auto TTS to one language profile, or unlock it |
| NVDA+Ctrl+T | Say whether Auto TTS is on and whether a language is locked |

You can change these under Preferences, Input gestures, in the Auto TTS category. NVDA also uses NVDA+Ctrl+T to switch the braille tether, and add-on shortcuts take priority, so braille display users should assign a different key to the status command.

## Settings

| Setting | What it does |
| --- | --- |
| Enable Automatic Language Switching | Turns detection on or off. The same as NVDA+Shift+L. |
| Use Unicode-based language detection | Chooses the language from the writing system of the text. |
| Smart same-script language detection | Tells apart languages that share a script, such as English and French, using the bundled FastText model. Works offline. |
| Smart Arabic/Urdu automatic separation | Separates Urdu from Arabic, and sends Quranic text with tashkeel to Arabic. |
| Protect math symbols and formulas | Keeps math from triggering a voice change. |
| Math reading language | The language used to read math. |
| Document language tags | Either detect from the text even when the document tag is wrong, or trust the language tags a document provides. |
| Switching granularity | Switch on every word, on every sentence or clause, or on every new line. |
| Numbers reading voice / language | Read numbers in the current language, the default language, or always in English, Urdu, Arabic or Hindi. |
| Mobile phone number pattern | Read mobile numbers as spaced digits, grouped clusters, or normal text. |
| Date reading format | Read dates with month names (e.g. 20 November 2026), as digits, or with synthesizer default. |
| Other numbers format | Read general numbers with synthesizer default, as individual spaced digits, or grouped in clusters. |
| Large numbers format | Read large numbers in default/Western system (Millions, Billions) or Indian numbering system (Lakh, Crore). |
| Diagnostic activity logging | Record speech events and synthesizer actions to Auto TTS log.txt in Documents. |
| Excluded Applications | Programs where Auto TTS never switches voices. |
| Configured Language Profiles | Add, edit and remove profiles, set the default, or reset everything. |
| Export Settings and Import Settings | Save or restore all profiles and options as a `.autotts` or `.json` file. |

### Profile options

Each language profile has these options.

- **Language**: a language from the list, or any language code such as `sw-KE` or `fil-PH`.
- **TTS Engine** and **Voice**: the synthesizer and voice for this language. Any synthesizer that NVDA lists can be used.
- **Send language information to synthesizer**: tells the synthesizer which language it is reading, which some voices need.
- **Enable this language profile for automatic switching**: turn it off to keep a profile without using it.
- **NVDA Profile**: take the speed, pitch and volume of the synthesizer from one of your NVDA configuration profiles, or leave it on none to use the synthesizer's normal settings.
- **Use custom rate, pitch and volume**: give this language its own speed, pitch and volume.
- **Test Speech**: speaks a sample sentence in this language.

## How language is detected

Detection works in three steps.

1. **Writing system.** Each script is linked to a language. By default Latin letters go to English, Arabic script to Urdu, Devanagari to Hindi, Cyrillic to Russian, and so on.
2. **Arabic script.** Urdu, Arabic, Persian, Pashto and Sindhi share one script. Auto TTS looks at the whole sentence for letters only one of them uses, such as ے and ڑ for Urdu, ة for Arabic, ځ for Pashto or ڪ for Sindhi, plus Quranic marks and tashkeel. When no letter settles it, the FastText model decides. Inside an Urdu sentence, a quoted Arabic phrase such as بسم الله الرحمن الرحيم gets the Arabic voice, while a single borrowed word stays with the sentence. Urdu typed on an Arabic keyboard (ي and ك) is still read as Urdu.
3. **Languages that share a script.** For text in the same script, such as English, French and German, a small offline FastText model picks the language. Regional shared scripts like Perso-Arabic (Urdu, Arabic, Persian), Devanagari (Hindi, Marathi, Nepali), and Bengali/Assamese use character heuristics and dedicated n-gram language models.

Text in a language that has no enabled profile is read with the default voice.

NVDA's own words, such as "link", "button" or "checked", are never given to the FastText model, so a role or state name is not read with a voice for another language.

### Symbols and honorific signs

Punctuation inside a sentence stays with the words around it and is never read aloud by name. When a line, or a character you move to or type, holds only symbols, Auto TTS reads each symbol by name in the language of its script: a line with only `؟` is read as "سوالیہ نشان" with your Urdu voice, even when your default language is English.

Arabic-script honorific signs and word ligatures, such as `ؑ` (علیہ السلام), `ؓ` (رضی اللہ عنہ) and `ﷺ` (صلی اللہ علیہ وسلم), stand for whole words, so they are always read as those words with every synthesizer, alone or inside a sentence. Urdu and Shahmukhi Punjabi profiles use the Urdu spelling; other Arabic-script languages use the Arabic spelling.

The add-on also gives NVDA a symbol dictionary for Urdu and Punjabi, named **Auto TTS Urdu and Punjabi symbols**, so these names are used wherever NVDA itself reads symbols in those languages. It needs NVDA 2024.4 or newer; on older versions Auto TTS still reads the symbols itself.

## Excluded applications

In an excluded application, Auto TTS does not switch voices and reads everything with your default language. These programs are excluded by default: Visual Studio Code, Command Prompt, PowerShell, Windows Terminal, Visual Studio and Notepad++. Open **Excluded Applications** in the settings to add or remove programs. Type the program name, for example `notepad.exe`. The `.exe` ending is added if you leave it out.

## Language lock

Press NVDA+Alt+L to read everything with one language profile, whatever the text says. Press it again to go back to automatic switching. You can also choose **Language lock** in NVDA's synthesizer settings ring or in NVDA's Voice settings. The lock is cleared when NVDA restarts.

## Synthesizer settings ring

In NVDA's synthesizer settings ring, the Voice setting moves between your language profiles. Rate, pitch and volume change the speed, pitch and volume used for the selected profile, and a change is heard from the next thing NVDA says.

## Backup and where settings are kept

Use **Export Settings** to back up your profiles or to copy them to another computer, and **Import Settings** to restore them. Settings are stored in the NVDA user configuration folder, usually `%APPDATA%\nvda`, in `autoTTS.json`. A copy named `autoTTS.json.bak` is kept next to it.

## If something does not work

1. Check that **Auto TTS for NVDA** is the selected synthesizer (NVDA+Ctrl+S).
2. Press NVDA+Ctrl+T to hear whether Auto TTS is on or locked to a language.
3. Open the profile for the language and check that it is enabled and that **Test Speech** works.
4. Check that the program you are using is not in the excluded list.
5. Check that the voice named in the profile is still installed.

If you report a problem, include the NVDA log. Open it with NVDA+F1. Lines from this add-on start with `AutoTTS:`. For a report about speech starting late, set the logging level to Debug in NVDA's General settings, reproduce the problem, and include the lines that say `took`. You can also open the Auto TTS log folder from settings.

## Known limitations

- Urdu written in English letters (Roman Urdu) is detected as English. Urdu voices cannot read English letters as Urdu, so detecting it would not help until the text is also converted to Urdu script.
- Sindhi or Pashto that uses none of its own letters can only be told apart from Urdu by the FastText model, which needs a few words of text.
- A single short word in a shared script is not guessed, to avoid constant voice changes. A clear change of script, such as Urdu to English, still switches on that word.
- Online synthesizers need an internet connection, and Auto TTS cannot make them faster.

## Privacy

Language detection runs on your computer and the add-on has no network code. If you choose an online synthesizer for a language, that synthesizer sends the text it reads to its own service. That is controlled by the synthesizer, not by Auto TTS.

## Report a problem or contribute

Report bugs and suggestions on the [issue tracker](https://github.com/hamid7780/Auto-TTS-for-NVDA/issues). Developers can find build and test steps in the [development notes](https://github.com/hamid7780/Auto-TTS-for-NVDA/blob/main/docs/DEVELOPMENT.md).

## Credits and licenses

Auto TTS is written by Raja Hamid and released under the [GPL-2.0 license](https://github.com/hamid7780/Auto-TTS-for-NVDA/blob/main/LICENSE.txt). It bundles the fastText prediction runtime (MIT license) and the fastText language identification model, which is licensed separately under CC BY-SA 3.0. See the [third-party notices](https://github.com/hamid7780/Auto-TTS-for-NVDA/blob/main/THIRD_PARTY_NOTICES.txt).

<div dir="rtl" lang="ur">

## اردو میں مختصر تعارف

Auto TTS for NVDA ایک ایڈ آن ہے جو پڑھے جانے والے متن کی زبان خود پہچانتا ہے اور ہر زبان کے لیے آپ کی منتخب کردہ آواز استعمال کرتا ہے۔ اردو، عربی اور انگریزی ملی ہوئی عبارت پڑھتے وقت آواز خود بدل جاتی ہے۔

ہر زبان کے لیے آپ الگ سنتھیسائزر، آواز، رفتار، پچ اور والیوم چن سکتے ہیں۔ زبان کی پہچان آپ کے اپنے کمپیوٹر پر ہوتی ہے۔ البتہ آن لائن سنتھیسائزر کو انٹرنیٹ درکار ہو سکتا ہے۔

انسٹال کرنے کے لیے ریلیز کے صفحے سے `.nvda-addon` فائل ڈاؤن لوڈ کریں، اسے کھولیں اور NVDA دوبارہ شروع کریں۔ پھر NVDA+Alt+A دبا کر ہر زبان کے لیے پروفائل بنائیں، اور NVDA+Ctrl+S سے Auto TTS for NVDA کو اپنا سنتھیسائزر منتخب کریں۔

</div>
