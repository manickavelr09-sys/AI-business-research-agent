from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import AsyncIterator

from research_agent.agentic_rag import build_research_summary
from research_agent.config import Settings, settings as default_settings
from research_agent.business_enrichment import BusinessEnricher
from research_agent.dedupe import dedupe_records, merge_businesses
from research_agent.discovery import build_discovery_queries, build_source_plan, filter_result, result_relevance_score
from research_agent.extraction import extract_business_from_html, extract_business_leads_from_html, record_from_search_result
from research_agent.geoapify_provider import GeoapifyProvider
from research_agent.http_client import HttpClient
from research_agent.models import BusinessRecord, ResearchReport
from research_agent.normalization import normalize_text
from research_agent.mongo_store import MongoResearchStore
from research_agent.places_provider import GooglePlacesProvider
from research_agent.query_parser import parse_user_query
from research_agent.record_quality import should_stream_record
from research_agent.report import data_quality_summary, verified_count
from research_agent.search_providers import BingHtmlProvider, DuckDuckGoHtmlProvider, SearchProvider, SerperSearchProvider, TavilySearchProvider
from research_agent.serper_provider import SerperPlacesProvider
from research_agent.storage import ResearchCache
from research_agent.verification import verify_record


class ResearchAgent:
    def __init__(self, settings: Settings = default_settings) -> None:
        self.settings = settings
        self.cache = ResearchCache(settings.cache_path)
        self.http = HttpClient(settings, self.cache)
        self.mongo = MongoResearchStore(settings)
        self.places = GooglePlacesProvider(settings, self.http)
        self.geoapify = GeoapifyProvider(settings, self.http)
        self.serper_places = SerperPlacesProvider(settings, self.http)
        self.providers: list[SearchProvider] = [
            SerperSearchProvider(self.http, self.cache),
            TavilySearchProvider(self.http, self.cache),
            DuckDuckGoHtmlProvider(self.http, self.cache),
            BingHtmlProvider(self.http, self.cache),
        ]
        self.enricher = BusinessEnricher(self.providers, self.http, self.settings.concurrency)

    async def close(self) -> None:
        await self.http.close()
        await self.mongo.close()

    async def research_stream(self, raw_query: str, limit: int | None = None) -> AsyncIterator[dict]:
        parsed = parse_user_query(raw_query)
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        yield {"event": "started", "query": parsed.display(), "started_at": started_at}

        search_queries = build_discovery_queries(parsed)
        target_limit = min(max(limit or 200, 1), 5000)
        candidate_goal = _candidate_collection_goal(target_limit)
        source_plan = build_source_plan(parsed, budget=max(12, self.settings.search_query_budget))
        result_urls: dict[str, object] = {}
        searched_sources = set()
        source_errors: list[str] = []
        semaphore = asyncio.Semaphore(self.settings.concurrency)
        records: list[BusinessRecord] = []
        for source_name, enabled in [
            ("geoapify", self.geoapify.enabled),
            ("google_places", self.places.enabled),
            ("serper_places", self.serper_places.enabled),
        ]:
            if not enabled:
                source_errors.append(f"{source_name}:disabled")
                yield {"event": "source_skipped", "source": source_name, "reason": "missing_api_key"}
        try:
            geoapify_records = await self.geoapify.search(parsed, limit=min(candidate_goal, 1200))
        except Exception as exc:
            geoapify_records = []
            source_errors.append(f"geoapify:{type(exc).__name__}")
            yield {"event": "source_error", "source": "geoapify", "error": type(exc).__name__}
        if self.geoapify.enabled:
            searched_sources.add("geoapify")
            yield {"event": "geoapify_complete", "candidate_records": len(geoapify_records)}

        try:
            place_records = await self.places.search(parsed, limit=min(candidate_goal, 500))
        except Exception as exc:
            place_records = []
            source_errors.append(f"google_places:{type(exc).__name__}")
            yield {"event": "source_error", "source": "google_places", "error": type(exc).__name__}
        if self.places.enabled:
            searched_sources.add("google_places")
            yield {"event": "places_complete", "candidate_records": len(place_records)}

        try:
            serper_place_records = await self.serper_places.search(parsed, limit=min(candidate_goal, 500))
        except Exception as exc:
            serper_place_records = []
            source_errors.append(f"serper_places:{type(exc).__name__}")
            yield {"event": "source_error", "source": "serper_places", "error": type(exc).__name__}
        if self.serper_places.enabled:
            searched_sources.add("serper_places")
            yield {"event": "serper_places_complete", "candidate_records": len(serper_place_records)}

        streamed_businesses = 0
        for map_record, source_kind in [
            *((record, "geoapify") for record in geoapify_records),
            *((record, "google_places") for record in place_records),
            *((record, "serper_places") for record in serper_place_records),
        ]:
            verified_map_record = verify_record(map_record)
            if should_stream_record(verified_map_record, parsed, source_kind):
                records.append(verified_map_record)
                if streamed_businesses < target_limit:
                    streamed_businesses += 1
                    yield {"event": "business_discovered", "business": verified_map_record.to_dict()}
                if len(records) >= candidate_goal:
                    break

        if records:
            yield {"event": "business_enrichment_started", "records": len(records)}
            enrichment_goal = min(len(records), _enrichment_collection_goal(target_limit))
            enriched_map_records = await self.enricher.enrich_many(
                records[:enrichment_goal],
                parsed,
                per_business_limit=2,
                timeout_seconds=self.settings.enrichment_timeout_seconds,
            )
            for enriched in enriched_map_records:
                if should_stream_record(enriched, parsed, "geoapify"):
                    records.append(enriched)
                    if streamed_businesses < target_limit:
                        streamed_businesses += 1
                        yield {"event": "business_enriched", "business": enriched.to_dict()}

        async def run_search(provider: SearchProvider, search_query: str, page: int) -> None:
            try:
                async with semaphore:
                    results = await provider.search(search_query, page)
                searched_sources.add(provider.name)
            except Exception as exc:
                source_errors.append(f"{provider.name}:{type(exc).__name__}")
                return
            for result in results:
                if filter_result(result, parsed):
                    result_urls.setdefault(result.url, result)

        active_query_limit = min(max(18, target_limit * 2) if records else self.settings.search_query_budget, len(source_plan))
        active_source_plan = source_plan[:active_query_limit]
        active_search_queries = [item.query for item in active_source_plan]
        active_search_pages = min(self.settings.max_search_pages, 2)
        search_tasks = [
            run_search(provider, search_query, page)
            for search_query in active_search_queries
            for page in range(1, active_search_pages + 1)
            for provider in self.providers
        ]
        yield {
            "event": "search_plan",
            "queries": len(active_search_queries),
            "providers": len(self.providers),
            "pages": active_search_pages,
            "source_groups": sorted({item.source_group for item in active_source_plan}),
        }
        if search_tasks:
            done, pending = await asyncio.wait(
                [asyncio.create_task(task) for task in search_tasks],
                timeout=self.settings.search_timeout_seconds if records else self.settings.search_timeout_seconds * 2,
            )
            for task in pending:
                task.cancel()
            if pending:
                yield {"event": "search_timeout", "cancelled_tasks": len(pending)}
            for task in done:
                try:
                    task.result()
                except Exception as exc:
                    source_errors.append(f"search_task:{type(exc).__name__}")
        search_results = sorted(
            result_urls.values(),
            key=lambda item: result_relevance_score(item, parsed),
            reverse=True,
        )[: self.settings.max_result_urls]
        if limit:
            search_results = search_results[:candidate_goal]
        yield {
            "event": "discovery_complete",
            "candidate_urls": len(search_results),
            "search_queries": len(search_queries),
        }

        async def fetch_and_extract(result) -> tuple[BusinessRecord, list[BusinessRecord]]:
            seed = record_from_search_result(result)
            try:
                fetched = await self.http.fetch(result.url)
                if fetched and fetched.status_code < 400 and fetched.body:
                    record = extract_business_from_html(fetched.url, fetched.body, seed)
                    leads = extract_business_leads_from_html(
                        fetched.url,
                        fetched.body,
                        parsed.category,
                        parsed.location,
                        limit=20,
                    )
                    return record, leads
            except Exception as exc:
                source_errors.append(f"extract:{type(exc).__name__}")
            return seed, []

        async def worker(result) -> tuple[BusinessRecord, list[BusinessRecord]]:
            async with semaphore:
                return await fetch_and_extract(result)

        article_leads: list[BusinessRecord] = []
        extraction_tasks = [asyncio.create_task(worker(result)) for result in search_results]
        if extraction_tasks:
            yield {"event": "extraction_started", "candidate_urls": len(extraction_tasks)}
            done, pending = await asyncio.wait(
                extraction_tasks,
                timeout=self.settings.extraction_timeout_seconds,
            )
            for task in pending:
                task.cancel()
            if pending:
                source_errors.append(f"extraction_timeout:{len(pending)}")
                yield {"event": "extraction_timeout", "cancelled_tasks": len(pending)}
            for task in done:
                try:
                    raw_record, leads = task.result()
                    article_leads.extend(leads)
                    record = verify_record(raw_record)
                except Exception as exc:
                    source_errors.append(f"worker:{type(exc).__name__}")
                    continue
                if should_stream_record(record, parsed, "web"):
                    records.append(record)
                    if streamed_businesses < target_limit:
                        streamed_businesses += 1
                        yield {"event": "business_discovered", "business": record.to_dict()}

        if article_leads:
            yield {"event": "lead_mining_complete", "candidate_leads": len(article_leads)}
            lead_deduped, _ = dedupe_records(article_leads)
            yield {"event": "lead_places_enrichment_started", "candidate_leads": len(lead_deduped)}
            place_enriched_leads = await self._enrich_leads_with_places(
                lead_deduped[: min(len(lead_deduped), self.settings.lead_enrichment_limit, candidate_goal)],
                parsed,
                source_errors,
            )
            yielded_place_enriched = 0
            for lead in place_enriched_leads:
                verified_lead = verify_record(lead)
                if should_stream_record(verified_lead, parsed, "serper_places"):
                    records.append(verified_lead)
                    yielded_place_enriched += 1
                    if streamed_businesses < target_limit:
                        streamed_businesses += 1
                        yield {"event": "business_enriched", "business": verified_lead.to_dict()}
            yield {
                "event": "lead_places_enrichment_complete",
                "candidate_leads": len(lead_deduped),
                "businesses_enriched": yielded_place_enriched,
            }
            enriched_leads = await self.enricher.enrich_many(
                lead_deduped[: min(len(lead_deduped), self.settings.lead_enrichment_limit, candidate_goal)],
                parsed,
                per_business_limit=3,
                timeout_seconds=max(self.settings.enrichment_timeout_seconds, 15),
            )
            for lead in enriched_leads:
                verified_lead = verify_record(lead)
                if should_stream_record(verified_lead, parsed, "web"):
                    records.append(verified_lead)
                    if streamed_businesses < target_limit:
                        streamed_businesses += 1
                        yield {"event": "business_enriched", "business": verified_lead.to_dict()}

        deduped, removed = dedupe_records(records)
        verified = [
            record
            for record in (verify_record(record) for record in deduped)
            if should_stream_record(record, parsed, "web")
        ]
        verified.sort(key=lambda record: record.reliability_score, reverse=True)
        final_results = verified[:target_limit]
        completed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        quality = data_quality_summary(final_results)
        research_summary = await build_research_summary(
            parsed.display(),
            final_results,
            quality,
            self.settings,
            source_errors,
        )
        report = ResearchReport(
            query=parsed.display(),
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=time.perf_counter() - started,
            businesses_found=len(final_results),
            businesses_verified=verified_count(final_results),
            duplicate_records_removed=removed,
            sources_searched=len(searched_sources) + len(search_queries),
            data_quality=quality,
            results=final_results,
            research_summary=research_summary,
        )
        report_payload = report.to_dict()
        mongo_result = await self.mongo.save_report(report_payload)
        completed_event = {"event": "completed", "report": report_payload}
        if mongo_result:
            completed_event["mongo"] = mongo_result
        yield completed_event

    async def _enrich_leads_with_places(
        self,
        leads: list[BusinessRecord],
        parsed,
        source_errors: list[str],
    ) -> list[BusinessRecord]:
        if not leads or not parsed.location:
            return []
        if not (self.serper_places.enabled or self.places.enabled):
            return []
        semaphore = asyncio.Semaphore(max(2, min(self.settings.concurrency, 8)))

        async def enrich_one(lead: BusinessRecord) -> BusinessRecord | None:
            if not lead.business_name:
                lead = verify_record(lead)
            if not lead.business_name:
                return None
            exact_query = type(parsed)(
                raw=f"{lead.business_name} in {parsed.location}",
                category=lead.business_name,
                location=parsed.location,
                modifiers=[],
            )
            candidates: list[BusinessRecord] = []
            async with semaphore:
                if self.serper_places.enabled:
                    try:
                        candidates.extend(await self.serper_places.search(exact_query, limit=4))
                    except Exception as exc:
                        source_errors.append(f"serper_places_exact:{type(exc).__name__}")
                if self.places.enabled:
                    try:
                        candidates.extend(await self.places.search(exact_query, limit=3))
                    except Exception as exc:
                        source_errors.append(f"google_places_exact:{type(exc).__name__}")
            verified_candidates = [verify_record(candidate) for candidate in candidates]
            matched = [candidate for candidate in verified_candidates if _place_candidate_matches_lead(lead, candidate)]
            if not matched:
                return None
            matched.sort(key=lambda candidate: _place_candidate_score(lead, candidate), reverse=True)
            enriched = lead
            for candidate in matched[:2]:
                merge_businesses(enriched, candidate)
            return verify_record(enriched)

        tasks = [asyncio.create_task(enrich_one(lead)) for lead in leads]
        if not tasks:
            return []
        done, pending = await asyncio.wait(tasks, timeout=max(self.settings.enrichment_timeout_seconds, 15))
        for task in pending:
            task.cancel()
        enriched: list[BusinessRecord] = []
        for task in done:
            if task.cancelled() or task.exception() is not None:
                continue
            record = task.result()
            if record:
                enriched.append(record)
        return enriched

    async def research(self, raw_query: str, limit: int | None = None) -> ResearchReport:
        report_data = None
        async for event in self.research_stream(raw_query, limit=limit):
            if event["event"] == "completed":
                report_data = event["report"]
        if report_data is None:
            raise RuntimeError("Research did not complete")
        summary = report_data["search_summary"]
        return ResearchReport(
            query=summary["query"],
            started_at=summary["started_at"],
            completed_at=summary["completed_at"],
            duration_seconds=float(summary["research_duration"].split()[0]),
            businesses_found=summary["businesses_found"],
            businesses_verified=summary["businesses_verified"],
            duplicate_records_removed=summary["duplicate_records_removed"],
            sources_searched=summary["sources_searched"],
            data_quality=report_data["data_quality_summary"],
            results=[],
        )


