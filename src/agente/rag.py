"""RAG ligero sobre el corpus de documentos (normativa, protocolos, recomendaciones).

Divide cada documento de docs/corpus/ en fragmentos, los indexa con TF-IDF de
scikit-learn y recupera los mas parecidos a una consulta por similitud de coseno.
No requiere red ni claves de API. La interfaz buscar(consulta, k) permite migrar a
embeddings + FAISS sin tocar el resto del agente.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

RAIZ = Path(__file__).resolve().parents[2]
CORPUS = RAIZ / "docs" / "corpus"

SALTO = chr(10)              # salto de linea
SEP_FRAG = chr(10) + chr(10) # separador entre parrafos dentro de un fragmento

def _parrafos(texto: str) -> list[str]:
    """Separa un texto en parrafos (bloques separados por lineas en blanco)."""
    parrafos: list[str] = []
    actual: list[str] = []
    for linea in texto.splitlines():
        if linea.strip() == "":
            if actual:
                parrafos.append(" ".join(actual).strip())
                actual = []
        else:
            actual.append(linea.strip())
    if actual:
        parrafos.append(" ".join(actual).strip())
    return [p for p in parrafos if p]

def _fragmentar(texto: str, fuente: str, max_palabras: int = 90) -> list[dict]:
    """Parte un documento en fragmentos por parrafos, agrupando hasta max_palabras."""
    fragmentos: list[dict] = []
    buffer: list[str] = []
    cuenta = 0
    for p in _parrafos(texto):
        palabras = len(p.split())
        if cuenta + palabras > max_palabras and buffer:
            fragmentos.append({"fuente": fuente, "texto": SEP_FRAG.join(buffer)})
            buffer, cuenta = [], 0
        buffer.append(p)
        cuenta += palabras
    if buffer:
        fragmentos.append({"fuente": fuente, "texto": SEP_FRAG.join(buffer)})
    return fragmentos

@dataclass
class BaseConocimiento:
    fragmentos: list[dict]
    _vectorizador: TfidfVectorizer = field(init=False)
    _matriz: object = field(init=False)

    def __post_init__(self) -> None:
        textos = [f["texto"] for f in self.fragmentos]
        self._vectorizador = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
        self._matriz = self._vectorizador.fit_transform(textos)

    @classmethod
    def desde_corpus(cls, carpeta: Path | None = None) -> "BaseConocimiento":
        carpeta = carpeta or CORPUS
        fragmentos: list[dict] = []
        for ruta in sorted(carpeta.glob("*.md")):
            fragmentos.extend(_fragmentar(ruta.read_text(encoding="utf-8"), ruta.name))
        if not fragmentos:
            raise FileNotFoundError("El corpus esta vacio. Agrega documentos .md a docs/corpus/.")
        return cls(fragmentos)

    def buscar(self, consulta: str, k: int = 3) -> list[dict]:
        """Devuelve los k fragmentos mas relevantes con su fuente y puntaje de similitud."""
        if not consulta.strip():
            return []
        vec = self._vectorizador.transform([consulta])
        sims = cosine_similarity(vec, self._matriz)[0]
        orden = sims.argsort()[::-1][:k]
        resultados = []
        for i in orden:
            if sims[i] <= 0:
                continue
            resultados.append({**self.fragmentos[i], "score": float(sims[i])})
        return resultados
