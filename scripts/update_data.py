from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "candidates.json"
OVERRIDES_PATH = ROOT / "data" / "paper_overrides.json"
REPORT_PATH = ROOT / "scrape-report.json"

US_RANKING_URL = "https://ideas.repec.org/top/top.usecondept.html"
UK_RANKING_URL = "https://ideas.repec.org/top/top.uk.html"

MACRO_RE = re.compile(
    r"\b(?:macro(?:economics?|economic)?|international\s+macro|monetary\s+economics?|"
    r"macro[\s-]?finance|economic\s+growth|business\s+cycles?|aggregate\s+economics?)\b",
    re.IGNORECASE,
)
PAPER_MARKER_RE = re.compile(r"\b(?:job\s+market\s+paper|paper\s+title|\(?jmp\)?)\b", re.IGNORECASE)
FIELD_LABEL_RE = re.compile(r"\b(?:primary\s+)?(?:research\s+)?fields?(?:\s+of\s+study)?\s*:", re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")


DEPARTMENTS = [
    # IDEAS/RePEc US economics department ranking, May 2026.
    {"institution": "Harvard University", "country": "US", "rank": 1, "url": "https://economics.harvard.edu/job-market-candidates"},
    {"institution": "MIT", "country": "US", "rank": 2, "url": "https://economics.mit.edu/academic-programs/phd-program/job-market"},
    {"institution": "UC Berkeley", "country": "US", "rank": 3, "url": "https://econ.berkeley.edu/graduate/placement/job-market-candidates-phd"},
    {"institution": "University of Chicago", "country": "US", "rank": 4, "url": "https://economics.uchicago.edu/job-market"},
    {"institution": "Stanford University", "country": "US", "rank": 5, "url": "https://economics.stanford.edu/graduate/job-market-candidates"},
    {"institution": "Yale University", "country": "US", "rank": 6, "url": "https://economics.yale.edu/graduate/job-market-candidates"},
    {"institution": "Princeton University", "country": "US", "rank": 7, "url": "https://economics.princeton.edu/graduate-program/job-market-candidates/"},
    {"institution": "New York University", "country": "US", "rank": 8, "url": "https://as.nyu.edu/departments/economics/graduate/job-market.html"},
    {"institution": "Columbia University", "country": "US", "rank": 9, "url": "https://econ.columbia.edu/phd/job-market-candidates/"},
    {"institution": "Brown University", "country": "US", "rank": 10, "url": "https://economics.brown.edu/academics/graduate/job-market-candidates"},
    {"institution": "University of Pennsylvania", "country": "US", "rank": 11, "url": "https://economics.sas.upenn.edu/graduate/job-market-candidates"},
    {"institution": "Boston University", "country": "US", "rank": 12, "url": "https://www.bu.edu/econ/job-market-candidates/"},
    {"institution": "University of Southern California", "country": "US", "rank": 17, "url": "https://dornsife.usc.edu/econ/doctoral/job-market-candidates/"},
    {"institution": "University of Minnesota", "country": "US", "rank": 33, "url": "https://cla.umn.edu/economics/people/job-market-candidates"},
    # Top degree-granting university economics departments in the UK ranking.
    {"institution": "London School of Economics", "country": "UK", "rank": 1, "url": "https://www.lse.ac.uk/economics/phd-job-market"},
    {"institution": "University of Oxford", "country": "UK", "rank": 2, "url": "https://www.economics.ox.ac.uk/job-market-candidates"},
    {"institution": "University College London", "country": "UK", "rank": 3, "url": "https://www.ucl.ac.uk/economics/people/phd-job-market-candidates"},
    {"institution": "University of Warwick", "country": "UK", "rank": 4, "url": "https://warwick.ac.uk/fac/soc/economics/staff/job-market-candidates/"},
    {"institution": "University of Nottingham", "country": "UK", "rank": 5, "url": "https://www.nottingham.ac.uk/economics/people/job-market-candidates.aspx"},
    {"institution": "University of Cambridge", "country": "UK", "rank": 6, "url": "https://www.econ.cam.ac.uk/postgraduate-studies/phd-job-market"},
    {"institution": "University of York", "country": "UK", "rank": 7, "url": "https://www.york.ac.uk/economics/postgraduate-research/job-market-candidates/"},
    {"institution": "Queen Mary University of London", "country": "UK", "rank": 8, "url": "https://www.qmul.ac.uk/sef/postgraduate/phd/job-market-candidates/"},
]


# These official rosters use layouts where fields or paper links live only on
# candidate profiles. Entries remain eligible only while the name appears on
# the official department roster; paper URLs are verified in paper_overrides.
CURATED_CANDIDATES = {
    "University of Pennsylvania": [
        {
            "name": "Luigi Falasconi",
            "fields": ["Macroeconomics", "Financial Economics", "International Finance"],
            "paper_title": "Bailout Expectations, Default Risk and the Dynamics of Bank Credit Spreads",
            "profile_url": "https://luigifalasconi.com",
        },
        {
            "name": "Ji Hwan Kim",
            "fields": ["Macroeconomics", "Urban Economics", "Environmental Economics"],
            "paper_title": "Adapting to Storms in the U.S.: A Spatial Dynamic Analysis",
            "profile_url": "https://jihwankim1994.weebly.com/",
        },
        {
            "name": "Josemaria Larrain",
            "fields": ["Quantitative Macroeconomics", "Labor Economics"],
            "paper_title": "A Taste for Luxury",
            "profile_url": "https://www.josemarialarrain.com",
        },
        {
            "name": "Alexander Sawyer",
            "fields": ["Macroeconomics", "Business Dynamics", "Information Frictions"],
            "paper_title": "Learning through Sequential Interactions in the Market for Venture Capital",
            "profile_url": "https://sites.google.com/sas.upenn.edu/alexander-sawyer/home",
        },
        {
            "name": "Javier Tasso",
            "fields": ["Macroeconomics", "Political Economy"],
            "paper_title": "Unemployment and Forward-Looking Congressmen",
            "profile_url": "https://javiertasso.github.io/",
        },
    ],
    "Boston University": [
        {
            "name": "Zixing Guo",
            "fields": ["Macroeconomics", "Monetary Economics", "Financial Economics"],
            "paper_title": "The Macro Impact of the Debt-Inflation Channel on Investment",
            "profile_url": "https://gzx0321.github.io/",
        },
        {
            "name": "Hannah Rhodenhiser",
            "fields": ["Macroeconomics", "Environmental Economics"],
            "paper_title": "Averting Deforestation At Scale: The Macroeconomics of Payments for Ecosystem Services",
            "profile_url": "https://sites.google.com/view/hannahrhodenhiser",
        },
    ],
    "University of Southern California": [
        {
            "name": "Yakup Kutsal Koca",
            "fields": ["Macroeconomics", "Labor Economics", "Economics of AI and Innovation"],
            "paper_title": "AI Automation and Labor Market Outcomes",
            "profile_url": "https://ykkoca.github.io",
        },
        {
            "name": "Zili Yang",
            "fields": ["Economic Growth", "Economics of Innovation", "Business Economics"],
            "paper_title": "Technology M&A and Knowledge Diffusion",
            "profile_url": "https://ziligit.github.io/",
        },
    ],
    "University of Minnesota": [
        {
            "name": "Leonardo Barreto",
            "roster_name": "Barreto, Leonardo",
            "fields": ["Macroeconomics", "International Economics", "Monetary Economics"],
            "paper_title": "Debt-Financed Fiscal Stimulus, Heterogeneity, and Welfare",
            "profile_url": "https://www.leonardo-barreto.com/",
        },
        {
            "name": "Carlos Bolivar",
            "roster_name": "Bolivar, Carlos",
            "fields": ["Macroeconomics", "International Economics"],
            "paper_title": "The Micro Effects of Aggregate Shocks in Endogenous Trade Networks",
            "profile_url": "https://carlosbolivar.info/",
        },
        {
            "name": "Francisco Bullano",
            "roster_name": "Bullano, Francisco",
            "fields": ["Macroeconomics", "Public Economics", "Health Economics"],
            "paper_title": "Health, Families and Private and Public Health Insurance",
            "profile_url": "https://franciscobullano.com/",
        },
        {
            "name": "Effie Karfaki",
            "roster_name": "Karfaki, Eftychia (Effie)",
            "fields": ["International Finance", "Applied Macroeconomics", "Monetary Economics"],
            "paper_title": "Are Exchange Rate Appreciations Contractionary or Expansionary? Evidence from Switzerland",
            "profile_url": "https://sites.google.com/umn.edu/effie-karfaki/home",
        },
        {
            "name": "Ioannis Koutsonikolis",
            "roster_name": "Koutsonikolis, Ioannis",
            "fields": ["Macroeconomics", "Public Finance", "Corporate Finance"],
            "paper_title": "Stock Market Accounting",
            "profile_url": "https://www.ikoutsonikolis.com/",
        },
        {
            "name": "Scott Sommers",
            "roster_name": "Sommers, Scott",
            "fields": ["International Macroeconomics", "International Trade", "Development"],
            "paper_title": "Land Institutions, Agricultural Productivity, and Climate Shocks",
            "profile_url": "https://sites.google.com/view/scottsommers",
        },
        {
            "name": "Bipul Verma",
            "roster_name": "Verma, Bipul",
            "fields": ["Macroeconomics", "Economic Growth", "Inequality"],
            "paper_title": "Higher Education and Economic Development: Evidence from College Expansion in India",
            "profile_url": "https://www.bipulverma.com/",
        },
        {
            "name": "Jacob Wright",
            "roster_name": "Wright, Jacob",
            "fields": ["Macroeconomics", "Labor Economics", "Spatial Economics"],
            "paper_title": "On the Spatial Distribution of Colleges",
            "profile_url": "https://www.jacob-wright.me/",
        },
        {
            "name": "Alexander Wurdinger",
            "roster_name": "Wurdinger, Alexander",
            "fields": ["Macroeconomics", "Labor Economics"],
            "paper_title": "Declining Teen Employment: Causes and Consequences",
            "profile_url": "https://sites.google.com/view/alexwurdinger/home",
        },
        {
            "name": "Lieyuan Yang",
            "roster_name": "Yang, Lieyuan",
            "fields": ["Macroeconomics", "Public Economics", "Economic Growth"],
            "paper_title": "Growth with Regional Redistribution",
            "profile_url": "https://sites.google.com/umn.edu/lieyuanyang",
        },
    ],
}


@dataclass
class Candidate:
    id: str
    name: str
    institution: str
    country: str
    rank: int
    fields: list[str]
    paper_title: str
    paper_url: str
    profile_url: str
    source_url: str
    last_verified: str


class Scraper:
    def __init__(self, delay: float = 0.25, timeout: int = 20, debug: bool = False):
        self.delay = delay
        self.timeout = timeout
        self.debug = debug
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/137.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.8",
            }
        )
        self.cache: dict[str, str] = {}
        self.overrides = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8")) if OVERRIDES_PATH.exists() else {}

    def fetch(self, url: str) -> str:
        if url in self.cache:
            return self.cache[url]
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "html" not in content_type and "text" not in content_type:
            raise ValueError(f"Unsupported content type for {url}: {content_type}")
        self.cache[url] = response.text
        time.sleep(self.delay)
        return response.text

    def scrape_department(self, department: dict) -> list[Candidate]:
        html = self.fetch(department["url"])
        soup = BeautifulSoup(html, "html.parser")
        curated = curated_partials(soup, department)
        blocks = [] if curated is not None else candidate_blocks(soup)
        partials = curated if curated is not None else [extract_candidate(block, department) for block in blocks]
        if self.debug:
            headings = [
                clean_text(tag.get_text(" ", strip=True))
                for tag in soup.find_all(["h2", "h3", "h4"])
                if tag.find("a", href=True)
            ]
            print(f"DEBUG linked headings: {headings[:30]}")
            print(f"DEBUG {department['institution']}: {len(blocks)} macro block(s)")
            for index, (block, partial) in enumerate(zip(blocks, partials), start=1):
                print(f"DEBUG block {index}: {clean_text(block.get_text(' ', strip=True))[:700]}")
                print(f"DEBUG html {index}: {str(block)[:1800]}")
                print(f"DEBUG parsed {index}: {partial}")
        partials = deduplicate_partials(item for item in partials if item)
        candidates: list[Candidate] = []
        for partial in partials:
            if partial["profile_url"].rstrip("/") == department["url"].rstrip("/"):
                continue
            override = self.overrides.get(partial["name"])
            if override:
                partial["paper_title"] = override["paper_title"]
                partial["paper_url"] = override["paper_url"]
            if not partial["paper_url"]:
                paper = self.resolve_paper(partial["profile_url"], partial["paper_title"])
                if paper:
                    partial["paper_title"], partial["paper_url"] = paper
            if not partial["paper_title"] or not partial["paper_url"]:
                continue
            partial["paper_url"] = urljoin(partial["profile_url"] or department["url"], partial["paper_url"])
            candidates.append(build_candidate(partial, department))
        return deduplicate_candidates(candidates)

    def resolve_paper(self, profile_url: str, known_title: str) -> tuple[str, str] | None:
        if not profile_url or profile_url.startswith("mailto:"):
            return None
        try:
            homepage = self.fetch(profile_url)
        except (requests.RequestException, ValueError):
            return None
        soup = BeautifulSoup(homepage, "html.parser")
        result = find_paper_link(soup, profile_url, known_title)
        if self.debug:
            print(f"DEBUG paper homepage {profile_url}: {result}")
        if result:
            return known_title or result[0], result[1]

        pages = []
        base_host = urlparse(profile_url).netloc.lower()
        for anchor in soup.find_all("a", href=True):
            label = clean_text(anchor.get_text(" ", strip=True)).lower()
            absolute = urljoin(profile_url, anchor["href"])
            if urlparse(absolute).netloc.lower() != base_host:
                continue
            if re.search(r"\b(research|papers?|publications?|working papers?)\b", label):
                pages.append(absolute)
        for page_url in list(dict.fromkeys(pages))[:3]:
            try:
                page_soup = BeautifulSoup(self.fetch(page_url), "html.parser")
            except (requests.RequestException, ValueError):
                continue
            result = find_paper_link(page_soup, page_url, known_title)
            if self.debug:
                print(f"DEBUG paper subpage {page_url}: {result}")
            if result:
                return known_title or result[0], result[1]
        return None


