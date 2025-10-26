import numpy as np
from rapidfuzz import fuzz
from FlagEmbedding import FlagReranker

# 초기화 (Cross-Encoder 기반 Re-ranker)
reranker = FlagReranker('BAAI/bge-reranker-large', use_fp16=True)

# 하이브리드 점수 계산 (Dense + Sparse)
def hybrid_score(query, doc, dense_score, w_vec=0.7, w_kw=0.3):
    """의미 유사도와 키워드 일치율을 혼합"""
    kw_score = fuzz.partial_ratio(query.lower(), doc.lower()) / 100.0
    return w_vec * dense_score + w_kw * kw_score

# 최종 검색 함수
def hybrid_retrieve(query, retriever, topk=10, rerank=True):
    """retriever는 Chroma나 FAISS와 호환되는 search 함수"""
    dense_results = retriever.similarity_search_with_score(query, k=topk*2)
    
    # hybrid score 계산
    hybrid_results = []
    for doc, dense_score in dense_results:
        score = hybrid_score(query, doc.page_content, dense_score)
        hybrid_results.append((doc, score))

    # 점수로 1차 정렬
    hybrid_results.sort(key=lambda x: x[1], reverse=True)
    top_docs = hybrid_results[:topk]

    # Re-ranker 적용 (Cross-Encoder)
    if rerank:
        pairs = [(query, d.page_content) for d, _ in top_docs]
        scores = reranker.compute_score(pairs, batch_size=8)
        reranked = sorted(
            [(d, float(s)) for (d, _), s in zip(top_docs, scores)],
            key=lambda x: x[1], reverse=True
        )
        return reranked

    return top_docs
