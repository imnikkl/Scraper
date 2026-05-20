from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

from md_leads.cache import SQLiteCache
from md_leads.config_loader import RunConfig, load_config
from md_leads.enrichment.idno_md import lookup_idno
from md_leads.enrichment.pagespeed import get_pagespeed
from md_leads.enrichment.website_check import check_website
from md_leads.exporter import write_xlsx
from md_leads.models import (
    Business, EnrichedBusiness, Lead, WebsiteStatus,
)
from md_leads.scoring import score
from md_leads.sources.apify_places import fetch_places, parse_apify_items

app = typer.Typer(add_completion=False, help="Moldova leads scraper.")
cache_app = typer.Typer(help="Cache management.")
app.add_typer(cache_app, name="cache")

logger = logging.getLogger("md_leads")

FIXTURE_PATH = Path("tests/fixtures/sample_apify_response.json")

# Rough estimate per place for compass/crawler-google-places (USD).
# Used only for the pre-flight cost guard; actual billing is reported by Apify.
ESTIMATED_COST_PER_PLACE_USD = 0.007


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )


def _cache_path() -> Path:
    return Path(os.environ.get("MD_LEADS_CACHE_PATH", "data/cache.db"))


def _out_dir(cfg: RunConfig) -> Path:
    return Path(os.environ.get("MD_LEADS_OUT_DIR", cfg.output.dir))


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_only.lower().replace(" ", "_")


def _enrich(
    biz: Business, *, skip: bool, pagespeed_key: Optional[str],
) -> EnrichedBusiness:
    if skip:
        return EnrichedBusiness(business=biz, website_check=None,
                                pagespeed=None, idno=None)

    wc = None
    ps = None
    if biz.website:
        wc = check_website(biz.website)
        if wc.error is None and wc.status_code and wc.status_code < 400 \
                and pagespeed_key:
            ps = get_pagespeed(wc.final_url or biz.website, pagespeed_key)

    idno = lookup_idno(biz.name)
    return EnrichedBusiness(business=biz, website_check=wc,
                            pagespeed=ps, idno=idno)


def _fetch_businesses(
    cfg: RunConfig, dry_run: bool, apify_token: Optional[str],
    max_cost_override: Optional[float], assume_yes: bool,
) -> list[Business]:
    if dry_run:
        if not FIXTURE_PATH.exists():
            raise typer.BadParameter(
                f"Dry-run requires fixture at {FIXTURE_PATH}"
            )
        items = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        return list(parse_apify_items(items))

    if not apify_token:
        raise typer.BadParameter("APIFY_TOKEN env var is required (or use --dry-run).")

    # Pre-flight cost estimate
    max_cost = max_cost_override if max_cost_override is not None \
        else cfg.safeguards.max_cost_usd
    estimated = (
        len(cfg.categories) * cfg.max_places_per_category
        * ESTIMATED_COST_PER_PLACE_USD
    )
    typer.echo(
        f"Pre-flight: ~{len(cfg.categories) * cfg.max_places_per_category} "
        f"places, estimated cost ~${estimated:.2f} "
        f"(limit ${max_cost:.2f})"
    )
    if estimated > max_cost and not assume_yes:
        if not typer.confirm(
            f"Estimated cost ${estimated:.2f} exceeds limit ${max_cost:.2f}. "
            "Continue?", default=False,
        ):
            raise typer.Exit(code=0)

    from apify_client import ApifyClient
    client = ApifyClient(apify_token)
    out: list[Business] = []
    for category in cfg.categories:
        try:
            out.extend(fetch_places(
                client, category=category, city=cfg.city,
                language=cfg.language,
                max_per_search=cfg.max_places_per_category,
            ))
        except Exception as e:  # noqa: BLE001 — surface but continue
            logger.error("apify fetch failed for %r: %s", category, e)
    return out