def clean_text(value: str) -> str:
    return SPACE_RE.sub(" ", value or "").strip()


def curated_partials(soup: BeautifulSoup, department: dict) -> list[dict] | None:
    configured = CURATED_CANDIDATES.get(department["institution"])
    if configured is None:
        return None
    roster_text = clean_text(soup.get_text(" ", strip=True)).casefold()
    return [
        {key: value for key, value in candidate.items() if key != "roster_name"} | {"paper_url": ""}
        for candidate in configured
        if clean_text(candidate.get("roster_name", candidate["name"])).casefold() in roster_text
    ]


def absolute_url(base: str, href: str) -> str:
    return urljoin(base, href.strip())


def is_person_name(value: str) -> bool:
    value = clean_text(value).strip("|:-")
    if not 3 <= len(value) <= 70 or any(char.isdigit() for char in value):
        return False
    lowered = value.lower()
    blocked = (
        "job market", "paper", "website", "research", "candidate", "economics", "university", "department", "email",
        "macroeconomics", "finance", "econometrics", "labor", "labour", "development", "monetary",
    )
    if any(word in lowered for word in blocked):
        return False
    words = value.replace(",", " ").split()
    return 2 <= len(words) <= 5 and sum(word[:1].isupper() for word in words) >= 2


def candidate_blocks(soup: BeautifulSoup) -> list[Tag]:
    blocks: list[Tag] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        anchor_text = clean_text(anchor.get_text(" ", strip=True))
        if not is_person_name(anchor_text):
            continue
        fragment = BeautifulSoup("", "html.parser")
        wrapper = fragment.new_tag("article", attrs={"class": "candidate-card"})
        heading = fragment.new_tag("h3")
        heading.append(BeautifulSoup(str(anchor), "html.parser").contents[0])
        wrapper.append(heading)
        copied_anchors: set[int] = set()
        for element in anchor.next_elements:
            if isinstance(element, Tag) and element.name == "a" and element is not anchor:
                next_label = clean_text(element.get_text(" ", strip=True))
                parent_text = clean_text(element.parent.get_text(" ", strip=True)) if element.parent else next_label
                if is_person_name(next_label) and not PAPER_MARKER_RE.search(parent_text):
                    break
            if not isinstance(element, NavigableString):
                continue
            if isinstance(element.parent, Tag) and element.parent.name == "a" and element.parent.get("href"):
                anchor_id = id(element.parent)
                if anchor_id not in copied_anchors:
                    copied_anchors.add(anchor_id)
                    wrapper.append(BeautifulSoup(str(element.parent), "html.parser").contents[0])
            else:
                wrapper.append(str(element) + " ")
            if len(clean_text(wrapper.get_text(" ", strip=True))) > 2200:
                break
        text = clean_text(wrapper.get_text(" ", strip=True))
        if MACRO_RE.search(text) and PAPER_MARKER_RE.search(text):
            fingerprint = hashlib.sha1(text.encode("utf-8")).hexdigest()
            seen.add(fingerprint)
            blocks.append(wrapper)

    for heading in soup.find_all(["h2", "h3", "h4"]):
        heading_text = clean_text(heading.get_text(" ", strip=True))
        if not is_person_name(heading_text):
            continue
        fragment = BeautifulSoup("", "html.parser")
        wrapper = fragment.new_tag("article", attrs={"class": "candidate-card"})
        wrapper.append(BeautifulSoup(str(heading), "html.parser").contents[0])
        copied_anchors: set[int] = set()
        for element in heading.next_elements:
            if isinstance(element, Tag) and element is not heading and element.name in {"h2", "h3", "h4"}:
                possible_name = clean_text(element.get_text(" ", strip=True))
                if is_person_name(possible_name):
                    break
            if not isinstance(element, NavigableString):
                continue
            if isinstance(element.parent, Tag) and element.parent.name == "a" and element.parent.get("href"):
                anchor_id = id(element.parent)
                if anchor_id not in copied_anchors:
                    copied_anchors.add(anchor_id)
                    wrapper.append(BeautifulSoup(str(element.parent), "html.parser").contents[0])
            else:
                wrapper.append(str(element) + " ")
            if len(clean_text(wrapper.get_text(" ", strip=True))) > 3000:
                break
        text = clean_text(wrapper.get_text(" ", strip=True))
        if MACRO_RE.search(text) and PAPER_MARKER_RE.search(text):
            fingerprint = hashlib.sha1(text.encode("utf-8")).hexdigest()
            seen.add(fingerprint)
            blocks.append(wrapper)

    for node in soup.find_all(string=MACRO_RE):
        current = node.parent
        choices: list[tuple[int, Tag]] = []
        for depth in range(8):
            if not isinstance(current, Tag) or current.name in {"body", "html"}:
                break
            if current.name not in {"article", "div", "li", "section", "tr", "td"}:
                current = current.parent
                continue
            text = clean_text(current.get_text(" ", strip=True))
            classes = " ".join(current.get("class", [])).lower()
            headings = [clean_text(tag.get_text(" ", strip=True)) for tag in current.find_all(["h2", "h3", "h4", "h5"], limit=3)]
            has_personal_website = any(
                "personal website" in clean_text(anchor.get_text(" ", strip=True)).lower()
                for anchor in current.find_all("a", href=True, limit=8)
            )
            candidate_shape = bool(
                re.search(r"candidate|person|profile|views-row|card|item", classes)
                or has_personal_website
                or any(is_person_name(heading) for heading in headings)
            )
            if 25 <= len(text) <= 3000 and candidate_shape:
                marker_bonus = 0 if PAPER_MARKER_RE.search(text) or "program entry" in text.lower() else 250
                choices.append((len(text) + depth * 25 + marker_bonus, current))
            current = current.parent
        if not choices:
            continue
        block = min(choices, key=lambda item: item[0])[1]
        fingerprint = hashlib.sha1(clean_text(block.get_text(" ", strip=True)).encode("utf-8")).hexdigest()
        if fingerprint not in seen:
            seen.add(fingerprint)
            blocks.append(block)
    return blocks


