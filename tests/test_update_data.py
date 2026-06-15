from bs4 import BeautifulSoup

from scripts.update_data import (
    candidate_blocks,
    curated_partials,
    extract_candidate,
    find_paper_link,
    is_valid_paper_title,
)


DEPARTMENT = {
    "institution": "Example University",
    "country": "US",
    "rank": 1,
    "url": "https://example.edu/candidates",
}


def test_extracts_structured_macro_candidate():
    soup = BeautifulSoup(
        """
        <article class="candidate-card">
          <h2><a href="https://candidate.example">Ada Economist</a></h2>
          <p>Job Market Paper: Aggregate Shocks and Household Saving</p>
          <p>Fields of Study: Macroeconomics, Household Finance</p>
        </article>
        """,
        "html.parser",
    )
    blocks = candidate_blocks(soup)
    candidate = extract_candidate(blocks[0], DEPARTMENT)
    assert candidate["name"] == "Ada Economist"
    assert candidate["paper_title"] == "Aggregate Shocks and Household Saving"
    assert candidate["fields"] == ["Macroeconomics", "Household Finance"]


def test_excludes_non_macro_candidate():
    soup = BeautifulSoup(
        """
        <article class="candidate-card">
          <h2><a href="https://candidate.example">Mina Researcher</a></h2>
          <p>Job Market Paper: Auctions and Market Design</p>
          <p>Fields of Study: Microeconomic Theory, Market Design</p>
        </article>
        """,
        "html.parser",
    )
    assert candidate_blocks(soup) == []


def test_resolves_jmp_link_from_candidate_site():
    soup = BeautifulSoup(
        """
        <section>
          <h2>Job Market Paper</h2>
          <a href="files/paper.pdf">Monetary Policy and Firm Dynamics</a>
          <p>Abstract: This paper studies...</p>
        </section>
        """,
        "html.parser",
    )
    result = find_paper_link(soup, "https://candidate.example/research/")
    assert result == (
        "Monetary Policy and Firm Dynamics",
        "https://candidate.example/research/files/paper.pdf",
    )


def test_prefers_known_title_link():
    soup = BeautifulSoup(
        """
        <main>
          <a href="cv.pdf">CV</a>
          <a href="jmp.pdf">The Macroeconomic Effects of Defense Spending News</a>
        </main>
        """,
        "html.parser",
    )
    result = find_paper_link(
        soup,
        "https://candidate.example/",
        "The Macroeconomic Effects of Defense Spending News",
    )
    assert result[1] == "https://candidate.example/jmp.pdf"


def test_does_not_treat_email_as_paper_link():
    soup = BeautifulSoup(
        """
        <article class="candidate-card">
          <h2><a href="https://candidate.example">Ada Economist</a></h2>
          <a href="mailto:ada@example.edu">ada@example.edu</a>
          <p>Job Market Paper: Aggregate Shocks and Household Saving</p>
          <p>Fields of Study: Macroeconomics</p>
        </article>
        """,
        "html.parser",
    )
    candidate = extract_candidate(candidate_blocks(soup)[0], DEPARTMENT)
    assert candidate["paper_title"] == "Aggregate Shocks and Household Saving"
    assert candidate["paper_url"] == ""


def test_extracts_prose_style_candidate_with_personal_site():
    soup = BeautifulSoup(
        """
        <div class="person-entry">
          Stephan Hobler
          <p>Primary Field: Macroeconomics</p>
          <a href="https://candidate.example">Personal Website</a>
        </div>
        """,
        "html.parser",
    )
    candidate = extract_candidate(candidate_blocks(soup)[0], DEPARTMENT)
    assert candidate["name"] == "Stephan Hobler"
    assert candidate["fields"] == ["Macroeconomics"]
    assert candidate["profile_url"] == "https://candidate.example"


def test_extracts_link_led_roster_entry():
    soup = BeautifulSoup(
        """
        <main>
          <a href="https://candidate.example">Finn Scholar</a>
          <p>Fields: Macroeconomics, Monetary Economics, and Labor</p>
          <p>Job Market Paper: <a href="https://candidate.example/jmp.pdf">The Phillips Curve</a></p>
          <a href="https://next.example">Next Candidate</a>
        </main>
        """,
        "html.parser",
    )
    candidates = [extract_candidate(block, DEPARTMENT) for block in candidate_blocks(soup)]
    candidate = next(item for item in candidates if item and item["name"] == "Finn Scholar")
    assert candidate["paper_title"] == "The Phillips Curve"
    assert candidate["paper_url"] == "https://candidate.example/jmp.pdf"


def test_curated_candidate_must_remain_on_official_roster():
    department = {
        "institution": "Boston University",
        "country": "US",
        "rank": 12,
        "url": "https://www.bu.edu/econ/job-market-candidates/",
    }
    present = BeautifulSoup("<main><h3>Zixing Guo</h3></main>", "html.parser")
    absent = BeautifulSoup("<main><h3>Another Candidate</h3></main>", "html.parser")

    assert [item["name"] for item in curated_partials(present, department)] == ["Zixing Guo"]
    assert curated_partials(absent, department) == []


def test_curated_candidate_supports_last_name_first_roster():
    department = {
        "institution": "University of Minnesota",
        "country": "US",
        "rank": 33,
        "url": "https://cla.umn.edu/economics/people/job-market-candidates",
    }
    roster = BeautifulSoup("<main><a>Barreto, Leonardo</a></main>", "html.parser")

    candidates = curated_partials(roster, department)
    assert [item["name"] for item in candidates] == ["Leonardo Barreto"]
    assert "roster_name" not in candidates[0]


def test_rejects_site_search_results_as_paper_titles():
    broken = "A candidate description ... Relevance: 38.8 News Item Now Hiring: Lecturer"

    assert not is_valid_paper_title(broken)
    assert is_valid_paper_title("Collateralized Debt Networks with Lender Default")
