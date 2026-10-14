// Web Speech API implementation of the voice provider interface
// (see voice.js for the contract). Zero server cost — recognition and
// synthesis both run in the browser. Chrome/Edge/Safari support
// SpeechRecognition; Firefox does not (isSupported().stt will be false
// there, and the UI hides the mic button accordingly).
(function () {
    var RecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
    var recognition = null;
    var listening = false;

    function isSupported() {
        return {
            stt: !!RecognitionCtor,
            tts: !!window.speechSynthesis,
        };
    }

    function startListening(opts) {
        if (!RecognitionCtor) {
            opts.onError && opts.onError('not_supported');
            return;
        }
        if (listening) return;

        recognition = new RecognitionCtor();
        recognition.lang = opts.lang || 'en-US';
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;

        // Chrome often ends a session (on a pause, or when the mic is clicked again)
        // with only an interim transcript and no final result — especially for Urdu
        // and Arabic. Whatever was heard is treated as final when listening stops,
        // so the question is sent without the user having to press Enter.
        var lastHeard = '';
        var finalSent = false;
        function deliverFinal(text) {
            text = (text || '').trim();
            if (finalSent || !text) return;
            finalSent = true;
            opts.onFinal && opts.onFinal(text);
        }

        recognition.onresult = function (event) {
            var interim = '';
            var final = '';
            for (var i = event.resultIndex; i < event.results.length; i++) {
                var transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    final += transcript;
                } else {
                    interim += transcript;
                }
            }
            if (interim) {
                lastHeard = interim;
                if (opts.onInterim) opts.onInterim(interim);
            }
            if (final) deliverFinal(final);
        };

        recognition.onerror = function (event) {
            var messageKey = {
                'not-allowed': 'mic_denied',
                'no-speech': 'no_speech',
                'audio-capture': 'no_mic',
                'network': 'voice_network_error',
            }[event.error] || 'voice_generic_error';
            opts.onError && opts.onError(messageKey);
        };

        recognition.onend = function () {
            listening = false;
            deliverFinal(lastHeard);
            opts.onEnd && opts.onEnd();
        };

        listening = true;
        recognition.start();
    }

    function stopListening() {
        if (recognition && listening) {
            recognition.stop();
        }
    }

    function isListening() {
        return listening;
    }

    function pickVoice(lang) {
        var voices = window.speechSynthesis.getVoices();
        if (!voices.length) return null;
        var exact = voices.find(function (v) { return v.lang === lang; });
        if (exact) return exact;
        var prefix = lang.split('-')[0];
        var byPrefix = voices.find(function (v) { return v.lang.indexOf(prefix) === 0; });
        return byPrefix || null;
    }

    function speak(text, lang) {
        if (!window.speechSynthesis || !text) return;
        window.speechSynthesis.cancel();
        var utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = lang || 'en-US';
        var voice = pickVoice(utterance.lang);
        if (voice) utterance.voice = voice;
        window.speechSynthesis.speak(utterance);
    }

    function stopSpeaking() {
        if (window.speechSynthesis) window.speechSynthesis.cancel();
    }

    registerVoiceProvider('web-speech', {
        isSupported: isSupported,
        startListening: startListening,
        stopListening: stopListening,
        isListening: isListening,
        speak: speak,
        stopSpeaking: stopSpeaking,
    });
})();
