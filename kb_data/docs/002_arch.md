The architecture consists of services: localllama, vector-store (Chroma), text-embedder, kb_service, rag api, and chatbot.
Requests flow through chatbot -> rag api -> vector store & LLM.