@app.command()
def run(
    config: Path = typer.Option(..., "--config", "-c",
                                exists=True, dir_okay=False),
    dry_run: bool = typer.Option(False, "--dry-run",
                                 help="Use fixture instead of Apify."),
    skip_enrichment: bool = typer.Option(False, "--skip-enrichment",
                                         help="Skip HTTP/PageSpeed/idno."),
    max_cost_usd: Optional[float] = typer.Option(
        None, "--max-cost-usd",
        help="Override safeguards.max_cost_usd from config.",
    ),
    yes: bool = typer.Option(False, "--yes", "-y",
                             help="Skip interactive cost prompt."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run the lead generation pipeline."""
    _setup_logging(verbose)
    load_dotenv()
    cfg = load_config(config)

    apify_token = os.environ.get("APIFY_TOKEN")
    pagespeed_key = os.environ.get("PAGESPEED_API_KEY")

    cache = SQLiteCache(_cache_path(), ttl_days=cfg.cache.ttl_days)

    logger.info("fetching businesses for %s (%d categories)",
                cfg.city, len(cfg.categories))
    businesses = _fetch_businesses(cfg, dry_run, apify_token,
                                   max_cost_usd, yes)
    logger.info("fetched %d raw businesses", len(businesses))

    fresh = [b for b in businesses if not cache.is_recent(b.name, b.phone)]
    logger.info("after cache dedup: %d to enrich (skipped %d cached)",
                len(fresh), len(businesses) - len(fresh))

    enriched: list[EnrichedBusiness] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures = {
            pool.submit(_enrich, b, skip=skip_enrichment,
                        pagespeed_key=pagespeed_key): b
            for b in fresh
        }
        for fut in concurrent.futures.as_completed(futures):
            b = futures[fut]
            try:
                enriched.append(fut.result())
            except Exception as e:  # noqa: BLE001
                logger.warning("enrichment failed for %s: %s", b.name, e)
                enriched.append(EnrichedBusiness(
                    business=b, website_check=None,
                    pagespeed=None, idno=None,
                ))

    for eb in enriched:
        cache.mark_seen(eb.business.name, eb.business.phone)

    leads = [score(eb, cfg.scoring) for eb in enriched]

    if cfg.scoring.exclude_good_websites:
        main = [l for l in leads if l.status != WebsiteStatus.GOOD]
        skipped = [l for l in leads if l.status == WebsiteStatus.GOOD]
    else:
        main, skipped = leads, []

    out_dir = _out_dir(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    city_slug = _slugify(cfg.city)
    out_path = out_dir / f"leads_{date_str}_{city_slug}.xlsx"

    write_xlsx(main, skipped, out_path)

    # Summary
    by_status: dict[str, int] = {}
    for l in main:
        by_status[l.status.value] = by_status.get(l.status.value, 0) + 1
    typer.echo("")
    typer.echo(f"✓ {cfg.city} — {len(cfg.categories)} categorii "
               f"— {len(businesses)} firme procesate")
    for st, count in sorted(by_status.items()):
        typer.echo(f"  • {count:4d} {st}")
    typer.echo(f"  → {len(main)} lead-uri exportate în {out_path}")


@app.command("validate-config")
def validate_config_cmd(path: Path = typer.Argument(..., exists=True)) -> None:
    """Validate a config YAML file."""
    try:
        cfg = load_config(path)
    except ValueError as e:
        typer.echo(f"INVALID: {e}", err=True)
        raise typer.Exit(code=2)
    typer.echo(
        f"valid — {len(cfg.categories)} categorii, city={cfg.city}, "
        f"max_per_cat={cfg.max_places_per_category}"
    )


@cache_app.command("stats")
def cache_stats_cmd() -> None:
    """Show cache stats."""
    cache = SQLiteCache(_cache_path(), ttl_days=30)
    s = cache.stats()
    typer.echo(f"total={s['total']} recent={s['recent']}")


@cache_app.command("clear")
def cache_clear_cmd() -> None:
    """Clear the cache."""
    cache = SQLiteCache(_cache_path(), ttl_days=30)
    cache.clear()
    typer.echo("cache cleared")


if __name__ == "__main__":
    app()