def extract_candidate(block: Tag, department: dict) -> dict | None:
    text = clean_text(block.get_text(" ", strip=True))
    fields = extract_fields(text, block)
    if not fields or not any(MACRO_RE.search(field) for field in fields):
        return None

    name = extract_name(block, text)
    if not name:
        return None

    profile_url = extract_profile_url(block, name, department["url"])
    paper_title, paper_url = extract_source_paper(block, text, department["url"], name)
    return {
        "name": name,
        "fields": fields,
        "paper_title": paper_title,
        "paper_url": paper_url,
        "profile_url": profile_url or department["url"],
    }


def extract_fields(text: str, block: Tag | None = None) -> list[str]:
    if block:
        field_node = block.select_one(".display-fields")
        if field_node:
            raw = clean_text(field_node.get_text(" ", strip=True))
            fields = [clean_text(field) for field in re.split(r"[,;/]", raw) if clean_text(field)]
            return fields[:6] if any(MACRO_RE.search(field) for field in fields) else []
    patterns = [
        r"Fields? of Study\s*:\s*(.+?)(?:Advisor|Job Market Paper|References|Email|$)",
        r"Field\(s\)\s*:\s*(.+?)(?:Paper Title|Main Advisor|Advisor|$)",
        r"Primary Research Focuses?\s*:\s*(.+?)(?:Secondary|References|Job Market Paper|$)",
        r"Primary (?:Research )?Field\s*:\s*(.+?)(?:Secondary|Personal Website|Job Market Paper|$)",
        r"(?:Research )?Fields?\s*:\s*(.+?)(?:Job Market Paper|Advisor|References|Email|$)",
    ]
    raw = ""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and MACRO_RE.search(match.group(1)):
            raw = match.group(1)
            break
    if not raw:
        sentences = re.split(r"(?<=[.!?])\s+|[|]", text)
        macro_sentence = next((segment for segment in sentences if len(segment) < 360 and MACRO_RE.search(segment)), "")
        if macro_sentence:
            detected = []
            for label, pattern in [
                ("International Macroeconomics", r"international\s+macroeconomics?"),
                ("Monetary Economics", r"monetary\s+(?:economics?|policy)"),
                ("Macro-Finance", r"macro[\s-]?finance"),
                ("Economic Growth", r"(?:economic\s+)?growth"),
                ("Macroeconomics", r"macroeconomics?"),
            ]:
                if re.search(pattern, macro_sentence, re.IGNORECASE):
                    detected.append(label)
            return detected or ["Macroeconomics"]
    fields = []
    for field in re.split(r"[,;/]", raw):
        field = clean_text(field).strip(".-")
        field = re.sub(r"^(?:and\s+)", "", field, flags=re.IGNORECASE)
        if 2 <= len(field) <= 80 and field.lower() not in {item.lower() for item in fields}:
            fields.append(field)
    if not any(MACRO_RE.search(field) for field in fields):
        return []
    return fields[:6]


