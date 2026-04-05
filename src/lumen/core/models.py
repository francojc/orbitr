"""Pydantic data models: Paper, Author, SearchResult."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Author(BaseModel):
    """A paper author."""

    name: str
    affiliation: str | None = None
    author_id: str | None = None


class Paper(BaseModel):
    """A single academic paper from any source."""

    id: str = Field(description="Source-specific identifier.")
    title: str
    authors: list[Author] = Field(default_factory=list)
    abstract: str | None = None
    published_date: datetime | None = None
    updated_date: datetime | None = None
    url: str
    pdf_url: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    venue: str | None = None
    categories: list[str] = Field(default_factory=list)
    citation_count: int | None = None
    source: str = Field(
        description="Data source name, e.g. 'arxiv' or 'semantic_scholar'."
    )

    @property
    def author_names(self) -> list[str]:
        """Return a list of author name strings."""
        return [a.name for a in self.authors]

    @property
    def year(self) -> int | None:
        """Return the publication year, or None if unknown."""
        if self.published_date:
            return self.published_date.year
        return None


class SearchResult(BaseModel):
    """The result of a multi-source search query."""

    papers: list[Paper] = Field(default_factory=list)
    total_count: int = 0
    query: str
    sources: list[str] = Field(default_factory=list)
