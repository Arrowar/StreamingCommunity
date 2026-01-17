#!/usr/bin/env python3
from curl_cffi import requests as _requests

NAVEGADORES_FUNCIONALES = [
    'chrome99', 'chrome100', 'chrome101', 'chrome104',
    'chrome107', 'chrome110', 'chrome116', 'edge99', 'edge101'
]
NAVEGADOR_RECOMENDADO = "chrome99"

# Cambia la classe SmartRequests in una classe NON statica
class SmartRequestsWrapper:
    # Mantiene un riferimento all'oggetto originale per la composizione
    _original_requests = _requests

    def __init__(self):
        # I metodi get, post, ecc. saranno gestiti dalla classe stessa
        pass

    @staticmethod
    def _validar(impersonate):
        if impersonate and impersonate not in NAVEGADORES_FUNCIONALES:
            raise ValueError(f"Navegador non verificato. Usa: {NAVEGADORES_FUNCIONALES}")
    
    # Metodi personalizzati
    def get(self, url, impersonate=None, **kwargs):
        if impersonate:
            self._validar(impersonate)
        else:
            impersonate = NAVEGADOR_RECOMENDATO
        # Chiama il metodo originale sull'oggetto originale
        return self._original_requests.get(url, impersonate=impersonate, **kwargs)
    
    def post(self, url, impersonate=None, **kwargs):
        if impersonate:
            self._validar(impersonate)
        else:
            impersonate = NAVEGADOR_RECOMENDATO
        return self._original_requests.post(url, impersonate=impersonate, **kwargs)
    
    def listar_funcionales(self):
        return NAVEGADORES_FUNCIONALES

    # NUOVA AGGIUNTA CRITICA: Gestore degli attributi mancanti
    def __getattr__(self, name):
        """
        Intercetta le richieste per attributi (metodi/proprietà) non definiti in SmartRequestsWrapper
        e li reindirizza all'oggetto _requests originale.
        """
        # Se l'attributo richiesto non è definito qui (es. head, Session, options),
        # lo cerchiamo e lo restituiamo dall'oggetto originale.
        if hasattr(self._original_requests, name):
            return getattr(self._original_requests, name)
        
        # Se non è trovato da nessuna parte, solleva AttributeError
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


# Rimpiazza l'oggetto requests nel tuo modulo con un'istanza del wrapper
requests = SmartRequestsWrapper()

# Esempio d'uso:
# requests.get(...)  -> Chiama il tuo metodo personalizzato
# requests.Session() -> Chiama Session dall'oggetto originale tramite __getattr__
# requests.head(...) -> Chiama head dall'oggetto originale tramite __getattr__