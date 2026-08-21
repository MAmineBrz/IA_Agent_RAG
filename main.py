import logging
import os
import datetime

from fastapi import FastAPI
from dotenv import load_dotenv
from openai import OpenAI
import inngest
import inngest.fast_api

from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage
from custom_types import RAGChunkAndSrc, RAGUpsertResult, RAGSearchResult, RAGQueryResult


load_dotenv()

inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
    serializer=inngest.PydanticSerializer(),
)


@inngest_client.create_function(
    fn_id="RAG: Ingest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf"),
)
async def rag_ingest_pdf(ctx: inngest.Context):
    def _load(ctx: inngest.Context) -> RAGChunkAndSrc:
        pdf_path = ctx.event.data["pdf_path"]
        source_id = ctx.event.data.get("source_id", pdf_path)
        chunks = load_and_chunk_pdf(pdf_path)
        return RAGChunkAndSrc(chunk=chunks, source_id=source_id)

    def _upsert(ctx: inngest.Context, data: RAGChunkAndSrc) -> RAGUpsertResult:
        chunks = data.chunk
        source_id = data.source_id
        vecs = embed_texts(chunks)
        ids = [f"{source_id}:{i}" for i in range(len(chunks))]
        payloads = [{"source_id": source_id, "text": chunks[i]} for i in range(len(chunks))]
        QdrantStorage().upsert(ids, vecs, payloads)
        return RAGUpsertResult(ingested=len(chunks))

    chunks_and_src = await ctx.step.run(
        "load-and-chunk",
        lambda: _load(ctx),
        output_type=RAGChunkAndSrc,
    )

    ingested = await ctx.step.run(
        "embed-and-upsert",
        lambda: _upsert(ctx, chunks_and_src),
        output_type=RAGUpsertResult,
    )

    return ingested.model_dump()


@inngest_client.create_function(
    fn_id="RAG: Query",
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ia"),
)
async def rag_query_pdf_ia(ctx: inngest.Context):
    def _search(question: str, top_k: int = 5) -> RAGSearchResult:
        query_vec = embed_texts([question])[0]
        store = QdrantStorage()
        found = store.search(query_vec, top_k)
        return RAGSearchResult(contexts=found["contexts"], sources=found["sources"])

    def _generate(question: str, context_block: str) -> str:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        user_content = (
            f"Question: {question}\n\n"
            f"Context:\n{context_block}\n\n"
            f"Answer the question based on the context above. "
            f"If the context does not contain the answer, say 'I don't know'."
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1024,
            temperature=0.2,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_content},
            ],
        )
        return response.choices[0].message.content.strip()

    question = ctx.event.data["question"]
    top_k = int(ctx.event.data.get("top_k", 5))

    found = await ctx.step.run(
        "embed-and-search",
        lambda: _search(question, top_k),
        output_type=RAGSearchResult,
    )

    context_block = "\n\n".join(found.contexts)
    answer = await ctx.step.run(
        "llm-answer",
        lambda: _generate(question, context_block),
    )

    return {
        "answer": answer,
        "sources": found.sources,
        "num_contexts": len(found.contexts),
    }


app = FastAPI()
inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf, rag_query_pdf_ia])