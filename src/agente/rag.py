"""RAG sobre el corpus de documentos oficiales (normativa, protocolo POECA, SIATA).

Cada documento de docs/corpus/ se parte por secciones (encabezados ##). Cada
fragmento lleva el título del documento, la sección y la fuente, para que el
agente cite de dónde sale cada dato.

Recuperación:
- Principal: embeddings multilingües (paraphrase-multilingual-MiniLM-L12-v2,
  ejecutado con fastembed/ONNX, sin GPU ni PyTorch) indexados en FAISS. Los
  vectores se normalizan, así que el producto interno es la similitud del coseno.
- Búsqueda híbrida: el ranking de embeddings se combina con uno de TF-IDF
  mediante Reciprocal Rank Fusion (k=60). Los embeddings capturan el significado;
  TF-IDF rescata términos exactos como siglas ("ND", "POECA") o colores ("naranja"),
  que el modelo pequeño de embeddings maneja mal.
- Respaldo: solo TF-IDF, si el modelo de embeddings no se puede cargar.

El índice se guarda en index/ y solo se reconstruye cuando cambia el corpus.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
CORPUS = RAIZ / "docs" / "corpus"
INDICE = RAIZ / "index"
MODELO_EMBEDDINGS = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MAX_PALABRAS = 160
K_RRF = 60


def _metadatos(texto: str, archivo: str) -> tuple[str, str]:
    """Título (primer encabezado #) y línea de fuente ("Fuente: ...") del documento."""
    titulo = next((l[2:].strip() for l in texto.splitlines() if l.startswith("# ")), archivo)
    fuente = next((l.strip() for l in texto.splitlines() if l.startswith("Fuente:")), "")
    return titulo, fuente


def _url(fuente: str) -> str:
    m = re.search(r"https?://\S+", fuente)
    return m.group(0).rstrip(".,") if m else ""


def fragmentar(texto: str, archivo: str) -> list[dict]:
    """Parte un documento por secciones ##; una sección larga se divide por párrafos."""
    titulo, fuente = _metadatos(texto, archivo)
    secciones: list[tuple[str, str]] = []
    actual, cuerpo = "Introducción", []
    for linea in texto.splitlines():
        if linea.startswith("## "):
            if cuerpo:
                secciones.append((actual, "\n".join(cuerpo)))
            actual, cuerpo = linea[3:].strip(), []
        elif not linea.startswith("# ") and not linea.startswith("Fuente:"):
            cuerpo.append(linea)
    if cuerpo:
        secciones.append((actual, "\n".join(cuerpo)))

    fragmentos = []
    for seccion, contenido in secciones:
        parrafos = [p.strip() for p in re.split(r"\n\s*\n", contenido) if p.strip()]
        bloque: list[str] = []
        for p in parrafos:
            if bloque and len(" ".join(bloque + [p]).split()) > MAX_PALABRAS:
                fragmentos.append(_fragmento(archivo, titulo, fuente, seccion, bloque))
                bloque = []
            bloque.append(p)
        if bloque:
            fragmentos.append(_fragmento(archivo, titulo, fuente, seccion, bloque))
    return fragmentos


def _fragmento(archivo, titulo, fuente, seccion, parrafos) -> dict:
    texto = "\n\n".join(parrafos)
    return {
        "fuente": archivo,
        "documento": titulo,
        "seccion": seccion,
        "url": _url(fuente),
        "texto": texto,
        # Lo que se indexa incluye el título y la sección para dar contexto al vector.
        "texto_indexado": f"{titulo}. {seccion}. {texto}",
    }


def cargar_corpus(carpeta: Path | None = None) -> list[dict]:
    carpeta = carpeta or CORPUS
    fragmentos: list[dict] = []
    for ruta in sorted(carpeta.glob("*.md")):
        fragmentos.extend(fragmentar(ruta.read_text(encoding="utf-8"), ruta.name))
    if not fragmentos:
        raise FileNotFoundError("El corpus está vacío. Agrega documentos .md a docs/corpus/.")
    return fragmentos


@dataclass
class BaseConocimiento:
    fragmentos: list[dict]
    backend: str = "embeddings"
    _modelo: object = field(init=False, default=None)
    _indice: object = field(init=False, default=None)
    _tfidf: object = field(init=False, default=None)
    _matriz: object = field(init=False, default=None)

    def __post_init__(self) -> None:
        self._construir_tfidf()
        if self.backend == "embeddings":
            try:
                self._construir_embeddings()
                self.backend = "hibrido"
            except Exception as e:  # noqa: BLE001
                print(f"[rag] Embeddings no disponibles ({e}); se usa solo TF-IDF.")
                self.backend = "tfidf"

    @classmethod
    def desde_corpus(cls, carpeta: Path | None = None, backend: str = "embeddings") -> "BaseConocimiento":
        return cls(cargar_corpus(carpeta), backend=backend)

    # --- embeddings + FAISS -------------------------------------------------
    def _construir_embeddings(self) -> None:
        import faiss
        from fastembed import TextEmbedding

        textos = [f["texto_indexado"] for f in self.fragmentos]
        huella = hashlib.sha256(
            (MODELO_EMBEDDINGS + "\n".join(textos)).encode("utf-8")
        ).hexdigest()[:16]
        self._modelo = TextEmbedding(MODELO_EMBEDDINGS, cache_dir=str(INDICE / "modelo"))

        ruta_indice = INDICE / f"faiss_{huella}.index"
        if ruta_indice.exists():
            self._indice = faiss.read_index(str(ruta_indice))
            return
        vectores = self._vectorizar(textos)
        self._indice = faiss.IndexFlatIP(vectores.shape[1])
        self._indice.add(vectores)
        INDICE.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._indice, str(ruta_indice))
        (INDICE / f"faiss_{huella}.json").write_text(
            json.dumps([{k: f[k] for k in ("fuente", "seccion")} for f in self.fragmentos],
                       ensure_ascii=False, indent=1),
            encoding="utf-8",
        )

    def _vectorizar(self, textos: list[str]) -> np.ndarray:
        v = np.array(list(self._modelo.embed(textos)), dtype="float32")
        return v / np.linalg.norm(v, axis=1, keepdims=True)

    # --- TF-IDF (respaldo) ---------------------------------------------------
    def _construir_tfidf(self) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._tfidf = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
        self._matriz = self._tfidf.fit_transform([f["texto_indexado"] for f in self.fragmentos])

    def _ranking_tfidf(self, consulta: str) -> list[int]:
        from sklearn.metrics.pairwise import cosine_similarity

        sims = cosine_similarity(self._tfidf.transform([consulta]), self._matriz)[0]
        return [int(i) for i in sims.argsort()[::-1] if sims[i] > 0]

    def _ranking_embeddings(self, consulta: str) -> list[int]:
        _, idx = self._indice.search(self._vectorizar([consulta]), len(self.fragmentos))
        return [int(i) for i in idx[0] if i >= 0]

    def buscar(self, consulta: str, k: int = 3) -> list[dict]:
        """Devuelve los k fragmentos más relevantes, con su puntaje de fusión."""
        if not consulta or not consulta.strip():
            return []
        rankings = [self._ranking_tfidf(consulta)]
        if self.backend == "hibrido":
            rankings.append(self._ranking_embeddings(consulta))
        puntaje: dict[int, float] = {}
        for ranking in rankings:
            for pos, i in enumerate(ranking, start=1):
                puntaje[i] = puntaje.get(i, 0.0) + 1.0 / (K_RRF + pos)
        mejores = sorted(puntaje, key=puntaje.get, reverse=True)[:k]
        return [{**self.fragmentos[i], "score": round(puntaje[i], 5)} for i in mejores]

if __name__ == "__main__":
    import sys

    kb = BaseConocimiento.desde_corpus()
    print(f"{len(kb.fragmentos)} fragmentos, backend: {kb.backend}")
    for consulta in sys.argv[1:] or ["límite diario de PM2.5 en Colombia"]:
        print(f"\n> {consulta}")
        for r in kb.buscar(consulta, k=3):
            print(f"  {r['score']:.3f}  {r['fuente']} / {r['seccion']}")