def _place_candidate_matches_lead(lead: BusinessRecord, candidate: BusinessRecord) -> bool:
    return _place_candidate_score(lead, candidate) >= 0.62


def _place_candidate_score(lead: BusinessRecord, candidate: BusinessRecord) -> float:
    lead_tokens = _important_name_tokens(lead.business_name)
    candidate_tokens = _important_name_tokens(candidate.business_name)
    if not lead_tokens or not candidate_tokens:
        return 0.0
    overlap = len(lead_tokens & candidate_tokens) / max(len(lead_tokens), 1)
    candidate_overlap = len(lead_tokens & candidate_tokens) / max(len(candidate_tokens), 1)
    score = overlap * 0.7 + candidate_overlap * 0.3
    if normalize_text(lead.business_name) == normalize_text(candidate.business_name):
        score = 1.0
    elif normalize_text(lead.business_name) in normalize_text(candidate.business_name):
        score = max(score, 0.82)
    return score


def _candidate_collection_goal(target_limit: int) -> int:
    if target_limit <= 10:
        return max(60, target_limit * 12)
    if target_limit <= 100:
        return max(300, target_limit * 6)
    if target_limit <= 500:
        return max(1000, target_limit * 5)
    return min(5000, max(target_limit * 3, target_limit + 500))


def _enrichment_collection_goal(target_limit: int) -> int:
    if target_limit <= 10:
        return target_limit
    if target_limit <= 100:
        return min(40, target_limit)
    return min(80, target_limit)


def _important_name_tokens(value: str) -> set[str]:
    ignored = {
        "the",
        "and",
        "restaurant",
        "restaurants",
        "hotel",
        "clinic",
        "shop",
        "store",
        "service",
        "services",
        "center",
        "centre",
        "near",
        "in",
    }
    return {token for token in normalize_text(value).split() if len(token) > 2 and token not in ignored}
