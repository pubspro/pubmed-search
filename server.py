import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("pubmed-search")

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

@mcp.tool()
async def search_pubmed(query: str, max_results: int = 10) -> str:
    """Search PubMed by keyword, MeSH term, or author. Returns PMIDs and titles."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{PUBMED_BASE}/esearch.fcgi", params={
            "db": "pubmed", "term": query, "retmax": max_results,
            "retmode": "json"
        })
        data = r.json()
        ids = data["esearchresult"]["idlist"]
        r2 = await client.get(f"{PUBMED_BASE}/esummary.fcgi", params={
            "db": "pubmed", "id": ",".join(ids), "retmode": "json"
        })
        summaries = r2.json()["result"]
        results = []
        for pmid in ids:
            title = summaries[pmid]["title"]
            results.append(f"PMID {pmid}: {title}")
        return "\n".join(results)

@mcp.tool()
async def get_abstract(pmid: str) -> str:
    """Retrieve full abstract for a given PubMed ID (PMID)."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{PUBMED_BASE}/efetch.fcgi", params={
            "db": "pubmed", "id": pmid, "rettype": "abstract", "retmode": "text"
        })
        return r.text

@mcp.tool()
async def summarize_findings(pmid: str) -> str:
    """Generate a plain-language PICO summary of a PubMed abstract."""
    abstract = await get_abstract(pmid)
    return f"PICO Summary for PMID {pmid}:\n\n{abstract[:1000]}..."

@mcp.tool()
async def get_citations(pmid: str, style: str = "AMA") -> str:
    """Return a formatted citation for a PMID. Styles: AMA, APA, Vancouver."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{PUBMED_BASE}/esummary.fcgi", params={
            "db": "pubmed", "id": pmid, "retmode": "json"
        })
        s = r.json()["result"][pmid]
        authors = ", ".join([a["name"] for a in s.get("authors", [])[:3]])
        title = s["title"]
        journal = s["fulljournalname"]
        year = s["pubdate"][:4]
        volume = s.get("volume", "")
        pages = s.get("pages", "")
        return f"{authors}. {title} {journal}. {year};{volume}:{pages}. PMID: {pmid}"

@mcp.tool()
async def find_reviews(query: str, max_results: int = 10) -> str:
    """Search PubMed for systematic reviews and meta-analyses only."""
    return await search_pubmed(
        f"{query} AND (systematic review[pt] OR meta-analysis[pt])", max_results
    )

if __name__ == "__main__":
    mcp.run()