def extract_name(block: Tag, text: str) -> str:
    name_node = block.select_one(".display-name")
    if name_node:
        candidate = clean_text(name_node.get_text(" ", strip=True))
        if is_person_name(candidate):
            return normalize_name(candidate)
    label = re.search(r"Candidate Name\s*:\s*(.+?)(?:Field\(s\)|Paper Title|$)", text, re.IGNORECASE)
    if label:
        candidate = clean_text(label.group(1))
        if is_person_name(candidate):
            return normalize_name(candidate)

    leading_name = re.search(r"^(.{3,80}?)\s+Primary (?:Research )?Field\s*:", text, re.IGNORECASE)
    if leading_name:
        candidate = clean_text(leading_name.group(1))
        if is_person_name(candidate):
            return normalize_name(candidate)

    for tag in block.find_all(["h2", "h3", "h4", "h5", "strong"], limit=8):
        candidate = clean_text(tag.get_text(" ", strip=True))
        if is_person_name(candidate):
            return normalize_name(candidate)
    for anchor in block.find_all("a", href=True, limit=12):
        candidate = clean_text(anchor.get_text(" ", strip=True))
        if is_person_name(candidate):
            return normalize_name(candidate)
    comma_name = re.search(r"\b([A-Z][A-Za-z'’-]+(?:\s+[A-Z][A-Za-z'’-]+)?)\s*,\s*([A-Z][A-Za-z'’-]+(?:\s+[A-Z][A-Za-z'’-]+)?)\b", text)
    if comma_name:
        return f"{comma_name.group(2)} {comma_name.group(1)}"
    return ""


