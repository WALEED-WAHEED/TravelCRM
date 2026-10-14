// Voice provider registry + factory. This is the ONLY file chat.html's
// inline script is allowed to depend on for voice — it never touches
// window.SpeechRecognition/speechSynthesis directly. Swapping to a
// different engine later (e.g. a server-side Gemini-audio provider) means
// writing one new file that calls registerVoiceProvider('gemini-audio', {...})
// with the same method shapes below, then changing VOICE_PROVIDER in
// settings.py — nothing here or in chat.html has to change.
//
// Provider interface (a plain object registered by name):
//   isSupported() -> { stt: bool, tts: bool }
//   startListening({ lang, onInterim(text), onFinal(text), onError(message), onEnd() })
//   stopListening()
//   isListening() -> bool
//   speak(text, lang)
//   stopSpeaking()
//
// `lang` is always a BCP-47 tag (e.g. "en-US"), never the short app
// language code — LANGUAGE_TAGS below is the one place that mapping lives.

window.VOICE_PROVIDERS = {};

function registerVoiceProvider(name, provider) {
    window.VOICE_PROVIDERS[name] = provider;
}

function getVoiceProvider(name) {
    return window.VOICE_PROVIDERS[name] || null;
}

// Short app language code (assistant/models.py LANGUAGE_CHOICES) -> BCP-47
// tag Web Speech understands. Extend this alongside LANGUAGE_CHOICES if a
// language is added there.
var VOICE_LANGUAGE_TAGS = {
    en: 'en-US', ar: 'ar-SA', ur: 'ur-PK', fr: 'fr-FR', es: 'es-ES', hi: 'hi-IN', de: 'de-DE',
};

function voiceLanguageTag(shortCode) {
    return VOICE_LANGUAGE_TAGS[shortCode] || VOICE_LANGUAGE_TAGS.en;
}