def normalize_name(name: str) -> str:
    name = clean_text(name).strip("|:-")
    if "," in name:
        last, first = [part.strip() for part in name.split(",", 1)]
        return f"{first} {last}"
    return name


def extract_profile_url(block: Tag, name: str, base_url: str) -> str:
    normalized_name = clean_text(name).lower()
    fallback = ""
    for anchor in block.find_all("a", href=True):
        label = clean_text(anchor.get_text(" ", strip=True))
        href = absolute_url(base_url, anchor["href"])
        if href.startswith("mailto:") or PAPER_MARKER_RE.search(label):
            continue
        if clean_text(label).lower() == normalized_name:
            return href
        if label.lower() in {"website", "personal website", "homepage", "profile"} or "personal website" in label.lower():
            fallback = href
    return fallback


def extract_source_paper(block: Tag, text: str, base_url: str, name: str) -> tuple[str, str]:
    title = ""
    for anchor in block.find_all("a", href=True):
        href = anchor["href"]
        label = clean_text(anchor.get_text(" ", strip=True))
        if ".pdf" in href.lower() and len(label) > 8 and label.lower() not in {"cv", "download", "pdf"}:
            return label, absolute_url(base_url, href)
    patterns = [
        r"Job Market Paper\s*:\s*[\"“]?(.*?)[\"”]?(?:Fields? of Study|Advisor|Abstract|Related Links|$)",
        r"Job Market Paper\s+[\"“]?(.*?)[\"”]?(?:Visit .{0,50}personal website|Fields?|Advisor|Abstract|$)",
        r"Paper Title\s*:\s*(.*?)(?:Main Advisor|Advisor|Candidate Name|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            title = clean_text(match.group(1)).strip(' "“”')
            break

    anchors = block.find_all("a", href=True)
    if title:
        normalized_title = normalize_title(title)
        for anchor in anchors:
            label = clean_text(anchor.get_text(" ", strip=True))
            if labels_match(normalized_title, normalize_title(label)):
                return title, absolute_url(base_url, anchor["href"])

    return title, ""


def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def labels_match(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return left == right or (len(left) > 24 and (left in right or right in left))


def find_paper_link(soup: BeautifulSoup, base_url: str, known_title: str = "") -> tuple[str, str] | None:
    anchors = [anchor for anchor in soup.find_all("a", href=True) if not anchor["href"].startswith(("mailto:", "javascript:"))]
    normalized_known = normalize_title(known_title)

    if normalized_known:
        for anchor in anchors:
            label = clean_text(anchor.get_text(" ", strip=True))
            if labels_match(normalized_known, normalize_title(label)):
                return known_title or label, absolute_url(base_url, anchor["href"])

    for marker in soup.find_all(string=PAPER_MARKER_RE):
        current = marker.parent
        contexts: list[tuple[int, Tag]] = []
        for _ in range(6):
            if not isinstance(current, Tag) or current.name in {"body", "html"}:
                break
            context_text = clean_text(current.get_text(" ", strip=True))
            context_anchors = current.find_all("a", href=True)
            if context_anchors and 8 <= len(context_text) <= 2500:
                contexts.append((len(context_text), current))
            current = current.parent
        if not contexts:
            continue
        context = min(contexts, key=lambda item: item[0])[1]
        options = []
        for anchor in context.find_all("a", href=True):
            href = anchor["href"]
            if href.startswith(("mailto:", "javascript:", "#")):
                continue
            label = clean_text(anchor.get_text(" ", strip=True))
            lowered = label.lower()
            if lowered in {"skip to content", "home", "research", "teaching", "cv", "email"}:
                continue
            local_context = clean_text(anchor.parent.get_text(" ", strip=True)) if anchor.parent else label
            generic = lowered in {"link", "paper", "read paper", "job market paper", "jmp", "pdf", "download"}
            title = extract_title_from_context(local_context, label) if generic else label
            if not title or len(title) < 9:
                continue
            score = (30 if generic else 0) + (0 if ".pdf" in href.lower() else 5) - min(len(title), 120) / 120
            options.append((score, title, absolute_url(base_url, href)))
        if options:
            _, title, url = min(options, key=lambda item: item[0])
            return title, url
    return None


def extract_title_from_context(context: str, label: str) -> str:
    context = re.sub(re.escape(label), "", context, count=1, flags=re.IGNORECASE)
    context = PAPER_MARKER_RE.sub("", context, count=1)
    context = re.split(r"\bAbstract\s*:", context, maxsplit=1, flags=re.IGNORECASE)[0]
    return clean_text(context).strip(" :-–—[]()")[:240]


def build_candidate(partial: dict, department: dict) -> Candidate:
    stable = f"{department['institution']}|{partial['name']}".lower().encode("utf-8")
    return Candidate(
        id=hashlib.sha1(stable).hexdigest()[:12],
        name=partial["name"],
        institution=department["institution"],
        country=department["country"],
        rank=department["rank"],
        fields=partial["fields"],
        paper_title=partial["paper_title"],
        paper_url=partial["paper_url"],
        profile_url=partial["profile_url"],
        source_url=department["url"],
        last_verified=datetime.now(UTC).date().isoformat(),
    )


def deduplicate_partials(partials: Iterable[dict]) -> list[dict]:
    by_name: dict[str, dict] = {}
    for partial in partials:
        key = clean_text(partial["name"]).lower()
        current = by_name.get(key)
        if not current or (partial["paper_url"] and not current["paper_url"]):
            by_name[key] = partial
    return list(by_name.values())


def deduplicate_candidates(candidates: Iterable[Candidate]) -> list[Candidate]:
    by_id: dict[str, Candidate] = {}
    for candidate in candidates:
        by_id[candidate.id] = candidate
    return list(by_id.values())


def load_existing() -> dict:
    if not DATA_PATH.exists():
        return {"candidates": []}
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def ranking_period(scraper: Scraper) -> str:
    try:
        html = scraper.fetch(US_RANKING_URL)
        title = clean_text(BeautifulSoup(html, "html.parser").title.get_text(" ", strip=True))
        match = re.search(r"as of ([A-Za-z]+ \d{4})", title, re.IGNORECASE)
        if match:
            return match.group(1)
    except (requests.RequestException, ValueError, AttributeError):
        pass
    return load_existing().get("ranking_period", "May 2026")


def merge_recent(existing: dict, fresh: list[Candidate], failed_institutions: set[str]) -> list[Candidate]:
    merged = {candidate.id: candidate for candidate in fresh}
    cutoff = datetime.now(UTC).date() - timedelta(days=21)
    for old in existing.get("candidates", []):
        if old.get("institution") not in failed_institutions:
            continue
        try:
            verified = datetime.fromisoformat(old["last_verified"]).date()
            candidate = Candidate(**old)
        except (KeyError, TypeError, ValueError):
            continue
        if candidate.paper_title.lower() in {"skip to content", "home", "research", "link"} or candidate.paper_url.endswith("#content"):
            continue
        if verified >= cutoff and candidate.id not in merged:
            merged[candidate.id] = candidate
    return sorted(merged.values(), key=lambda item: (item.country, item.rank, item.institution, item.name))


def write_output(candidates: list[Candidate], period: str) -> None:
    payload = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "ranking_period": period,
        "ranking_sources": {"US": US_RANKING_URL, "UK": UK_RANKING_URL},
        "departments_monitored": len(DEPARTMENTS),
        "candidates": [asdict(candidate) for candidate in candidates],
    }
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh macroeconomics job market candidate data.")
    parser.add_argument("--delay", type=float, default=0.25, help="Delay between HTTP requests.")
    parser.add_argument("--department", help="Only scrape departments containing this text.")
    parser.add_argument("--debug", action="store_true", help="Print parser diagnostics.")
    args = parser.parse_args()

    scraper = Scraper(delay=args.delay, debug=args.debug)
    existing = load_existing()
    selected = DEPARTMENTS
    if args.department:
        needle = args.department.lower()
        selected = [item for item in DEPARTMENTS if needle in item["institution"].lower()]
        if not selected:
            print(f"No configured department matches {args.department!r}.", file=sys.stderr)
            return 2

    all_candidates: list[Candidate] = []
    failed: set[str] = set()
    report = []
    for department in selected:
        try:
            candidates = scraper.scrape_department(department)
            all_candidates.extend(candidates)
            if not candidates:
                failed.add(department["institution"])
            report.append({"institution": department["institution"], "count": len(candidates), "status": "ok" if candidates else "no verified records"})
            print(f"{department['institution']}: {len(candidates)} verified macro candidate(s)")
        except (requests.RequestException, ValueError) as error:
            failed.add(department["institution"])
            report.append({"institution": department["institution"], "count": 0, "status": str(error)})
            print(f"{department['institution']}: failed ({error})", file=sys.stderr)

    if args.department:
        untouched = [Candidate(**item) for item in existing.get("candidates", []) if item.get("institution") not in {d["institution"] for d in selected}]
        all_candidates.extend(untouched)

    merged = merge_recent(existing, deduplicate_candidates(all_candidates), failed)
    write_output(merged, ranking_period(scraper))
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(merged)} candidate(s) to {DATA_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
